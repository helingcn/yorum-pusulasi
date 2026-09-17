"""
Turkish Customer Review Sentiment Analysis
----------------------------------------
Classifies Turkish text using a multilingual, three-class
(positive/neutral/negative) sentiment model.

Model: ./duygu_finetuned_v5_full (production) — cardiffnlp/twitter-xlm-roberta-base-sentiment
fine-tuned on maydogan/Turkish_SentimentAnalysis_TRSAv1 (real product reviews,
balanced) + synthetic "procedural neutral" sentences (sentetik_notr.py)
(see finetune3.py). v4_full and v3 are earlier, still-valid fallback
versions of the same chain (see the _FINETUNED_YOL order below).

Round summary (details: .claude/skills/run-duygu-analizi/SKILL.md Gotchas):
              winvoker test (Wikipedia neutral)   TRSAv1/gold test (real neutral)
base model:   74.4%                                63.6%
v1:           91.8%  (misleading — see Gotchas)   63.1%  (no real gain)
v2:           70.0%                                81.3%  (real gain)
v3:           73.2%                                81.6%  (+ specific errors fixed)
v4_full/v5_full: improved with short-review + return-process targeted
              examples, each measured against and promoted over its
              predecessor — v5_full is in production.
v6 (candidate): REJECTED against v5_full on the gold set (accuracy -3.1,
              neutral recall -8.3 points)

v1 leaned negative and sourced neutral from winvoker/Wikipedia — it scored
91.8% in evaluate.py but this was MISLEADING (that test's neutral class is
also Wikipedia). Tested against real product reviews (evaluate_trsav1.py),
v1's real neutral recall came out to 0.7%. v2 was trained on balanced TRSAv1
(real reviews) and genuinely improved. But v2 still classified purely
procedural/transactional sentences like "sipariş verildi" (order placed),
"kutunun içinde fatura vardı" (there was an invoice in the box), "fotoğraftakiyle
aynı" (same as in the photo) as negative — because even within TRSAv1 itself,
such purely neutral procedural sentences are rare. v3 fills that gap with
~1500 template-generated synthetic procedural sentences; these specific
errors are now fixed with 99%+ confidence. v4_full/v5_full extend the same
recipe with targeted corrective examples (every new candidate is measured
against the production model via model_karsilastir.py).

Model folders are searched in order (see _FINETUNED_YOL): v5_full → v4_full
→ v3 → base model if none are present.
"""

import re
import threading
from functools import lru_cache
from pathlib import Path

from transformers import pipeline

_TABAN_MODEL = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
_V5_FULL_YOL = Path(__file__).parent / "duygu_finetuned_v5_full"
_V4_FULL_YOL = Path(__file__).parent / "duygu_finetuned_v4_full"
_V3_YOL = Path(__file__).parent / "duygu_finetuned_v3"
# v5_full improved on short/direct-review and return-process neutral
# regressions, and also raised overall accuracy and neutral recall on the
# TRSAv1 held-out set. Falls back safely to earlier verified versions if a
# model folder is missing.
_FINETUNED_YOL = next((yol for yol in (_V5_FULL_YOL, _V4_FULL_YOL, _V3_YOL) if yol.is_dir()), _TABAN_MODEL)

# The model is called through the SAME shared pipeline object by both
# api.py (FastAPI, multiple requests) and app.py (Streamlit, multiple
# sessions/threads). Concurrency protection lives here, in one place —
# previously only api.py had its own global lock, app.py had none at all.
#
# IMPORTANT (verified live): this used to be a semaphore allowing as many
# concurrent inferences as there are CPU cores ("for performance"). When the
# React frontend fired genuinely parallel requests (via Promise.all, /analiz
# + /konu-analizi at the same time), this caused the entire API process to
# crash silently in this environment (macOS + PyTorch) with a native abort
# (NSException) — the HuggingFace pipeline object turned out not to be safe
# when called from multiple threads truly concurrently; the earlier
# assumption that "forward passes are thread-safe" was wrong. The semaphore
# was therefore deliberately reduced to 1 (a full mutex): only one request
# is processed at a time. This costs throughput but is provably crash-safe —
# stability comes before performance. If real concurrency is wanted later,
# load a separate copy of the model per worker thread (or use separate
# worker processes) instead.
_CIKARIM_SEMAFORU = threading.Semaphore(1)


def aktif_model_adi() -> str:
    """Returns the human-readable name of the currently selected production model, for the API and UI."""
    return _FINETUNED_YOL.name if isinstance(_FINETUNED_YOL, Path) else _FINETUNED_YOL


def model_yuklu_mu() -> bool:
    """Reports the current load state on a health-check call, without loading the model."""
    return _model_yukle.cache_info().currsize > 0


