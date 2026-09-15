"""Kısa ve kuvvetlendiricisiz müşteri yorumları için hedefli eğitim örnekleri.

Bu veri, "üründen memnun kaldım" gibi doğrudan fakat kısa ifadelerin nötr
etikete kaymasını azaltmak içindir. Regresyon seti bu dosyadan ayrıdır;
aynı metin iki tarafta da bulunmamalıdır.
"""

from collections import Counter


_KALIPLAR = {
    "positive": [
        "ürünü olumlu buldum", "ürün beklentimi karşıladı",
        "aldığıma memnunum", "ürün işimi gördü", "benim için uygun oldu",
        "ürünü beğendim", "ürün gayet güzel", "üründen razıyım",
        "tercihimden memnunum", "ürün istediğim gibi çıktı",
        "kullanışlı bir ürün", "ürün ihtiyacımı karşıladı",
        "ürün bende olumlu izlenim bıraktı", "ürün iyi çıktı",
        "bu alışverişten memnun kaldım", "ürün beklentime uygundu",
        "ürünü rahatlıkla kullanıyorum", "ürün benim için yeterli",
        "ürün başarılı", "ürünü severek kullanıyorum",
        "üründen hoşnut kaldım", "ürün doğru bir tercih oldu",
        "ürün umduğum gibiydi", "ürün kullanım amacına uygun",
    ],
    "negative": [
        "üründen memnun kalmadım", "ürün beklentimi karşılamadı",
        "aldığıma pişman oldum", "ürün işimi görmedi", "benim için uygun olmadı",
        "ürünü beğenmedim", "ürün yeterli gelmedi", "üründen razı değilim",
        "tercihimden memnun değilim", "ürün istediğim gibi çıkmadı",
        "kullanışlı bir ürün değil", "ürün ihtiyacımı karşılamadı",
        "ürün bende olumsuz izlenim bıraktı", "ürün kötü çıktı",
        "bu alışverişten memnun kalmadım", "ürün beklentime uymadı",
        "ürünü kullanmak zor geliyor", "ürün benim için yetersiz",
        "ürün başarısız", "ürünü kullanmayı bıraktım",
        "üründen hoşnut kalmadım", "ürün yanlış bir tercih oldu",
        "ürün umduğum gibi değildi", "ürün kullanım amacına uygun değil",
    ],
    "neutral": [
        "ürün elime ulaştı", "ürünü bugün teslim aldım",
        "ürün kargodan çıktı", "ürün paketli şekilde geldi",
        "siparişimi teslim aldım", "ürünü henüz kullanmadım",
        "ürün siyah renkte geldi", "ürün medium beden olarak geldi",
        "ürün kutusundan çıktı", "ürünün faturası paketteydi",
        "sipariş bilgisi gönderildi", "ürün için bildirim geldi",
        "ürün adresime teslim edildi", "paket bugün geldi",
        "ürünü açtım", "ürün kargo firmasına verildi",
        "ürünle ilgili henüz yorum yapmayacağım", "ürün tanıtımdaki renkte",
        "sipariş numaram oluşturuldu", "ürün için iade talebi açıldı",
        "ürünün paketi kapalıydı", "ürün stoktan gönderildi",
        "ürün teslim sürecinde", "kargo takip bilgisi paylaşıldı",
        "ürün için değişim kaydı oluşturuldu", "sipariş hazırlanıyor",
        "iade kargosu teslim edildi", "para iadesi sürecini bekliyorum",
        "değişim talebim inceleniyor", "iade paketini gönderim noktasına bıraktım",
        "iade kodu oluşturuldu", "geri ödeme talebim kayda alındı",
        "iade işlemi başlatıldı", "ürün iade için kargoya verildi",
        "değişim kargosu yola çıktı", "para iadesi işlemde",
    ],
}

_BASLAR = ["", "genel olarak ", "kısacası "]


def egitim_ornekleri() -> list[dict]:
    """Her sınıfta dengeli sayıda, toplam 200'den fazla eğitim örneği döndürür."""
    ornekler = []
    for etiket, kaliplar in _KALIPLAR.items():
        for bas in _BASLAR:
            for kalip in kaliplar:
                ornekler.append({"text": f"{bas}{kalip}.", "label": etiket})

    sayilar = Counter(ornek["label"] for ornek in ornekler)
    assert len(ornekler) == len({ornek["text"] for ornek in ornekler})
    assert sayilar == {etiket: len(kaliplar) * len(_BASLAR) for etiket, kaliplar in _KALIPLAR.items()}
    return ornekler
