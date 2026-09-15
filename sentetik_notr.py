"""
Gerçek veride nadir bulunan "saf işlemsel/prosedürel nötr" cümleleri
(sipariş verildi, kutunun içinde X vardı, kargo bilgisi gönderildi vb.)
şablon + varyasyonla üretir. Amaç: finetune3.py'nin eğitim verisine
ekleyip modelin bu kalıpları "şikayetin girişi" yerine gerçekten nötr
olarak öğrenmesini sağlamak. Bkz. SKILL.md Gotchas ("sipariş verildi" /
"fatura" / "aynı" bulguları).

Çalıştırmak için: python sentetik_notr.py  (örnek çıktı basar)
"""

import itertools
import random

RENKLER = ["siyah", "beyaz", "mavi", "kırmızı", "yeşil", "sarı", "gri",
           "pembe", "mor", "turuncu", "bej", "lacivert", "turkuaz", "bordo",
           "altın", "gümüş", "haki"]
BEDENLER = ["XS", "S", "M", "L", "XL", "XXL", "36", "38", "40", "42", "44", "46"]
URUNLER = ["ayakkabı", "çanta", "gömlek", "pantolon", "elbise", "ceket",
           "kazak", "telefon kılıfı", "kulaklık", "saat", "gözlük", "çorap",
           "sırt çantası", "bilezik", "kolye", "şapka", "eldiven", "terlik",
           "kemer", "bere"]
GUNLER = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "12", "14"]
YONTEMLER = ["SMS", "e-posta", "mail", "WhatsApp mesajı", "telefon araması",
             "uygulama bildirimi", "kargo firması sitesi"]
ESYALAR = ["fatura", "kullanım kılavuzu", "garanti belgesi", "hediye çeki",
           "teşekkür kartı", "yedek parça", "temizlik bezi", "kartvizit",
           "örnek ürün paketi", "indirim kuponu", "sticker"]

SABLONLAR = [
    lambda: f"Ürün {r()} renkte, {b()} beden olarak sipariş verildi.",
    lambda: f"Sipariş {g()} gün içinde kargoya verildi.",
    lambda: f"Kargo takip numarası {y()} ile gönderildi.",
    lambda: f"Kutunun içinde {e()} vardı.",
    lambda: f"Ürün {g()} gün içinde elime ulaştı.",
    lambda: f"Sipariş numarası {y()} ile bildirildi.",
    lambda: f"Rengi tam fotoğraftakiyle aynıydı.",
    lambda: f"{u()} {r()} renkte geldi.",
    lambda: f"Paketin içinden {e()} çıktı.",
    lambda: f"Ürünü {g()} gündür kullanıyorum, henüz bir yorum yapmadım.",
    lambda: f"Fatura ve garanti belgesi kutunun içindeydi.",
    lambda: f"Ürün açıklamasında belirtilen ölçülerle uyumluydu.",
    lambda: f"{b()} beden tercih ettim, {r()} renk seçtim.",
    lambda: f"Kargo şirketi {y()} üzerinden bilgilendirme yaptı.",
    lambda: f"{u()} sipariş verildi, {g()} gün içinde teslim edildi.",
    lambda: f"Ürünün rengi ilanda gösterilenle aynıydı.",
    lambda: kutuda_esya_cumlesi(),
    lambda: f"Boyut fotoğraftakiyle aynıydı.",
    lambda: f"Ürün {b()} beden olarak değiştirildi.",
]

SON_UNLU_KALIN = set("aıou")  # da/dı/du/dö -> kalınsa "da"; bu proje icin basit ayrım: kalın/ince


def r(): return random.choice(RENKLER)
def b(): return random.choice(BEDENLER)
def u(): return random.choice(URUNLER).capitalize()
def g(): return random.choice(GUNLER)
def y(): return random.choice(YONTEMLER)
def e(): return random.choice(ESYALAR)


def kutuda_esya_cumlesi() -> str:
    """Basit ünlü uyumu: kelimenin son ünlüsü kalınsa 'da', inceyse 'de'."""
    esya = e()
    son_unlu = next((c for c in reversed(esya) if c in "aeıioöuü"), "a")
    baglac = "da" if son_unlu in SON_UNLU_KALIN else "de"
    return f"{u()} kutusunda {esya} {baglac} vardı."


def uret(adet: int, seed: int = 123) -> list[str]:
    """`adet` kadar cümle üretir. Şablon+kelime kombinasyon uzayı `adet`'ten
    küçükse (sonsuz döngüye girmeden) kalanı tekrarlarla doldurur — bu,
    yüzlerce kombinasyon varken pratikte nadiren devreye girer."""
    random.seed(seed)
    cumleler = set()
    deneme = 0
    max_deneme = adet * 50
    while len(cumleler) < adet and deneme < max_deneme:
        sablon = random.choice(SABLONLAR)
        cumleler.add(sablon())
        deneme += 1
    sonuc = list(cumleler)
    while len(sonuc) < adet:  # kombinasyon uzayı yetersizse tekrarla tamamla
        sablon = random.choice(SABLONLAR)
        sonuc.append(sablon())
    return sonuc


if __name__ == "__main__":
    ornekler = uret(30)
    for c in ornekler:
        print(c)
    print(f"\n(örnek 30 tanesi gösterildi, uret(n) ile istenilen sayıda üretilebilir)")