def modeli_hazirla() -> None:
    """Loads the model immediately, without waiting for the first user request.

    api.py calls this at application startup (lifespan): if the model fails
    to load, the application never comes up at all (fail-fast) — the user
    never hits a hidden multi-second delay on their first request, nor a
    failure in production.
    """
    _model_yukle()


@lru_cache(maxsize=1)
def _model_yukle():
    """Loads the model only once (caches it) — never reloads it on later calls."""
    model_yolu = str(_FINETUNED_YOL) if _FINETUNED_YOL.is_dir() else _TABAN_MODEL
    return pipeline("sentiment-analysis", model=model_yolu)


ETIKET_MAP = {"positive": "olumlu", "neutral": "nötr", "negative": "olumsuz",
              "LABEL_2": "olumlu", "LABEL_1": "nötr", "LABEL_0": "olumsuz"}
BATCH_BOYUTU = 16
MAKSIMUM_TOKEN = 512


@lru_cache(maxsize=512)
def _tum_skorlari_hesapla(kucuk_metin: str) -> tuple[tuple[str, float], ...]:
    """Runs a text through the model once and caches the scores for all three classes.

    When the UI asks first for the dominant label and then for the
    probabilities, the same text is not sent to the model a second time.
    ``truncation`` prevents very long reviews from erroring out by
    exceeding the model's context limit.
    """
    with _CIKARIM_SEMAFORU:
        sonuclar = _model_yukle()(
            kucuk_metin,
            top_k=None,
            truncation=True,
            max_length=MAKSIMUM_TOKEN,
        )
    return tuple(
        (ETIKET_MAP.get(sonuc["label"], sonuc["label"]), float(sonuc["score"]))
        for sonuc in sonuclar
    )


def analiz_et(metin: str) -> dict:
    """
    Analyzes a single piece of text.

    Args:
        metin: The Turkish text to analyze (e.g. a customer review).

    Returns:
        {"etiket": "olumlu" | "nötr" | "olumsuz", "guven": 0.0-1.0}
    """
    if not metin or not metin.strip():
        raise ValueError("Boş metin analiz edilemez.")

    # The model behaves inconsistently on sentences starting with a capital
    # letter (e.g. "Berbat..." can come out positive, "berbat..." negative —
    # same meaning, different result). Lowercasing raised accuracy on the
    # real-world eval set from 73.2% to 74.4% (500 examples, evaluate.py).
    # See .claude/skills/run-duygu-analizi/SKILL.md Gotchas.
    skorlar = _tum_skorlari_hesapla(metin.strip().lower())
    etiket, guven = max(skorlar, key=lambda oge: oge[1])

    return {"etiket": etiket, "guven": round(guven, 3)}


def duygu_olasiliklari(metin: str) -> dict[str, float]:
    """Returns the model probabilities for all three sentiment classes, for the UI."""
    if not metin or not metin.strip():
        raise ValueError("Boş metin analiz edilemez.")

    return {etiket: round(skor, 4) for etiket, skor in _tum_skorlari_hesapla(metin.strip().lower())}


def toplu_analiz(metinler: list[str], ilerleme_callback=None) -> list[dict]:
    """
    Analyzes multiple texts as a batch (feeding the model chunks of
    BATCH_BOYUTU items at a time, instead of calling analiz_et one by one).
    Measured on 500 examples: ~1.38x faster, zero difference in labels, at
    most a 0.000002 floating-point difference in confidence scores (doesn't
    affect the displayed percentages) — see SKILL.md Gotchas.

    Args:
        ilerleme_callback: If given, called as ilerleme_callback(islenen, toplam)
            after each chunk is processed (e.g. for a Streamlit progress bar).
            Chunking manually (instead of leaving it to the pipeline's own
            internal batching) exists precisely so intermediate progress can
            be observed; the speed characteristics stay the same.
    """
    for m in metinler:
        if not m or not m.strip():
            raise ValueError("Boş metin analiz edilemez.")

    model = _model_yukle()
    kucuk_metinler = [m.lower() for m in metinler]
    toplam = len(kucuk_metinler)

    sonuclar = []
    for i in range(0, toplam, BATCH_BOYUTU):
        parca = kucuk_metinler[i:i + BATCH_BOYUTU]
        # The semaphore is released after each chunk (not for the whole
        # request) — so other concurrent requests can interleave between
        # chunks while a large batch request is being processed.
        with _CIKARIM_SEMAFORU:
            sonuclar.extend(
                model(
                    parca,
                    batch_size=BATCH_BOYUTU,
                    truncation=True,
                    max_length=MAKSIMUM_TOKEN,
                )
            )
        if ilerleme_callback:
            ilerleme_callback(min(i + BATCH_BOYUTU, toplam), toplam)

    return [
        {"metin": m, "etiket": ETIKET_MAP.get(s["label"], s["label"]), "guven": round(s["score"], 3)}
        for m, s in zip(metinler, sonuclar)
    ]


