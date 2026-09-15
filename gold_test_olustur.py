"""Manuel denetim CSV'sini TRSAv1 held-out setine işleyerek gold set üretir."""

import argparse
import csv
import json
from pathlib import Path


KOK = Path(__file__).parent
VARSAYILAN_HELD_OUT = KOK / "trsav1_held_out.json"
VARSAYILAN_CIKTI = KOK / "gold_test_seti.json"
GECERLI = {"olumlu", "nötr", "olumsuz"}
ETIKET_MAP = {"Positive": "olumlu", "Neutral": "nötr", "Negative": "olumsuz"}


def denetimi_oku(yol: Path) -> list[dict]:
    with yol.open(encoding="utf-8-sig", newline="") as dosya:
        ilk_satir = dosya.readline()
        baslik = ilk_satir if "manuel_etiket" in ilk_satir else dosya.readline()
        delimiter = ";" if ";" in baslik else ","
        alanlar = next(csv.reader([baslik], delimiter=delimiter))
        satirlar = list(csv.DictReader(dosya, fieldnames=alanlar, delimiter=delimiter))
    return satirlar


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("denetim_csv", type=Path)
    parser.add_argument("--held-out", type=Path, default=VARSAYILAN_HELD_OUT)
    parser.add_argument("--output", type=Path, default=VARSAYILAN_CIKTI)
    args = parser.parse_args()

    denetim = denetimi_oku(args.denetim_csv)
    if len(denetim) != 52:
        raise ValueError(f"52 denetim satırı bekleniyordu, {len(denetim)} bulundu.")

    manuel = {}
    for satir in denetim:
        etiket = (satir.get("manuel_etiket") or "").strip().lower()
        if etiket not in GECERLI:
            raise ValueError(f"Geçersiz manuel etiket: {satir.get('id')} = {etiket!r}")
        manuel[satir["yorum"]] = etiket

    with args.held_out.open(encoding="utf-8") as dosya:
        held_out = json.load(dosya)

    gold = []
    eslesen = 0
    for ornek in held_out:
        if ornek["text"] in manuel:
            etiket = manuel[ornek["text"]]
            kaynak = "manuel_denetim"
            eslesen += 1
        else:
            etiket = ETIKET_MAP[ornek["label"]]
            kaynak = "orijinal"
        gold.append({"text": ornek["text"], "label": etiket, "label_kaynagi": kaynak})

    if eslesen != 52:
        raise ValueError(f"52 denetim yorumu eşleşmeliydi, {eslesen} eşleşti.")
    with args.output.open("w", encoding="utf-8") as dosya:
        json.dump(gold, dosya, ensure_ascii=False, indent=2)
    print(f"Gold test seti oluşturuldu: {args.output} ({len(gold)} örnek, {eslesen} manuel etiket)")


if __name__ == "__main__":
    main()
