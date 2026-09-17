"""Automated tests for the Streamlit UI (app.py).

Uses streamlit.testing.v1.AppTest to run the script inside a Streamlit
script runner and simulate widget interactions, without opening a real
browser. The most fragile file in the project — 877+ lines of hand-written
HTML/CSS/JS (see .claude/skills/run-duygu-analizi/SKILL.md Gotchas, where
every UI bug listed there was found through live manual testing) — had no
automated tests at all before this. Even while writing this file, a real
crash was found and fixed: `st.toast(mesaj, icon="✓")` crashed on the
current Streamlit version with a "✓ is not a valid emoji" error (see
app.py, fixed with "✅") — a previously unnoticed regression that locked up
the app on every rerun after feedback was saved.
"""

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import geri_bildirim
import pdf_raporu


@pytest.fixture(autouse=True)
def _test_veritabani(tmp_path, monkeypatch):
    """Keeps feedback tests from writing to the real geri_bildirimler.db file."""
    monkeypatch.setattr(geri_bildirim, "VERITABANI_DOSYASI", tmp_path / "test_geri_bildirimler.db")


def _calistir() -> AppTest:
    """Runs the app fresh, ready for a test to interact with it.

    Setting the "tema" query param is a leftover from an earlier dark-mode
    bootstrap approach that app.py no longer reads (see the comment near
    the `karanlik_mod` toggle in app.py for why it was reverted) — harmless
    to keep, but no longer load-bearing.
    """
    at = AppTest.from_file("app.py")
    at.query_params["tema"] = "light"
    at.run(timeout=60)
    return at


def test_sayfa_hatasiz_yuklenir():
    at = _calistir()
    assert not at.exception
    assert [t.label for t in at.tabs] == ["Tekil analiz", "Dosya analizi"]


def test_bos_yorum_gonderilince_uyari_gosterilir():
    at = _calistir()
    at.text_area[0].set_value("   ")
    at.button[0].click()
    at.run(timeout=60)
    assert not at.exception
    assert any("yorum gir" in w.value.lower() for w in at.warning)


def test_olumlu_yorum_dogru_siniflandirilir_ve_sonuc_gosterilir():
    at = _calistir()
    at.text_area[0].set_value("Bu ürün gerçekten çok kaliteli, tavsiye ederim!")
    at.button[0].click()
    at.run(timeout=60)
    assert not at.exception
    veri = at.session_state["tekil_analiz_verisi"]
    assert veri["sonuc"]["etiket"] == "olumlu"
    assert "onemler" in veri  # kelime_onemleri should have been computed too
    assert "konu_sonuclari" in veri  # konu_analizi should have been computed too


def test_gecerli_geri_bildirim_veritabanina_yazilir_ve_cokmez():
    """This test also runs the rerun AFTER the feedback is saved, covering
    the moment st.toast fires (regression: invalid emoji icon)."""
    at = _calistir()
    at.text_area[0].set_value("Kargo çok geç geldi, hiç memnun kalmadım.")
    at.button[0].click()
    at.run(timeout=60)
    assert not at.exception

    at.radio(key="geri_bildirim_karar").set_value("Doğru")
    kaydet_dugmesi = next(b for b in at.button if b.label == "Geri bildirimi kaydet")
    kaydet_dugmesi.click()
    at.run(timeout=60)  # feedback gets saved + st.toast fires
    assert not at.exception

    kayitlar = geri_bildirim.tumunu_al()
    assert len(kayitlar) == 1
    assert kayitlar[0]["kullanici_karari"] == "doğru"
    assert kayitlar[0]["dogru_etiket"] == "olumsuz"


def test_yanlis_geri_bildirim_duzeltme_olarak_kaydedilir():
    at = _calistir()
    at.text_area[0].set_value("Ürün bugün kargoya verildi.")
    at.button[0].click()
    at.run(timeout=60)
    assert not at.exception

    at.radio(key="geri_bildirim_karar").set_value("Yanlış")
    at.selectbox(key="geri_bildirim_etiket").set_value("olumlu")
    kaydet_dugmesi = next(b for b in at.button if b.label == "Geri bildirimi kaydet")
    kaydet_dugmesi.click()
    at.run(timeout=60)
    assert not at.exception

    duzeltmeler = geri_bildirim.egitim_duzeltmelerini_al()
    assert duzeltmeler == [{"yorum": "Ürün bugün kargoya verildi.", "etiket": "olumlu"}]


def test_pdf_raporu_turkce_karakterlerle_cokmez():
    """Regression: PDF_FONT used to be a hardcoded macOS system path
    (/System/Library/Fonts/...) — this function crashed outright on
    Linux/Windows/Docker since the file couldn't be found there. Now uses a
    font bundled into the repo, independent of the OS (fonts/DejaVuSans.ttf)."""
    sonuc_df = pd.DataFrame([
        {"metin": "Ürün çok kaliteliydi, çok memnun kaldım!", "etiket": "olumlu", "guven": 0.95},
        {"metin": "Kargo geç geldi, üzgünüm.", "etiket": "olumsuz", "guven": 0.88},
    ])
    pdf_bytes = pdf_raporu.pdf_raporu_olustur(2, 1, 0, 1, 91.5, sonuc_df)
    assert pdf_bytes[:5] == b"%PDF-"
    assert len(pdf_bytes) > 1000
