"""Compares a candidate model against production v5 on the gold test set."""

import argparse
import json
from collections import Counter
from pathlib import Path

from transformers import pipeline


KOK = Path(__file__).parent
ETIKET_MAP = {
    "positive": "olumlu", "neutral": "nötr", "negative": "olumsuz",
    "LABEL_2": "olumlu", "LABEL_1": "nötr", "LABEL_0": "olumsuz",
}
SINIFLAR = ("olumlu", "nötr", "olumsuz")


def tahmin_et(model_yolu: str, metinler: list[str]) -> list[str]:
    model = pipeline("sentiment-analysis", model=model_yolu)
    sonuclar = model([m.lower() for m in metinler], batch_size=16, truncation=True, max_length=512)
    return [ETIKET_MAP[sonuc["label"]] for sonuc in sonuclar]


def metrikler(gercek: list[str], tahmin: list[str]) -> dict:
    sonuc = {"dogruluk": sum(g == t for g, t in zip(gercek, tahmin)) / len(gercek), "siniflar": {}}
    for sinif in SINIFLAR:
        tp = sum(g == sinif and t == sinif for g, t in zip(gercek, tahmin))
        fp = sum(g != sinif and t == sinif for g, t in zip(gercek, tahmin))
        fn = sum(g == sinif and t != sinif for g, t in zip(gercek, tahmin))
        precision = tp / (tp + fp) if tp + fp else 0
        recall = tp / (tp + fn) if tp + fn else 0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
        sonuc["siniflar"][sinif] = {"precision": precision, "recall": recall, "f1": f1}
    return sonuc


def yazdir(ad: str, sonuc: dict) -> None:
    print(f"\n{ad}: doğruluk %{sonuc['dogruluk'] * 100:.1f}")
    print(f"  {'Sınıf':10} {'Precision':>10} {'Recall':>10} {'F1':>10}")
    for sinif in SINIFLAR:
        m = sonuc["siniflar"][sinif]
        print(f"  {sinif:10} %{m['precision'] * 100:8.1f} %{m['recall'] * 100:8.1f} %{m['f1'] * 100:8.1f}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uretim", default="./duygu_finetuned_v5_full")
    parser.add_argument("--aday", default="./duygu_finetuned_v6_full")
    parser.add_argument("--gold", type=Path, default=KOK / "gold_test_seti.json")
    args = parser.parse_args()

    with args.gold.open(encoding="utf-8") as dosya:
        veri = json.load(dosya)
    metinler = [o["text"] for o in veri]
    gercek = [o["label"] for o in veri]
    print(f"Gold set: {len(veri)} örnek · dağılım {dict(Counter(gercek))}")

    uretim = metrikler(gercek, tahmin_et(args.uretim, metinler))
    aday = metrikler(gercek, tahmin_et(args.aday, metinler))
    yazdir("Üretim modeli", uretim)
    yazdir("Aday model", aday)

    fark = (aday["dogruluk"] - uretim["dogruluk"]) * 100
    notr_fark = (aday["siniflar"]["nötr"]["recall"] - uretim["siniflar"]["nötr"]["recall"]) * 100
    gecti = fark >= 0 and notr_fark >= 0 and all(
        aday["siniflar"][s]["recall"] >= uretim["siniflar"][s]["recall"] - 0.02 for s in SINIFLAR
    )
    print(f"\nFark: doğruluk {fark:+.1f} puan · nötr recall {notr_fark:+.1f} puan")
    print("Karar:", "ADAY ÜRETİME UYGUN" if gecti else "ADAY REDDEDİLDİ")


if __name__ == "__main__":
    main()
