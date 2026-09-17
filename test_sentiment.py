"""
Unit tests for sentiment.py.

Run with: pytest test_sentiment.py -v
(Uses the real model — the first test loads it into memory, which takes a
few seconds; later ones are fast thanks to _model_yukle's lru_cache.)
"""

import pytest
import json
from pathlib import Path

from sentiment import (
    ETIKET_MAP,
    _tum_skorlari_hesapla,
    analiz_et,
    duygu_olasiliklari,
    kelime_onemleri,
    konu_analizi,
    toplu_analiz,
)
from hedefli_notr_karsi_ornekler import egitim_ornekleri as notr_karsi_ornekleri


def test_bos_metin_hata_verir():
    with pytest.raises(ValueError):
        analiz_et("")


def test_bosluk_metin_hata_verir():
    with pytest.raises(ValueError):
        analiz_et("   ")


def test_olumlu_yorum_dogru_siniflandirilir():
    sonuc = analiz_et("Bu ürün gerçekten harika, çok memnun kaldım, kesinlikle tavsiye ederim!")
    assert sonuc["etiket"] == "olumlu"
    assert 0.0 <= sonuc["guven"] <= 1.0


def test_olumsuz_yorum_dogru_siniflandirilir():
    sonuc = analiz_et("Berbat bir ürün, param boşa gitti, hiç memnun kalmadım.")
    assert sonuc["etiket"] == "olumsuz"
    assert 0.0 <= sonuc["guven"] <= 1.0


def test_notr_yorum_dogru_siniflandirilir():
    sonuc = analiz_et("Ürün bugün kargoya verildi.")
    assert sonuc["etiket"] == "nötr"


def test_analiz_sonucu_beklenen_anahtarlari_icerir():
    sonuc = analiz_et("Fena değil.")
    assert set(sonuc.keys()) == {"etiket", "guven"}
    assert sonuc["etiket"] in ("olumlu", "nötr", "olumsuz")


def test_buyuk_kucuk_harf_tutarli_sonuc_verir():
    # The model used to behave inconsistently on sentences starting with a
    # capital letter (see .claude/skills/run-duygu-analizi/SKILL.md); the
    # lowercasing fix should make both give the same result.
    kucuk = analiz_et("berbat bir ürün, hiç beğenmedim.")
    buyuk = analiz_et("Berbat bir ürün, hiç beğenmedim.")
    assert kucuk["etiket"] == buyuk["etiket"]


def test_etiket_ve_olasiliklar_ayni_model_cagrisini_paylasir():
    metin = "önbellek doğrulaması için benzersiz ürün yorumu 84729"
    analiz_et(metin)
    onceki_isabet = _tum_skorlari_hesapla.cache_info().hits
    olasiliklar = duygu_olasiliklari(metin)
    assert _tum_skorlari_hesapla.cache_info().hits == onceki_isabet + 1
    assert set(olasiliklar) == {"olumlu", "nötr", "olumsuz"}


def test_uzun_metin_model_sinirinda_guvenle_kesilir():
    sonuc = analiz_et("kaliteli ürün " * 700)
    assert sonuc["etiket"] in ("olumlu", "nötr", "olumsuz")


def test_toplu_analiz_dogru_sayida_sonuc_dondurur():
    metinler = ["harika ürün, çok memnunum", "berbat ürün, hiç memnun kalmadım", "ürün bugün kargoya verildi"]
    sonuclar = toplu_analiz(metinler)
    assert len(sonuclar) == len(metinler)


def test_toplu_analiz_sirayi_korur():
    metinler = ["Çok memnun kaldım, harika!", "Berbat, hiç beğenmedim.", "Ürün kargoya verildi."]
    sonuclar = toplu_analiz(metinler)
    assert [s["metin"] for s in sonuclar] == metinler


def test_toplu_analiz_ilerleme_callback_cagrilir():
    metinler = [f"ürün {i} numaralı sipariş, gayet iyi" for i in range(20)]  # bigger than BATCH_BOYUTU(16) -> 2 chunks
    cagrilar = []
    toplu_analiz(metinler, ilerleme_callback=lambda islenen, toplam: cagrilar.append((islenen, toplam)))
    assert cagrilar == [(16, 20), (20, 20)]


def test_toplu_analiz_beklenen_anahtarlari_icerir():
    sonuclar = toplu_analiz(["iyi ürün, memnun kaldım"])
    assert set(sonuclar[0].keys()) == {"metin", "etiket", "guven"}


def test_toplu_analiz_bos_metinde_hata_verir():
    with pytest.raises(ValueError):
        toplu_analiz(["iyi ürün, memnun kaldım", ""])


def test_kelime_onemleri_kelime_sayisi_kadar_sonuc_dondurur():
    metin = "Bu ürün gerçekten çok kötü çıktı"
    sonuclar = kelime_onemleri(metin)
    assert len(sonuclar) == len(metin.split())


def test_kelime_onemleri_kelimeleri_orijinal_sirayla_dondurur():
    metin = "Bu ürün gerçekten çok kötü çıktı"
    sonuclar = kelime_onemleri(metin)
    assert [s["kelime"] for s in sonuclar] == metin.split()


def test_kelime_onemleri_tek_kelimede_calisir():
    sonuclar = kelime_onemleri("harika")
    assert len(sonuclar) == 1
    assert sonuclar[0]["onem"] == 0.0


def test_etiket_map_temel_etiketleri_dogru_esler():
    assert ETIKET_MAP["positive"] == "olumlu"
    assert ETIKET_MAP["neutral"] == "nötr"
    assert ETIKET_MAP["negative"] == "olumsuz"


def test_notr_karsi_ornekleri_dengeli_ve_benzersizdir():
    ornekler = notr_karsi_ornekleri()
    assert len(ornekler) == 72
    assert {etiket: sum(o["label"] == etiket for o in ornekler) for etiket in ("neutral", "positive", "negative")} == {
        "neutral": 24, "positive": 24, "negative": 24,
    }
    assert len({o["text"].casefold().strip() for o in ornekler}) == len(ornekler)


def test_notr_karsi_ornekleri_degerlendirme_setleriyle_cakismaz():
    kok = Path(__file__).parent
    with (kok / "trsav1_held_out.json").open(encoding="utf-8") as f:
        held_out = json.load(f)
    with (kok / "kisa_yorum_regresyon.json").open(encoding="utf-8") as f:
        regresyon = json.load(f)
    normal = lambda metin: metin.casefold().strip().rstrip(".")
    egitim = {normal(o["text"]) for o in notr_karsi_ornekleri()}
    degerlendirme = {normal(o["text"]) for o in held_out + regresyon}
    assert not egitim & degerlendirme


def test_konu_analizi_farkli_konulari_ayirir():
    sonuclar = konu_analizi("Kargo hızlıydı ama kalite kötüydü.")
    konular = {s["konu"] for s in sonuclar}
    assert konular == {"kargo", "kalite"}


def test_konu_analizi_olumsuz_konuyu_dogru_bulur():
    sonuclar = konu_analizi("Kargo hızlıydı ama kalite kötüydü.")
    kalite = next(s for s in sonuclar if s["konu"] == "kalite")
    assert kalite["etiket"] == "olumsuz"


def test_konu_analizi_konu_gecmeyen_metinde_bos_liste_dondurur():
    assert konu_analizi("Harika bir ürün, çok memnun kaldım!") == []


def test_konu_analizi_sonuc_beklenen_anahtarlari_icerir():
    sonuclar = konu_analizi("Kargo hızlıydı ama kalite kötüydü.")
    for s in sonuclar:
        assert set(s.keys()) == {"konu", "parca", "etiket", "guven"}
