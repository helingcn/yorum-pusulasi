"""Training-independent regression evaluation for short/direct reviews.

Usage:
  python evaluate_kisa_yorumlar.py                 # production v3
  python evaluate_kisa_yorumlar.py --model ./duygu_finetuned_v4
"""

import argparse
import json
from collections import Counter


DOSYA = "./kisa_yorum_regresyon.json"
SINIFLAR = ("positive", "neutral", "negative")
ALIAS = {
    "positive": "positive", "olumlu": "positive", "label_2": "positive",
    "neutral": "neutral", "nötr": "neutral", "notr": "neutral", "label_1": "neutral",
    "negative": "negative", "olumsuz": "negative", "label_0": "negative",
}


def normalize(etiket: str) -> str:
    return ALIAS.get(etiket.lower().strip(), etiket.lower().strip())


def metrikleri_yaz(gercekler: list[str], tahminler: list[str]) -> None:
    print("\nSınıf bazında metrikler:")
    print(f"  {'Sınıf':10} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Destek':>8}")
    f1ler = []
    for sinif in SINIFLAR:
        tp = sum(g == sinif and t == sinif for g, t in zip(gercekler, tahminler))
        fp = sum(g != sinif and t == sinif for g, t in zip(gercekler, tahminler))
        fn = sum(g == sinif and t != sinif for g, t in zip(gercekler, tahminler))
        destek = sum(g == sinif for g in gercekler)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        f1ler.append(f1)
        print(f"  {sinif:10} %{precision * 100:8.1f} %{recall * 100:8.1f} %{f1 * 100:8.1f} {destek:8d}")
    print(f"  {'Macro F1':10} {'':>10} {'':>10} %{sum(f1ler) / len(f1ler) * 100:8.1f}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", help="Model folder to evaluate")
    args = parser.parse_args()

    with open(DOSYA, encoding="utf-8") as f:
        ornekler = json.load(f)

    if args.model:
        from transformers import pipeline
        pipe = pipeline("sentiment-analysis", model=args.model)
        tahmin_et = lambda metin: normalize(pipe(metin.lower())[0]["label"])
        model_adi = args.model
    else:
        from sentiment import analiz_et
        tahmin_et = lambda metin: normalize(analiz_et(metin)["etiket"])
        model_adi = "production model (sentiment.py)"

    gercekler = [ornek["label"] for ornek in ornekler]
    tahminler = [tahmin_et(ornek["text"]) for ornek in ornekler]
    dogru = sum(g == t for g, t in zip(gercekler, tahminler))

    print(f"Model: {model_adi}")
    print(f"Kısa yorum regresyon seti: {len(ornekler)} örnek")
    print(f"Doğruluk: {dogru}/{len(ornekler)} = %{dogru / len(ornekler) * 100:.1f}")
    metrikleri_yaz(gercekler, tahminler)

    hatalar = [(o["text"], g, t) for o, g, t in zip(ornekler, gercekler, tahminler) if g != t]
    print(f"\nHatalar ({len(hatalar)}):")
    for metin, gercek, tahmin in hatalar:
        print(f"  {gercek:8} -> {tahmin:8} | {metin}")


if __name__ == "__main__":
    main()
