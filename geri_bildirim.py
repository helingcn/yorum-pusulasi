"""Kullanıcı geri bildirimlerinin kalıcı depolanması.

Önceden düz CSV dosyasına (geri_bildirimler.csv) satır satır ekleniyordu —
sorgulanamıyordu ve eşzamanlı yazmalarda güvenli değildi (aynı anda iki
yazma birbirini bozabilirdi). SQLite'a taşındı: stdlib içinde geliyor (yeni
bağımlılık yok), dosya kilitleme ile eşzamanlı yazmaları güvenli şekilde
sıralıyor, ve "yanlış" işaretlenen düzeltmeleri artık ayrı bir CSV
(egitim_duzeltmeleri.csv) tutmak yerine tek bir kaynaktan SQL ile
sorgulayabiliyoruz.
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
    # Her çağrıda yeni bağlantı: thread'ler arasında paylaşılan bir
    # sqlite3.Connection nesnesi olmadığı için (Streamlit çoklu thread,
    # FastAPI çoklu istek) thread-safety sorunu yok — dosya seviyesindeki
    # kilitlemeyi SQLite'ın kendisi yönetiyor.
    conn = sqlite3.connect(VERITABANI_DOSYASI, timeout=10)
    conn.execute(_SEMA)
    return conn


def kaydet(metin: str, tahmin: str, guven: float, karar: str, dogru_etiket: str = "") -> None:
    """Bir geri bildirimi kaydeder.

    Args:
        metin: Analiz edilen yorum.
        tahmin: Modelin verdiği etiket.
        guven: Modelin o tahmine güveni (0-1).
        karar: Kullanıcının değerlendirmesi ("doğru" / "yanlış").
        dogru_etiket: karar "yanlış" ise kullanıcının belirttiği doğru etiket.
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
    """Yanlış işaretlenen geri bildirimleri, sonraki fine-tune turunda
    doğrudan kullanılabilecek {"yorum": ..., "etiket": ...} biçiminde döndürür.
    """
    with _baglanti() as conn:
        conn.row_factory = sqlite3.Row
        satirlar = conn.execute(
            "SELECT yorum, dogru_etiket AS etiket FROM geri_bildirimler "
            "WHERE kullanici_karari = 'yanlış' ORDER BY id"
        ).fetchall()
    return [dict(satir) for satir in satirlar]


def tumunu_al() -> list[dict]:
    """Tüm geri bildirim kayıtlarını (denetim/analiz amaçlı) döndürür."""
    with _baglanti() as conn:
        conn.row_factory = sqlite3.Row
        satirlar = conn.execute("SELECT * FROM geri_bildirimler ORDER BY id").fetchall()
    return [dict(satir) for satir in satirlar]
