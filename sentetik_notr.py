"""
Generates "purely transactional/procedural neutral" sentences (order
placed, there was X in the box, shipping info sent, etc.) — which are rare
in real data — from templates with variation. Goal: add these to
finetune3.py's training data so the model genuinely learns these patterns
as neutral instead of "the start of a complaint." See SKILL.md Gotchas
(the "sipariş verildi" / "fatura" / "aynı" findings).

Run with: python sentetik_notr.py  (prints sample output)
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

SON_UNLU_KALIN = set("aıou")  # da/dı/du/dö -> "da" if back vowel; simplified back/front distinction for this project


def r(): return random.choice(RENKLER)
def b(): return random.choice(BEDENLER)
def u(): return random.choice(URUNLER).capitalize()
def g(): return random.choice(GUNLER)
def y(): return random.choice(YONTEMLER)
def e(): return random.choice(ESYALAR)


def kutuda_esya_cumlesi() -> str:
    """Simple vowel harmony: 'da' if the word's last vowel is a back vowel, 'de' if front."""
    esya = e()
    son_unlu = next((c for c in reversed(esya) if c in "aeıioöuü"), "a")
    baglac = "da" if son_unlu in SON_UNLU_KALIN else "de"
    return f"{u()} kutusunda {esya} {baglac} vardı."


def uret(adet: int, seed: int = 123) -> list[str]:
    """Generates `adet` sentences. If the template+word combination space is
    smaller than `adet` (without going into an infinite loop), fills the rest
    with repeats — with hundreds of combinations available, this rarely
    kicks in in practice."""
    random.seed(seed)
    cumleler = set()
    deneme = 0
    max_deneme = adet * 50
    while len(cumleler) < adet and deneme < max_deneme:
        sablon = random.choice(SABLONLAR)
        cumleler.add(sablon())
        deneme += 1
    sonuc = list(cumleler)
    while len(sonuc) < adet:  # fill up with repeats if the combination space runs short
        sablon = random.choice(SABLONLAR)
        sonuc.append(sablon())
    return sonuc


if __name__ == "__main__":
    ornekler = uret(30)
    for c in ornekler:
        print(c)
    print(f"\n(30 sample sentences shown above; use uret(n) to generate as many as you want)")
