"""
Bir modelin gerçek, etiketli bir veri seti üzerindeki doğruluğunu ölçer.
Varsayılan olarak üretimdeki modeli (sentiment.py) test eder; --model ile
başka bir HuggingFace modelini aynı örneklemde karşılaştırmak için kullanılır.

Veri seti: winvoker/turkish-sentiment-analysis-dataset (CC-BY-SA-4.0)
- Olumlu/Olumsuz örnekler: 'urun_yorumlari' ve 'magaza_yorumlari' alt kümelerinden
  (gerçek Hepsiburada/mağaza ürün yorumları).
- Nötr örnekler: bu veri setinde ürün yorumu kaynaklı nötr örnek YOK; nötr etiketli
  metinlerin neredeyse tamamı ('wiki' alt kümesi) Wikipedia cümleleri. Yani nötr
  sonucu, ürün yorumu değil, genel/ansiklopedik metin üzerinde ölçülüyor — bu bir
  sınırlama, sonuçları yorumlarken göz önünde bulundur.

Çalıştırmak için:
  python evaluate.py                                    # üretimdeki model
  python evaluate.py --model incidelen/bert-base-turkish-sentiment-analysis-cased
"""

import argparse
import random
from collections import Counter

from datasets import load_dataset

random.seed(42)

N_POZITIF_NEGATIF = 200
N_NOTR = 100

LABEL_ALIASES = {
    "positive": "Positive", "pozitif": "Positive", "olumlu": "Positive",
    "negative": "Negative", "negatif": "Negative", "olumsuz": "Negative",
    "neutral": "Notr", "notr": "Notr", "nötr": "Notr",
}


def normalize(label: str) -> str:
    return LABEL_ALIASES.get(label.strip().lower(), label)


def orneklem_olustur():
    ds = load_dataset("winvoker/turkish-sentiment-analysis-dataset")["train"]

    urun_yorumlari = ds.filter(lambda x: x["dataset"] in ("urun_yorumlari", "magaza_yorumlari"))
    pozitif = urun_yorumlari.filter(lambda x: x["label"] == "Positive")
    negatif = urun_yorumlari.filter(lambda x: x["label"] == "Negative")
    notr = ds.filter(lambda x: x["label"] == "Notr")

    def rastgele_sec(bolum, n):
        idx = random.sample(range(len(bolum)), min(n, len(bolum)))
        return [bolum[i] for i in idx]

    ornekler = (
        rastgele_sec(pozitif, N_POZITIF_NEGATIF)
        + rastgele_sec(negatif, N_POZITIF_NEGATIF)
        + rastgele_sec(notr, N_NOTR)
    )
    random.shuffle(ornekler)
    return ornekler


def degerlendir(ornekler, tahmin_et):
    dogru = 0
    karisiklik = Counter()  # (gercek_etiket, tahmin_etiket) -> sayı
    sinif_toplam = Counter()
    sinif_dogru = Counter()

    for i, ornek in enumerate(ornekler, 1):
        gercek = ornek["label"]
        metin = ornek["text"][:512]
        tahmin_label = normalize(tahmin_et(metin))

        sinif_toplam[gercek] += 1
        karisiklik[(gercek, tahmin_label)] += 1
        if tahmin_label == gercek:
            dogru += 1
            sinif_dogru[gercek] += 1

        if i % 50 == 0:
            print(f"  {i}/{len(ornekler)} işlendi...")

    return dogru, karisiklik, sinif_toplam, sinif_dogru


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=None,
                         help="Karşılaştırılacak HuggingFace model adı. Verilmezse üretimdeki model (sentiment.py) test edilir.")
    args = parser.parse_args()

    if args.model:
        from transformers import pipeline
        print(f"Model yükleniyor: {args.model} ...")
        pipe = pipeline("sentiment-analysis", model=args.model)
        tahmin_et = lambda metin: pipe(metin)[0]["label"]
        model_adi = args.model
    else:
        from sentiment import analiz_et
        tahmin_et = lambda metin: analiz_et(metin)["etiket"]
        model_adi = "cardiffnlp/twitter-xlm-roberta-base-sentiment (üretimdeki model)"

    print("Değerlendirme örneklemi hazırlanıyor...")
    ornekler = orneklem_olustur()
    print(f"Model: {model_adi}")
    print(f"Toplam {len(ornekler)} örnek üzerinde değerlendiriliyor "
          f"({N_POZITIF_NEGATIF} olumlu + {N_POZITIF_NEGATIF} olumsuz [gerçek ürün yorumu] "
          f"+ {N_NOTR} nötr [Wikipedia, bu veri setinde ürün yorumu kaynaklı nötr yok])...\n")

    dogru, karisiklik, sinif_toplam, sinif_dogru = degerlendir(ornekler, tahmin_et)
    toplam = len(ornekler)

    print(f"\nGenel doğruluk: {dogru}/{toplam} = %{100 * dogru / toplam:.1f}\n")

    print("Sınıf bazında recall (gerçek sınıf doğru tahmin edilme oranı):")
    for sinif in ["Positive", "Notr", "Negative"]:
        t = sinif_toplam.get(sinif, 0)
        d = sinif_dogru.get(sinif, 0)
        oran = 100 * d / t if t else 0
        print(f"  {sinif:9s}: {d:4d}/{t:<4d} = %{oran:.1f}")

    print("\nKarışıklık matrisi (gerçek -> tahmin : adet):")
    for (gercek, tahmin), adet in sorted(karisiklik.items(), key=lambda x: -x[1]):
        isaret = "  " if gercek == tahmin else "✗ "
        print(f"  {isaret}{gercek:9s} -> {tahmin:9s} : {adet}")



if __name__ == "__main__":
    main()
