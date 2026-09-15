"""
finetune2.py'nin ayırdığı TRSAv1 held-out setiyle (gerçek ürün yorumu,
gerçek nötr örnekler içerir) bir modeli değerlendirir. evaluate.py'nin
aksine, nötr örnekler burada Wikipedia değil, gerçek ürün yorumu —
bu yüzden "gerçek dünya nötr tespiti" sorusuna evaluate.py'den daha
güvenilir bir cevap verir.

Çalıştırmak için:
  python evaluate_trsav1.py --model ./duygu_finetuned_v2
  python evaluate_trsav1.py --model ./duygu_finetuned      # 1. tur ile kıyas
  python evaluate_trsav1.py                                 # üretimdeki model
"""

import argparse
import json
from collections import Counter

HELD_OUT_DOSYA = "./trsav1_held_out.json"

LABEL_ALIASES = {
    "positive": "Positive", "pozitif": "Positive", "olumlu": "Positive",
    "negative": "Negative", "negatif": "Negative", "olumsuz": "Negative",
    "neutral": "Neutral", "notr": "Neutral", "nötr": "Neutral",
}


def normalize(label: str) -> str:
    return LABEL_ALIASES.get(label.strip().lower(), label)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=None)
    args = parser.parse_args()

    with open(HELD_OUT_DOSYA, encoding="utf-8") as f:
        ornekler = json.load(f)

    if args.model:
        from transformers import pipeline
        print(f"Model yükleniyor: {args.model} ...")
        pipe = pipeline("sentiment-analysis", model=args.model)
        tahmin_et = lambda metin: pipe(metin)[0]["label"]
        model_adi = args.model
    else:
        from sentiment import analiz_et
        tahmin_et = lambda metin: analiz_et(metin)["etiket"]
        model_adi = "üretimdeki model (sentiment.py)"

    print(f"Model: {model_adi}")
    print(f"TRSAv1 held-out setinde {len(ornekler)} gerçek ürün yorumu ile değerlendiriliyor...\n")

    dogru = 0
    karisiklik = Counter()
    sinif_toplam = Counter()
    sinif_dogru = Counter()

    for i, ornek in enumerate(ornekler, 1):
        gercek = ornek["label"]
        metin = ornek["text"][:512]
        tahmin_label = normalize(tahmin_et(metin.lower()))

        sinif_toplam[gercek] += 1
        karisiklik[(gercek, tahmin_label)] += 1
        if tahmin_label == gercek:
            dogru += 1
            sinif_dogru[gercek] += 1

        if i % 50 == 0:
            print(f"  {i}/{len(ornekler)} işlendi...")

    toplam = len(ornekler)
    print(f"\nGenel doğruluk: {dogru}/{toplam} = %{100 * dogru / toplam:.1f}\n")

    print("Sınıf bazında recall:")
    for sinif in ["Positive", "Neutral", "Negative"]:
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
