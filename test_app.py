"""Streamlit arayüzü (app.py) için otomatik testler.

streamlit.testing.v1.AppTest ile gerçek bir tarayıcı açmadan, script'i bir
Streamlit script runner içinde çalıştırıp widget etkileşimlerini simüle
eder. 877+ satırlık, elle yazılmış HTML/CSS/JS içeren en kırılgan dosyanın
(bkz. .claude/skills/run-duygu-analizi/SKILL.md Gotchas — buradaki UI
hatalarının hepsi canlı manuel testle bulunmuştu) önceden hiç otomatik
testi yoktu. Bu dosya yazılırken bile gerçek bir çökme bulundu ve
düzeltildi: `st.toast(mesaj, icon="✓")` geçerli Streamlit sürümünde
"✓ geçerli bir emoji değil" hatasıyla çöküyordu (bkz. app.py, "✅" ile
düzeltildi) — geri bildirim kaydedildikten sonraki her rerun'da uygulamayı
kilitleyen, önceden fark edilmemiş bir regresyondu.
"""

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import geri_bildirim
import pdf_raporu


@pytest.fixture(autouse=True)
def _test_veritabani(tmp_path, monkeypatch):
    """Geri bildirim testleri gerçek geri_bildirimler.db dosyasına yazmasın."""
    monkeypatch.setattr(geri_bildirim, "VERITABANI_DOSYASI", tmp_path / "test_geri_bildirimler.db")


def _calistir() -> AppTest:
    """Uygulamayı, OS-tercihi sorgu parametresi zaten ayarlanmış gibi çalıştırır."""
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
    assert "onemler" in veri  # kelime_onemleri de hesaplanmış olmalı
    assert "konu_sonuclari" in veri  # konu_analizi de hesaplanmış olmalı


def test_gecerli_geri_bildirim_veritabanina_yazilir_ve_cokmez():
    """Bu test, geri bildirim kaydından SONRAKİ rerun'u da çalıştırarak
    st.toast'ın (regresyon: geçersiz emoji ikonu) tetiklendiği anı kapsar."""
    at = _calistir()
    at.text_area[0].set_value("Kargo çok geç geldi, hiç memnun kalmadım.")
    at.button[0].click()
    at.run(timeout=60)
    assert not at.exception

    at.radio(key="geri_bildirim_karar").set_value("Doğru")
    kaydet_dugmesi = next(b for b in at.button if b.label == "Geri bildirimi kaydet")
    kaydet_dugmesi.click()
    at.run(timeout=60)  # geri bildirim kaydedilir + st.toast tetiklenir
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
    """Regresyon: PDF_FONT önceden sabit bir macOS sistem yoluna
    (/System/Library/Fonts/...) bağlıydı — Linux/Windows/Docker'da dosya
    bulunamadığı için bu fonksiyon doğrudan çökerdi. Artık repo içine
    gömülü, platformdan bağımsız bir font kullanıyor (fonts/DejaVuSans.ttf)."""
    sonuc_df = pd.DataFrame([
        {"metin": "Ürün çok kaliteliydi, çok memnun kaldım!", "etiket": "olumlu", "guven": 0.95},
        {"metin": "Kargo geç geldi, üzgünüm.", "etiket": "olumsuz", "guven": 0.88},
    ])
    pdf_bytes = pdf_raporu.pdf_raporu_olustur(2, 1, 0, 1, 91.5, sonuc_df)
    assert pdf_bytes[:5] == b"%PDF-"
    assert len(pdf_bytes) > 1000
