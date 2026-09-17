"""Yorum Pusulası standalone HTTP API layer."""

import io
import json as json_modulu
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Literal

import pandas as pd
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from geri_bildirim import kaydet as geri_bildirim_kaydet
from pdf_raporu import pdf_raporu_olustur
from sentiment import (
    aktif_model_adi,
    analiz_et,
    duygu_olasiliklari,
    kelime_onemleri,
    konu_analizi,
    model_yuklu_mu,
    modeli_hazirla,
    toplu_analiz,
)


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("yorum_pusulasi.api")

MAKSIMUM_KARAKTER = 10_000
MAKSIMUM_TOPLU_YORUM = 500
Duygu = Literal["olumlu", "nötr", "olumsuz"]

# Authentication: if the API_ANAHTARI environment variable is not set,
# auth is disabled (for local development) — it must always be set before
# going to production. Required for /analiz and /toplu-analiz once set.
_API_ANAHTARI = os.getenv("API_ANAHTARI")
_api_anahtari_basligi = APIKeyHeader(name="X-API-Key", auto_error=False)

# CORS: IZINLI_ORIJINLER is a comma-separated origin list (e.g.
# "https://myapp.com,https://panel.myapp.com"). Falls back to the React/Vite
# dev server's default addresses if the environment variable is not set
# (the frontend/ folder is set up for this) — always set the real domain via
# IZINLI_ORIJINLER before going to production, otherwise only local dev
# origins are accepted.
_VARSAYILAN_GELISTIRME_ORIJINLERI = ["http://localhost:5173", "http://127.0.0.1:5173"]
_IZINLI_ORIJINLER = [o.strip() for o in os.getenv("IZINLI_ORIJINLER", "").split(",") if o.strip()] or _VARSAYILAN_GELISTIRME_ORIJINLERI

limiter = Limiter(key_func=get_remote_address)


def api_anahtarini_dogrula(anahtar: str | None = Depends(_api_anahtari_basligi)) -> None:
    if _API_ANAHTARI is None:
        return
    if anahtar != _API_ANAHTARI:
        raise HTTPException(status_code=401, detail="Geçersiz veya eksik API anahtarı (X-API-Key başlığı).")


class _IstekLoglamaOrtaKatmani(BaseHTTPMiddleware):
    """Logs every request with its method, path, status code, and duration."""

    async def dispatch(self, request: Request, call_next):
        baslangic = time.perf_counter()
        try:
            yanit = await call_next(request)
        except Exception:
            sure_ms = (time.perf_counter() - baslangic) * 1000
            logger.exception("%s %s -> HATA (%.1fms)", request.method, request.url.path, sure_ms)
            raise
        sure_ms = (time.perf_counter() - baslangic) * 1000
        logger.info("%s %s -> %s (%.1fms)", request.method, request.url.path, yanit.status_code, sure_ms)
        return yanit


@asynccontextmanager
async def _lifespan(app: FastAPI):
    if _API_ANAHTARI is None:
        logger.warning(
            "API_ANAHTARI ortam değişkeni ayarlanmadı — kimlik doğrulama DEVRE DIŞI. "
            "Bu yalnızca yerel geliştirme için güvenlidir, üretime bu şekilde alınmamalı."
        )
    logger.info("Model önceden yükleniyor...")
    modeli_hazirla()  # blows up here if it fails to load — the app never comes up (fail-fast)
    logger.info("Model hazır: %s", aktif_model_adi())
    yield


