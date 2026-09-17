"""Persistent storage of user feedback.

Previously appended line by line to a plain CSV file (geri_bildirimler.csv)
— it couldn't be queried and wasn't safe for concurrent writes (two
simultaneous writes could corrupt each other). Moved to SQLite: it ships
with the stdlib (no new dependency), file locking safely serializes
concurrent writes, and corrections marked "yanlış" (wrong) can now be
queried with SQL from a single source instead of keeping a separate CSV
(egitim_duzeltmeleri.csv).
"""

import sqlite3
from datetime import datetime
from pathlib import Path

VERITABANI_DOSYASI = Path(__file__).parent / "geri_bildirimler.db"
GECERLI_ETIKETLER = {"olumlu", "nötr", "olumsuz"}

_SEMA = """
CREATE TABLE IF NOT EXISTS geri_bildirimler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tarih TEXT NOT NULL,
    yorum TEXT NOT NULL,
    model_tahmini TEXT NOT NULL,
    guven REAL NOT NULL,
    kullanici_karari TEXT NOT NULL,
    dogru_etiket TEXT NOT NULL
)
"""


def _baglanti() -> sqlite3.Connection:
    # A fresh connection on every call: since there's no sqlite3.Connection
    # object shared across threads (Streamlit multi-threaded, FastAPI
    # multi-request), there's no thread-safety issue — SQLite itself
    # manages file-level locking.
    conn = sqlite3.connect(VERITABANI_DOSYASI, timeout=10)
    conn.execute(_SEMA)
    return conn


def kaydet(metin: str, tahmin: str, guven: float, karar: str, dogru_etiket: str = "") -> None:
    """Saves a piece of feedback.

    Args:
        metin: The review that was analyzed.
        tahmin: The label the model produced.
        guven: The model's confidence in that prediction (0-1).
        karar: The user's assessment ("doğru" / "yanlış" — correct/wrong).
        dogru_etiket: The correct label the user specified, if karar is "yanlış".
    """
    if not metin.strip():
        raise ValueError("Boş yorum geri bildirim olarak kaydedilemez.")
    if tahmin not in GECERLI_ETIKETLER or (dogru_etiket and dogru_etiket not in GECERLI_ETIKETLER):
        raise ValueError("Geçersiz duygu etiketi.")

    with _baglanti() as conn:
        conn.execute(
            "INSERT INTO geri_bildirimler "
            "(tarih, yorum, model_tahmini, guven, kullanici_karari, dogru_etiket) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                datetime.now().isoformat(timespec="seconds"),
                metin,
                tahmin,
                guven,
                karar,
                dogru_etiket,
            ),
        )


def egitim_duzeltmelerini_al() -> list[dict]:
    """Returns feedback marked as wrong, in the {"yorum": ..., "etiket": ...}
    shape ready to use directly in the next fine-tuning round.
    """
    with _baglanti() as conn:
        conn.row_factory = sqlite3.Row
        satirlar = conn.execute(
            "SELECT yorum, dogru_etiket AS etiket FROM geri_bildirimler "
            "WHERE kullanici_karari = 'yanlış' ORDER BY id"
        ).fetchall()
    return [dict(satir) for satir in satirlar]


def tumunu_al() -> list[dict]:
    """Returns all feedback records (for auditing/analysis)."""
    with _baglanti() as conn:
        conn.row_factory = sqlite3.Row
        satirlar = conn.execute("SELECT * FROM geri_bildirimler ORDER BY id").fetchall()
    return [dict(satir) for satir in satirlar]
