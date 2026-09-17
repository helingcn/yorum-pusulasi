"""FastAPI contract and validation tests."""

import io

import pytest
from fastapi.testclient import TestClient

import geri_bildirim
from api import MAKSIMUM_KARAKTER, app


client = TestClient(app)


@pytest.fixture(autouse=True)
def _test_veritabani(tmp_path, monkeypatch):
    """Keeps feedback tests from writing to the real geri_bildirimler.db file."""
    monkeypatch.setattr(geri_bildirim, "VERITABANI_DOSYASI", tmp_path / "test_geri_bildirimler.db")


def test_saglik_modeli_yuklemeden_cevap_verir():
    cevap = client.get("/saglik")
    assert cevap.status_code == 200
    assert cevap.json()["durum"] == "hazır"
    assert cevap.json()["model"] == "duygu_finetuned_v5_full"


def test_bos_tekil_metin_reddedilir():
    cevap = client.post("/analiz", json={"metin": "   "})
    assert cevap.status_code == 422


def test_cok_uzun_tekil_metin_reddedilir():
    cevap = client.post("/analiz", json={"metin": "a" * (MAKSIMUM_KARAKTER + 1)})
    assert cevap.status_code == 422


def test_tekil_analiz_sozlesmesi():
    cevap = client.post("/analiz", json={"metin": "Ürün bugün kargoya verildi."})
    assert cevap.status_code == 200
    veri = cevap.json()
    assert veri["etiket"] == "nötr"
    assert set(veri["olasiliklar"]) == {"olumlu", "nötr", "olumsuz"}


def test_toplu_analiz_sozlesmesi():
    metinler = ["Çok memnun kaldım.", "Ürün bugün teslim edildi."]
    cevap = client.post("/toplu-analiz", json={"metinler": metinler})
    assert cevap.status_code == 200
    assert cevap.json()["toplam"] == 2
    assert [satir["metin"] for satir in cevap.json()["sonuclar"]] == metinler


def test_toplu_analizde_bos_satir_reddedilir():
    cevap = client.post("/toplu-analiz", json={"metinler": ["iyi ürün", ""]})
    assert cevap.status_code == 422


def test_kelime_onemleri_sozlesmesi():
    cevap = client.post("/kelime-onemleri", json={"metin": "Ürün gerçekten çok kaliteli."})
    assert cevap.status_code == 200
    kelimeler = cevap.json()["kelimeler"]
    assert len(kelimeler) == 4
    assert {"kelime", "onem"} <= kelimeler[0].keys()


def test_konu_analizi_karma_duygu_ayristirir():
    cevap = client.post("/konu-analizi", json={"metin": "Kargo hızlıydı ama kalitesi kötüydü."})
    assert cevap.status_code == 200
    konular = cevap.json()["konular"]
    bulunan = {k["konu"] for k in konular}
    assert {"kargo", "kalite"} <= bulunan


def test_konu_analizi_konu_gecmeyen_metinde_bos_liste_doner():
    cevap = client.post("/konu-analizi", json={"metin": "Harika bir ürün, çok memnun kaldım!"})
    assert cevap.status_code == 200
    assert cevap.json()["konular"] == []


def test_gecerli_geri_bildirim_kaydedilir():
    cevap = client.post("/geri-bildirim", json={
        "metin": "Ürün bugün kargoya verildi.", "tahmin": "nötr", "guven": 0.9, "karar": "doğru",
    })
    assert cevap.status_code == 200
    assert cevap.json() == {"kaydedildi": True}
    kayitlar = geri_bildirim.tumunu_al()
    assert len(kayitlar) == 1
    assert kayitlar[0]["dogru_etiket"] == "nötr"


def test_yanlis_karari_dogru_etiketsiz_reddedilir():
    cevap = client.post("/geri-bildirim", json={
        "metin": "Ürün bugün kargoya verildi.", "tahmin": "nötr", "guven": 0.9, "karar": "yanlış",
    })
    assert cevap.status_code == 422


def test_dosyadan_toplu_analiz_csv_sozlesmesi():
    csv_icerik = "yorum\nÇok memnun kaldım.\nÜrün bugün teslim edildi.\n"
    dosya = io.BytesIO(csv_icerik.encode("utf-8"))
    cevap = client.post("/toplu-analiz-dosya", files={"dosya": ("yorumlar.csv", dosya, "text/csv")})
    assert cevap.status_code == 200
    assert cevap.json()["toplam"] == 2


def test_dosyadan_toplu_analiz_yorum_sutunu_yoksa_reddedilir():
    csv_icerik = "baslik\nBir şey\n"
    dosya = io.BytesIO(csv_icerik.encode("utf-8"))
    cevap = client.post("/toplu-analiz-dosya", files={"dosya": ("yorumlar.csv", dosya, "text/csv")})
    assert cevap.status_code == 422


def test_dosyadan_toplu_analiz_desteklenmeyen_uzanti_reddedilir():
    dosya = io.BytesIO(b"ilgisiz veri")
    cevap = client.post("/toplu-analiz-dosya", files={"dosya": ("yorumlar.txt", dosya, "text/plain")})
    assert cevap.status_code == 422


def test_pdf_raporu_gecerli_pdf_dondurur():
    istek = {
        "toplam": 2, "olumlu": 1, "notr": 0, "olumsuz": 1, "ort_guven": 91.5,
        "sonuclar": [
            {"metin": "Ürün çok kaliteliydi!", "etiket": "olumlu", "guven": 0.95},
            {"metin": "Kargo geç geldi.", "etiket": "olumsuz", "guven": 0.88},
        ],
    }
    cevap = client.post("/pdf-raporu", json=istek)
    assert cevap.status_code == 200
    assert cevap.headers["content-type"] == "application/pdf"
    assert cevap.content[:5] == b"%PDF-"
