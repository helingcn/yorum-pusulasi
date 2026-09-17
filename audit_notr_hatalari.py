"""Writes model disagreements on TRSAv1 neutral labels to an audit CSV.

The model's prediction is only a suggestion. The ``manuel_etiket`` and
``inceleme_notu`` fields are not used for training purposes until a human
has filled them in.
"""

import csv
import json
from pathlib import Path

from sentiment import toplu_analiz


KAYNAK = Path(__file__).parent / "trsav1_held_out.json"
CIKTI = Path(__file__).parent / "notr_hata_denetimi.csv"


def main() -> None:
    with KAYNAK.open(encoding="utf-8") as dosya:
        ornekler = json.load(dosya)

    notr_ornekler = [ornek for ornek in ornekler if ornek["label"] == "Neutral"]
    sonuclar = toplu_analiz([ornek["text"] for ornek in notr_ornekler])

    uyusmazliklar = []
    for sira, (ornek, sonuc) in enumerate(zip(notr_ornekler, sonuclar), start=1):
        if sonuc["etiket"] == "nötr":
            continue
        uyusmazliklar.append({
            "id": f"NOTR-{sira:03d}",
            "yorum": ornek["text"],
            "mevcut_etiket": "nötr",
            "model_tahmini": sonuc["etiket"],
            "guven": sonuc["guven"],
            "onerilen_etiket": sonuc["etiket"],
            "manuel_etiket": "",
            "inceleme_notu": "",
        })

    alanlar = [
        "id", "yorum", "mevcut_etiket", "model_tahmini", "guven",
        "onerilen_etiket", "manuel_etiket", "inceleme_notu",
    ]
    with CIKTI.open("w", encoding="utf-8-sig", newline="") as dosya:
        yazici = csv.DictWriter(dosya, fieldnames=alanlar)
        yazici.writeheader()
        yazici.writerows(uyusmazliklar)

    olumlu = sum(satir["model_tahmini"] == "olumlu" for satir in uyusmazliklar)
    olumsuz = sum(satir["model_tahmini"] == "olumsuz" for satir in uyusmazliklar)
    print(f"Denetim dosyası: {CIKTI}")
    print(f"Toplam uyuşmazlık: {len(uyusmazliklar)} (olumlu: {olumlu}, olumsuz: {olumsuz})")
    print("'manuel_etiket' alanına yalnızca olumlu, nötr veya olumsuz yazın.")


if __name__ == "__main__":
    main()