def kelime_onemleri(metin: str) -> list[dict]:
    """
    Computes how much each word contributed to the decision using the
    "leave-one-word-out" (occlusion) method: how much does the model's
    confidence in the originally predicted label drop when a word is
    removed from the text (or does the label change entirely)? The higher
    the value, the more that word supports the decision. Requires no extra
    library — it just calls the existing model repeatedly.

    Returns:
        [{"kelime": str, "onem": float}, ...] — in the order they appear in the text.
    """
    model = _model_yukle()
    kelimeler = metin.split()
    if len(kelimeler) <= 1:
        return [{"kelime": k, "onem": 0.0} for k in kelimeler]

    with _CIKARIM_SEMAFORU:
        taban = model(metin.lower())[0]
    taban_etiket, taban_skor = taban["label"], taban["score"]

    onemler = []
    for i in range(len(kelimeler)):
        kalan = " ".join(kelimeler[:i] + kelimeler[i + 1:])
        with _CIKARIM_SEMAFORU:
            sonuc = model(kalan.lower())[0]
        if sonuc["label"] == taban_etiket:
            fark = taban_skor - sonuc["score"]
        else:
            fark = taban_skor  # the label changed, so this word was decisive
        onemler.append({"kelime": kelimeler[i], "onem": round(fark, 3)})

    return onemler


KONU_SOZLUGU = {
    "kargo": ["kargo", "teslimat", "gönderi", "paket", "kutu", "elime ulaş"],
    "kalite": ["kalite", "malzeme", "dayanıklı", "sağlam", "kırık", "bozuk", "kaliteli", "kalitesiz"],
    "fiyat": ["fiyat", "pahalı", "ucuz", "para", "bütçe", "indirim"],
    "beden": ["beden", "ölçü", "büyük geldi", "küçük geldi", "dar geldi", "bol geldi"],
    "renk": ["renk", "renkte", "renkli"],
    "müşteri hizmetleri": ["müşteri hizmet", "destek", "satıcı", "iade", "değişim", "ilgilen"],
}

_AYIRICI_BAGLAC = re.compile(r"\b(ama|fakat|ancak|lakin)\b", re.IGNORECASE)


def _parcalara_ayir(metin: str) -> list[str]:
    """Splits text into clauses on the conjunctions 'ama/fakat/ancak/lakin'
    ("but/however") and commas. Very short (<2-word) fragments are dropped —
    they're unlikely to be a meaningful sub-clause and only add noise."""
    parcalar = _AYIRICI_BAGLAC.split(metin)
    parcalar = [p for p in parcalar if p.strip().lower() not in ("ama", "fakat", "ancak", "lakin")]

    sonuc = []
    for parca in parcalar:
        for alt in parca.split(","):
            alt = alt.strip(" .!?")
            if len(alt.split()) >= 2:
                sonuc.append(alt)
    return sonuc if sonuc else [metin.strip()]


def _konulari_bul(parca: str) -> list[str]:
    parca_kucuk = parca.lower()
    return [konu for konu, anahtarlar in KONU_SOZLUGU.items()
            if any(a in parca_kucuk for a in anahtarlar)]


def konu_analizi(metin: str) -> list[dict]:
    """
    Splits a review into topics (shipping, quality, price, size, color,
    customer service) and analyzes the sentiment of each topic separately.
    E.g. "Shipping was fast but quality was bad" -> shipping: positive,
    quality: negative.

    A rule-based approach (not "real" ABSA in the academic sense): splits
    the text on conjunctions/commas, looks for the topic dictionary's
    keywords in each clause, and runs the existing analiz_et separately on
    clauses where a topic was found. Requires no new model or data. See
    SKILL.md Gotchas for its limitations.

    Returns:
        [{"konu": str, "parca": str, "etiket": str, "guven": float}, ...]
        Returns an empty list if no known topic appears in any clause.
    """
    sonuclar = []
    for parca in _parcalara_ayir(metin):
        konular = _konulari_bul(parca)
        if not konular:
            continue
        analiz = analiz_et(parca)
        for konu in konular:
            sonuclar.append({"konu": konu, "parca": parca,
                              "etiket": analiz["etiket"], "guven": analiz["guven"]})
    return sonuclar


if __name__ == "__main__":
    ornekler = [
        "Bu ürün gerçekten çok kaliteli, tavsiye ederim!",
        "Kargo çok geç geldi ve ürün kırık çıktı, hiç memnun kalmadım.",
        "Ürün bugün kargoya verildi.",
    ]

    print("Örnek analiz sonuçları:\n")
    for sonuc in toplu_analiz(ornekler):
        print(f"Yorum : {sonuc['metin']}")
        print(f"Sonuç : {sonuc['etiket']} (güven: {sonuc['guven']})\n")
