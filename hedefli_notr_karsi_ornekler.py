"""Doğrulanmış nötr hata türleri için bağımsız karşıt eğitim örnekleri.

Her satır nötr, olumlu ve olumsuz bir üçlüdür. Böylece nötr sınırı
güçlendirilirken kutuplu sınıfların anlamı korunur. Denetim/test cümleleri
bu dosyaya kopyalanmamıştır.
"""

from collections import Counter


_KARSI_UCLULER = [
    # Ürün henüz yeterince kullanılmadı / sonuç bekleniyor.
    ("ürünü yeni kullanmaya başladım, sonucunu zamanla göreceğim", "ilk kullanımda etkisini gösterdi, memnun kaldım", "bir süredir kullanıyorum fakat hiçbir etkisini görmedim"),
    ("etkisini değerlendirmek için biraz daha kullanmam gerekiyor", "etkisini kısa sürede gördüm ve beğendim", "uzun süre kullandım ama fayda sağlamadı"),
    ("ürünü denedikten sonra deneyimimi paylaşacağım", "ürünü denedim ve sonuçtan memnun kaldım", "ürünü denedim ve sonuç beni hayal kırıklığına uğrattı"),
    ("ilk kez aldım, kullanım sonucunu henüz bilmiyorum", "ilk kez aldım ve beklediğimden iyi çıktı", "ilk kez aldım fakat beklentimi karşılamadı"),
    ("yorumları inceleyerek sipariş verdim, henüz denemedim", "yorumlara bakarak aldım ve seçimimden memnunum", "yorumlara bakarak aldım ama aldığıma pişman oldum"),
    ("ürünün uzun süreli etkisini daha sonra değerlendireceğim", "uzun süreli kullanımda oldukça faydalı oldu", "uzun süreli kullanımda etkisiz kaldı"),

    # Teslimat ve paketleme: olgu ile memnuniyet/şikâyet ayrımı.
    ("paket iki gün içinde adresime teslim edildi", "paket beklediğimden erken geldi, çok memnun kaldım", "paket söz verilen tarihten sonra geldi"),
    ("sipariş aynı hafta içinde elime ulaştı", "sipariş çok hızlı ulaştı, hizmet harikaydı", "sipariş çok geç ulaştı, mağdur oldum"),
    ("ürün kutulu şekilde teslim edildi", "ürün özenli ve sağlam bir kutuyla geldi", "ürünün kutusu ezilmiş ve yırtılmıştı"),
    ("paketin içinde ürün ve faturası bulunuyordu", "paket eksiksiz ve çok düzenli hazırlanmıştı", "paketten sipariş ettiğim parça eksik çıktı"),
    ("kargo görevlisi paketi kapıya bıraktı", "kargo görevlisi çok yardımcı oldu, teşekkür ederim", "kargo görevlisi paketi hasarlı bıraktı"),
    ("ürün belirtilen teslimat yöntemiyle gönderildi", "teslimat süreci sorunsuz ve hızlıydı", "teslimat sürecinde sürekli sorun yaşadım"),

    # Orta/zayıf değerlendirme ile açık kutupluluk ayrımı.
    ("ürün idare eder, belirgin bir fark görmedim", "ürün beklediğimden başarılı çıktı", "ürün tamamen başarısız çıktı"),
    ("ortalama bir ürün, özel bir yanı yok", "ortalamanın üstünde kaliteli bir ürün", "kalitesi ortalamanın çok altında"),
    ("ürün temel ihtiyacı karşılıyor", "ürün ihtiyacımı fazlasıyla karşıladı", "ürün temel ihtiyacımı bile karşılamadı"),
    ("performansı standart seviyede", "performansı oldukça başarılı", "performansı kabul edilemeyecek kadar kötü"),
    ("ne belirgin bir avantajı ne de dezavantajı var", "avantajları beklentimin üzerinde", "dezavantajları nedeniyle kullanamadım"),
    ("ürün hakkında kesin bir olumlu veya olumsuz fikrim oluşmadı", "ürün hakkında genel fikrim oldukça olumlu", "ürün hakkında genel fikrim tamamen olumsuz"),

    # Renk, yapı ve kullanım alanı hakkında bağlamsal/faktüel ifadeler.
    ("ürünün rengi açık bir tonda", "ürünün açık tonunu çok beğendim", "rengi beklediğimden açık olduğu için kullanamadım"),
    ("bu seçenek koyu renk olarak sunuluyor", "koyu rengi çok şık görünüyor", "rengi gereğinden koyu ve kötü görünüyor"),
    ("ürün ince telli saçlar için belirtilmiş", "ince telli saçlarımda çok iyi sonuç verdi", "saçımda kötü sonuç verdi ve kullanmayı bıraktım"),
    ("bu ürün kalın kaşlar için tasarlanmamış", "kaş tipime tam uydu ve iyi sabitledi", "kaşlarımda hiçbir işe yaramadı"),
    ("ambalajın üzerinde güvenlik bandı bulunmuyor", "ambalajı güvenli ve özenli hazırlanmış", "ambalaj açık geldiği için ürüne güvenemedim"),
    ("şişe ayrı bir koruyucu poşete konulmamış", "şişe koruyucu ambalajla sağlam geldi", "şişe korumasız geldi ve içeriği dökülmüştü"),
]


def egitim_ornekleri() -> list[dict]:
    ornekler = []
    for notr, olumlu, olumsuz in _KARSI_UCLULER:
        ornekler.extend([
            {"text": notr, "label": "neutral"},
            {"text": olumlu, "label": "positive"},
            {"text": olumsuz, "label": "negative"},
        ])

    sayilar = Counter(ornek["label"] for ornek in ornekler)
    assert sayilar == {"neutral": 24, "positive": 24, "negative": 24}
    assert len(ornekler) == len({ornek["text"].casefold().strip() for ornek in ornekler})
    return ornekler
