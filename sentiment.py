"""
Türkçe Müşteri Yorumları Duygu Analizi
----------------------------------------
Çok dilli, üç sınıflı (olumlu/nötr/olumsuz) bir sentiment modelini
kullanarak Türkçe metinleri sınıflandırır.

Model: ./duygu_finetuned_v5_full (üretimde) — cardiffnlp/twitter-xlm-roberta-base-sentiment'in
maydogan/Turkish_SentimentAnalysis_TRSAv1 (gerçek ürün yorumları, dengeli)
+ sentetik "prosedürel nötr" cümlelerle (sentetik_notr.py) fine-tune edilmiş
hali (bkz. finetune3.py). v4_full ve v3 aynı zincirin önceki, hâlâ geçerli
fallback sürümleri (aşağıdaki _FINETUNED_YOL sırasına bakınız).

Turların özeti (detaylar: .claude/skills/run-duygu-analizi/SKILL.md Gotchas):
              winvoker testi (Wikipedia nötr)   TRSAv1/gold testi (gerçek nötr)
taban model:  %74.4                              %63.6
v1:           %91.8  (yanıltıcı — bkz. Gotchas)  %63.1  (gerçekte kazanç yok)
v2:           %70.0                              %81.3  (gerçek kazanç)
v3:           %73.2                              %81.6  (+ spesifik hatalar düzeldi)
v4_full/v5_full: kısa yorum + iade süreci hedefli örnekleriyle iyileştirildi,
              her biri kendi selefine karşı ölçülüp terfi etti — v5_full üretimde.
v6 (aday):    gold sette v5_full'e karşı REDDEDİLDİ (doğruluk -3.1, nötr recall -8.3 puan)

v1, olumsuza ağırlık verip nötr'ü winvoker/Wikipedia'dan aldı — evaluate.py'de
%91.8 gösterdi ama YANILTICIYDI (o testin nötr'ü de Wikipedia). Gerçek
ürün yorumlarıyla (evaluate_trsav1.py) test edilince v1'in gerçek nötr
recall'ı %0.7 çıktı. v2, TRSAv1 (gerçek yorum) ile dengeli eğitildi ve
gerçekten iyileşti. Ama v2 hâlâ "sipariş verildi", "kutunun içinde fatura
vardı", "fotoğraftakiyle aynı" gibi saf prosedürel/işlemsel cümleleri
olumsuz sanıyordu — TRSAv1'in kendisinde bile bu tür saf nötr cümleler nadir
olduğu için. v3, bu boşluğu şablonla üretilmiş ~1500 sentetik prosedürel
cümleyle dolduruyor; bu spesifik hatalar artık %99+ güvenle düzeldi. v4_full/
v5_full aynı tarifi hedefli düzeltici örneklerle genişletiyor
(model_karsilastir.py ile her yeni aday üretimdeki modele karşı ölçülüyor).

Model klasörleri sırayla aranır (bkz. _FINETUNED_YOL): v5_full → v4_full →
v3 → hiçbiri yoksa taban model.
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
# v5_full, kısa/doğrudan ve iade süreci nötr regresyonlarında iyileşti;
# TRSAv1 held-out'ta genel doğruluğu ve nötr recall'ı da artırdı.
# Model klasörü yoksa güvenli biçimde önceki doğrulanmış sürümlere dönülür.
_FINETUNED_YOL = next((yol for yol in (_V5_FULL_YOL, _V4_FULL_YOL, _V3_YOL) if yol.is_dir()), _TABAN_MODEL)

# Model, hem api.py (FastAPI, çoklu istek) hem de app.py (Streamlit, çoklu
# oturum/thread) tarafından AYNI paylaşılan pipeline nesnesi üzerinden
# çağrılıyor. Eşzamanlılık koruması burada, tek bir yerde yapılıyor — önceden
# yalnızca api.py kendi global kilidiyle korunuyordu, app.py hiç korumasızdı.
#
# ÖNEMLİ (canlı doğrulanmış): Burada başlangıçta CPU çekirdek sayısı kadar
# eşzamanlı çıkarıma izin veren bir semafor vardı ("performans için").
# React frontend'i gerçek paralel istek attığında (Promise.all ile aynı anda
# /analiz + /konu-analizi) bu, bu ortamda (macOS + PyTorch) tüm API
# sürecinin sessizce çökmesine yol açtı (NSException / native abort) —
# HuggingFace pipeline nesnesi birden fazla thread'den GERÇEKTEN eşzamanlı
# çağrıldığında güvenli değilmiş, önceki "forward pass'ler thread-safe'dir"
# varsayımı yanlış çıktı. Bu yüzden semafor kasıtlı olarak 1'e (tam mutex)
# döndürüldü: aynı anda tek istek işlenir. Bu, hız kaybına yol açar ama
# çökmeye karşı kesin güvenlidir — kararlılık, performanstan önce gelir.
# İleride gerçek eşzamanlılık isteniyorsa, tek model nesnesini thread başına
# ayrı bir kopya olarak yüklemek (veya ayrı worker süreçleri) gerekir.
_CIKARIM_SEMAFORU = threading.Semaphore(1)


def aktif_model_adi() -> str:
    """API ve arayüz için seçili üretim modelinin okunabilir adını döndürür."""
    return _FINETUNED_YOL.name if isinstance(_FINETUNED_YOL, Path) else _FINETUNED_YOL


def model_yuklu_mu() -> bool:
    """Kontrol çağrısında modeli yüklemeden mevcut yükleme durumunu bildirir."""
    return _model_yukle.cache_info().currsize > 0


def modeli_hazirla() -> None:
    """Modeli hemen, ilk kullanıcı isteğini beklemeden yükler.

    api.py bunu uygulama açılışında (lifespan) çağırır: model yüklenemezse
    uygulama hiç ayağa kalkmaz (fail-fast) — kullanıcı ilk isteğinde
    birkaç saniyelik gizli bir gecikmeyle ya da üretimde bir hatayla
    karşılaşmaz.
    """
    _model_yukle()


@lru_cache(maxsize=1)
def _model_yukle():
    """Modeli sadece bir kez yükler (cache'ler), her çağrıda tekrar yüklemez."""
    model_yolu = str(_FINETUNED_YOL) if _FINETUNED_YOL.is_dir() else _TABAN_MODEL
    return pipeline("sentiment-analysis", model=model_yolu)


ETIKET_MAP = {"positive": "olumlu", "neutral": "nötr", "negative": "olumsuz",
              "LABEL_2": "olumlu", "LABEL_1": "nötr", "LABEL_0": "olumsuz"}
BATCH_BOYUTU = 16
MAKSIMUM_TOKEN = 512


@lru_cache(maxsize=512)
def _tum_skorlari_hesapla(kucuk_metin: str) -> tuple[tuple[str, float], ...]:
    """Bir metni tek kez çalıştırıp üç sınıf skorunu önbelleğe alır.

    Arayüz önce baskın etiketi, ardından olasılıkları istediğinde aynı metin
    modele ikinci kez gönderilmez. ``truncation`` uzun yorumların modelin
    bağlam sınırını aşarak hata vermesini engeller.
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
    Tek bir metni analiz eder.

    Args:
        metin: Analiz edilecek Türkçe metin (örn. bir müşteri yorumu).

    Returns:
        {"etiket": "olumlu" | "nötr" | "olumsuz", "guven": 0.0-1.0}
    """
    if not metin or not metin.strip():
        raise ValueError("Boş metin analiz edilemez.")

    # Model büyük harfle başlayan cümlelerde tutarsız davranıyor (örn. "Berbat..."
    # olumlu, "berbat..." olumsuz çıkabiliyor — aynı anlam, farklı sonuç). Küçük
    # harfe çevirmek gerçek veri setinde doğruluğu %73.2 -> %74.4 çıkardı (500
    # örnek, evaluate.py). Bkz. .claude/skills/run-duygu-analizi/SKILL.md Gotchas.
    skorlar = _tum_skorlari_hesapla(metin.strip().lower())
    etiket, guven = max(skorlar, key=lambda oge: oge[1])

    return {"etiket": etiket, "guven": round(guven, 3)}


def duygu_olasiliklari(metin: str) -> dict[str, float]:
    """Üç duygu sınıfının model olasılıklarını arayüz için döndürür."""
    if not metin or not metin.strip():
        raise ValueError("Boş metin analiz edilemez.")

    return {etiket: round(skor, 4) for etiket, skor in _tum_skorlari_hesapla(metin.strip().lower())}


def toplu_analiz(metinler: list[str], ilerleme_callback=None) -> list[dict]:
    """
    Birden fazla metni batch halinde analiz eder (tek tek analiz_et çağırmak
    yerine modele parça parça — BATCH_BOYUTU'luk gruplar halinde — verir).
    500 örnekte ölçüldü: ~1.38x daha hızlı, etiketlerde sıfır fark, güven
    skorunda en fazla 0.000002 kayan nokta farkı (görünen yüzdeleri
    etkilemez) — bkz. SKILL.md Gotchas.

    Args:
        ilerleme_callback: Verilirse her grup işlendikten sonra
            ilerleme_callback(islenen, toplam) ile çağrılır (örn. Streamlit
            ilerleme çubuğu için). Manuel gruplama (pipeline'ın kendi iç
            batch'lemesine bırakmak yerine) tam bu yüzden — ara ilerleme
            gözlemlenebilsin diye; hız karakteristiği aynı kalır.
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
        # Semafor her parçadan sonra serbest bırakılıyor (tüm istek boyunca
        # değil) — böylece büyük bir toplu istek işlenirken diğer eşzamanlı
        # istekler de parçalar arasında araya girebiliyor.
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
    Her kelimenin karara ne kadar etki ettiğini "leave-one-word-out" (occlusion)
    yöntemiyle hesaplar: kelime metinden çıkarıldığında modelin, orijinal tahmin
    edilen etikete verdiği güven ne kadar düşüyor (veya etiket tamamen değişiyor mu).
    Değer ne kadar yüksekse, o kelime kararı o kadar çok destekliyor demektir.
    Ekstra kütüphane gerektirmez, mevcut modeli tekrar tekrar çağırır.

    Returns:
        [{"kelime": str, "onem": float}, ...] — metindeki sırayla.
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
            fark = taban_skor  # etiket değiştiyse bu kelime belirleyiciydi
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
    """Metni 'ama/fakat/ancak/lakin' bağlaçlarına ve virgüllere göre parçalara
    ayırır. Çok kısa (<2 kelime) parçalar atılır — anlamlı bir alt cümle
    olma ihtimali düşük, sadece gürültü eklerler."""
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
    Yorumu konu bazında (kargo, kalite, fiyat, beden, renk, müşteri
    hizmetleri) parçalara ayırıp her konudaki duyguyu ayrı ayrı analiz eder.
    Örn. "Kargo hızlıydı ama kalite kötüydü" -> kargo: olumlu, kalite: olumsuz.

    Kural tabanlı bir yaklaşım (akademik anlamda "gerçek" ABSA değil): metni
    bağlaç/virgüle göre böler, her parçada konu sözlüğündeki kelimeleri arar,
    konu bulunan parçaları mevcut analiz_et ile ayrı ayrı analiz eder. Yeni
    model/veri gerektirmez. Sınırlamaları için bkz. SKILL.md Gotchas.

    Returns:
        [{"konu": str, "parca": str, "etiket": str, "guven": float}, ...]
        Hiçbir parçada bilinen bir konu geçmiyorsa boş liste döner.
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
