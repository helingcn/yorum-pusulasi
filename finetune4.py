"""Fine-tunes v3 as a corrective for the short/direct-review error class.

Uses only 222 targeted, balanced examples instead of re-teaching v3's
general TRSAv1 knowledge. Output is written to a new v4 folder; it's not
promoted to production until evaluations are complete.
"""

import json

from datasets import Dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer, Trainer, TrainingArguments

from hedefli_kisa_yorumlar import egitim_ornekleri

KAYNAK_MODEL = "./duygu_finetuned_v3"
CIKTI_DIZINI = "./duygu_finetuned_v4"
REGRESYON_DOSYA = "./kisa_yorum_regresyon.json"
LABEL2ID = {"negative": 0, "neutral": 1, "positive": 2}


def main():
    ornekler = egitim_ornekleri()
    with open(REGRESYON_DOSYA, encoding="utf-8") as f:
        regresyon = json.load(f)
    egitim_metinleri = {o["text"].lower().strip() for o in ornekler}
    regresyon_metinleri = {o["text"].lower().strip() for o in regresyon}
    if egitim_metinleri & regresyon_metinleri:
        raise ValueError("Eğitim ve regresyon kümeleri çakışıyor.")

    print(f"v3 modeli yükleniyor: {KAYNAK_MODEL}")
    tokenizer = AutoTokenizer.from_pretrained(KAYNAK_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(KAYNAK_MODEL)
    ds = Dataset.from_dict({
        "text": [o["text"].lower() for o in ornekler],
        "label": [LABEL2ID[o["label"]] for o in ornekler],
    })

    def tokenize(ornek):
        return tokenizer(ornek["text"], truncation=True, max_length=128, padding="max_length")

    ds = ds.map(tokenize, batched=True).remove_columns(["text"])
    ds.set_format("torch")
    args = TrainingArguments(
        output_dir="./_egitim_gecici_v4",
        num_train_epochs=3,
        per_device_train_batch_size=8,
        learning_rate=5e-6,
        save_strategy="no",
        logging_steps=10,
        report_to=[],
        disable_tqdm=False,
    )
    print(f"{len(ornekler)} hedefli örnekle düzeltici eğitim başlıyor...")
    Trainer(model=model, args=args, train_dataset=ds).train()
    model.save_pretrained(CIKTI_DIZINI)
    tokenizer.save_pretrained(CIKTI_DIZINI)
    print(f"Yeni model kaydedildi: {CIKTI_DIZINI}")


if __name__ == "__main__":
    main()
