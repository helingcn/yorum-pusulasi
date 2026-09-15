"""v5 tam eğitim tarifine doğrulanmış nötr hata türlerinin karşıtlarını ekler.

Test/denetim cümleleri eğitime girmez. Yeni aday model ancak kısa yorum,
TRSAv1 held-out ve bağımsız karşıt set değerlendirmelerini birlikte geçerse
üretime alınmalıdır.
"""

from finetune3 import main as tam_egitim
from hedefli_notr_karsi_ornekler import egitim_ornekleri


if __name__ == "__main__":
    tam_egitim(
        ek_hedefli_ornekler=egitim_ornekleri(),
        cikti_dizini="./duygu_finetuned_v6_full",
        gecici_dizin="./_egitim_gecici_v6",
    )