class AnalizIstegi(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    metin: str = Field(min_length=1, max_length=MAKSIMUM_KARAKTER)


class TopluAnalizIstegi(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    metinler: list[str] = Field(min_length=1, max_length=MAKSIMUM_TOPLU_YORUM)

    @field_validator("metinler")
    @classmethod
    def metinleri_dogrula(cls, metinler: list[str]) -> list[str]:
        temiz = []
        for sira, metin in enumerate(metinler):
            if not isinstance(metin, str) or not metin.strip():
                raise ValueError(f"{sira}. sıradaki yorum boş olamaz")
            metin = metin.strip()
            if len(metin) > MAKSIMUM_KARAKTER:
                raise ValueError(f"{sira}. sıradaki yorum {MAKSIMUM_KARAKTER} karakteri aşamaz")
            temiz.append(metin)
        return temiz


class AnalizSonucu(BaseModel):
    etiket: Duygu
    guven: float = Field(ge=0, le=1)
    olasiliklar: dict[Duygu, float]


class TopluSonucSatiri(BaseModel):
    metin: str
    etiket: Duygu
    guven: float = Field(ge=0, le=1)


class TopluAnalizSonucu(BaseModel):
    toplam: int
    sonuclar: list[TopluSonucSatiri]


class KelimeOnemi(BaseModel):
    kelime: str
    onem: float


class KelimeOnemleriSonucu(BaseModel):
    kelimeler: list[KelimeOnemi]


class KonuSonucu(BaseModel):
    konu: str
    parca: str
    etiket: Duygu
    guven: float = Field(ge=0, le=1)


class KonuAnaliziSonucu(BaseModel):
    konular: list[KonuSonucu]


class GeriBildirimIstegi(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    metin: str = Field(min_length=1, max_length=MAKSIMUM_KARAKTER)
    tahmin: Duygu
    guven: float = Field(ge=0, le=1)
    karar: Literal["doğru", "yanlış"]
    dogru_etiket: Duygu | None = None

    @model_validator(mode="after")
    def dogru_etiketi_kontrol_et(self) -> "GeriBildirimIstegi":
        if self.karar == "yanlış" and self.dogru_etiket is None:
            raise ValueError("karar 'yanlış' ise dogru_etiket zorunludur.")
        return self


class PdfRaporuIstegi(BaseModel):
    toplam: int = Field(ge=0)
    olumlu: int = Field(ge=0)
    notr: int = Field(ge=0)
    olumsuz: int = Field(ge=0)
    ort_guven: float = Field(ge=0, le=100)
    sonuclar: list[TopluSonucSatiri]


app = FastAPI(
    title="Yorum Pusulası API",
    description="Türkçe müşteri yorumları için olumlu, nötr ve olumsuz duygu analizi.",
    version="1.0.0",
    lifespan=_lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(_IstekLoglamaOrtaKatmani)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_IZINLI_ORIJINLER,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/", tags=["sistem"])
def kok() -> dict[str, str]:
    return {"mesaj": "Yorum Pusulası API", "dokumantasyon": "/docs"}


@app.get("/saglik", tags=["sistem"])
def saglik() -> dict[str, str | bool]:
    # model_yuklu_mu() always returns True here because modeli_hazirla() runs
    # in the lifespan (if the app is up, the model is ready) — no longer
    # cosmetic, it reflects a real successful preload.
    return {"durum": "hazır", "model": aktif_model_adi(), "model_yuklu": model_yuklu_mu()}


@app.post(
    "/analiz",
    response_model=AnalizSonucu,
    tags=["analiz"],
    dependencies=[Depends(api_anahtarini_dogrula)],
)
@limiter.limit("30/minute")
def tekil_analiz(request: Request, istek: AnalizIstegi) -> AnalizSonucu:
    try:
        sonuc = analiz_et(istek.metin)
        olasiliklar = duygu_olasiliklari(istek.metin)
    except ValueError as hata:
        raise HTTPException(status_code=422, detail=str(hata)) from hata
    return AnalizSonucu(**sonuc, olasiliklar=olasiliklar)


@app.post(
    "/toplu-analiz",
    response_model=TopluAnalizSonucu,
    tags=["analiz"],
    dependencies=[Depends(api_anahtarini_dogrula)],
)
@limiter.limit("5/minute")
def coklu_analiz(request: Request, istek: TopluAnalizIstegi) -> TopluAnalizSonucu:
    try:
        sonuclar = toplu_analiz(istek.metinler)
    except ValueError as hata:
        raise HTTPException(status_code=422, detail=str(hata)) from hata
    return TopluAnalizSonucu(toplam=len(sonuclar), sonuclar=sonuclar)


@app.post(
    "/toplu-analiz-dosya",
    response_model=TopluAnalizSonucu,
    tags=["analiz"],
    dependencies=[Depends(api_anahtarini_dogrula)],
)
@limiter.limit("5/minute")
async def dosyadan_toplu_analiz(request: Request, dosya: UploadFile = File(...)) -> TopluAnalizSonucu:
    """Uploads a CSV/Excel(.xlsx)/JSON file and runs a batch analysis.

    The parsing logic is identical to app.py's Streamlit version (looks for
    a column/field named ``yorum``, skips empty rows) — centralized here, in
    the API layer, so both clients (Streamlit and React) work against the
    same contract.
    """
    uzanti = (dosya.filename or "").lower().rsplit(".", 1)[-1]
    icerik = await dosya.read()
    try:
        if uzanti == "csv":
            df = pd.read_csv(io.BytesIO(icerik))
        elif uzanti == "xlsx":
            df = pd.read_excel(io.BytesIO(icerik))
        elif uzanti == "json":
            veri = json_modulu.loads(icerik)
            df = pd.DataFrame({"yorum": veri}) if isinstance(veri, list) and veri and isinstance(veri[0], str) else pd.DataFrame(veri)
        else:
            raise HTTPException(status_code=422, detail="Desteklenmeyen dosya türü. CSV, XLSX veya JSON yükleyin.")
    except HTTPException:
        raise
    except Exception as hata:
        raise HTTPException(status_code=422, detail=f"Dosya okunamadı: {hata}") from hata

    if "yorum" not in df.columns:
        raise HTTPException(status_code=422, detail="Dosyada 'yorum' adında bir sütun/alan bulunamadı.")

    df = df[df["yorum"].notna()].copy()
    df["yorum"] = df["yorum"].astype(str).str.strip()
    df = df[df["yorum"] != ""]
    if df.empty:
        raise HTTPException(status_code=422, detail="Dosyada analiz edilebilecek dolu bir yorum bulunamadı.")
    if len(df) > MAKSIMUM_TOPLU_YORUM:
        raise HTTPException(status_code=422, detail=f"Dosya en fazla {MAKSIMUM_TOPLU_YORUM} yorum içerebilir.")

    try:
        sonuclar = toplu_analiz(df["yorum"].tolist())
    except ValueError as hata:
        raise HTTPException(status_code=422, detail=str(hata)) from hata
    return TopluAnalizSonucu(toplam=len(sonuclar), sonuclar=sonuclar)


@app.post(
    "/kelime-onemleri",
    response_model=KelimeOnemleriSonucu,
    tags=["analiz"],
    dependencies=[Depends(api_anahtarini_dogrula)],
)
@limiter.limit("30/minute")
def kelime_onemleri_uc_nokta(request: Request, istek: AnalizIstegi) -> KelimeOnemleriSonucu:
    try:
        onemler = kelime_onemleri(istek.metin)
    except ValueError as hata:
        raise HTTPException(status_code=422, detail=str(hata)) from hata
    return KelimeOnemleriSonucu(kelimeler=onemler)


@app.post(
    "/konu-analizi",
    response_model=KonuAnaliziSonucu,
    tags=["analiz"],
    dependencies=[Depends(api_anahtarini_dogrula)],
)
@limiter.limit("30/minute")
def konu_analizi_uc_nokta(request: Request, istek: AnalizIstegi) -> KonuAnaliziSonucu:
    try:
        konular = konu_analizi(istek.metin)
    except ValueError as hata:
        raise HTTPException(status_code=422, detail=str(hata)) from hata
    return KonuAnaliziSonucu(konular=konular)


@app.post("/geri-bildirim", tags=["geri-bildirim"], dependencies=[Depends(api_anahtarini_dogrula)])
@limiter.limit("30/minute")
def geri_bildirim_uc_nokta(request: Request, istek: GeriBildirimIstegi) -> dict[str, bool]:
    dogru_etiket = istek.dogru_etiket if istek.karar == "yanlış" else istek.tahmin
    try:
        geri_bildirim_kaydet(istek.metin, istek.tahmin, istek.guven, istek.karar, dogru_etiket)
    except ValueError as hata:
        raise HTTPException(status_code=422, detail=str(hata)) from hata
    return {"kaydedildi": True}


@app.post("/pdf-raporu", tags=["analiz"], dependencies=[Depends(api_anahtarini_dogrula)])
@limiter.limit("10/minute")
def pdf_raporu_uc_nokta(request: Request, istek: PdfRaporuIstegi) -> Response:
    df = pd.DataFrame([s.model_dump() for s in istek.sonuclar])
    pdf_bytes = pdf_raporu_olustur(istek.toplam, istek.olumlu, istek.notr, istek.olumsuz, istek.ort_guven, df)
    return Response(content=pdf_bytes, media_type="application/pdf")
