"""
Round 2 fine-tuning: trains the cardiffnlp base model on TRSAv1
(maydogan/Turkish_SentimentAnalysis_TRSAv1) with a BALANCED distribution.

Difference from round 1 (finetune.py): in round 1, the neutral examples
came from the winvoker dataset and were all Wikipedia-sourced (not real
product reviews) — which caused a regression in real-world neutral
detection (confirmed via test_sentiment.py and manual testing). TRSAv1's
neutral examples are REAL product reviews (hedged phrasing like "not bad
but...", "may vary by skin type"), so this round uses a balanced
distribution (6000+6000+6000).

We start over from the base model (not duygu_finetuned, the original
cardiffnlp) — to avoid accumulating any odd side effects from round 1.

Only a single final model is saved to disk. Output is ./duygu_finetuned_v2
— the existing ./duygu_finetuned (round 1) is not deleted, since we'll
test both against evaluate.py + the TRSAv1 held-out set and decide which
one to use based on that.

Run with: python finetune2.py
"""

import random
import time

from datasets import Dataset, load_dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

BASE_MODEL = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
CIKTI_DIZINI = "./duygu_finetuned_v2"
HELD_OUT_DOSYA = "./trsav1_held_out.json"  # examples set aside for later evaluation

N_EGITIM_SINIF_BASI = 6000
N_HELD_OUT_SINIF_BASI = 150

LABEL2ID = {"negative": 0, "neutral": 1, "positive": 2}
TRSAV1_LABEL_TO_MODEL = {"Negative": "negative", "Neutral": "neutral", "Positive": "positive"}


def main():
    t0 = time.time()
    print("TRSAv1 veri seti yükleniyor...")
    ds = load_dataset("maydogan/Turkish_SentimentAnalysis_TRSAv1")["train"]

    random.seed(99)  # different from finetune.py's seeds, so they don't mix

    egitim_metin, egitim_etiket = [], []
    held_out = []  # {"text":..., "label":...} — for later evaluation

    for sinif_ds_label, model_label in TRSAV1_LABEL_TO_MODEL.items():
        alt_kume = ds.filter(lambda x, s=sinif_ds_label: x["score"] == s)
        idx = list(range(len(alt_kume)))
        random.shuffle(idx)

        held_out_idx = idx[:N_HELD_OUT_SINIF_BASI]
        egitim_idx = idx[N_HELD_OUT_SINIF_BASI:N_HELD_OUT_SINIF_BASI + N_EGITIM_SINIF_BASI]

        for i in held_out_idx:
            held_out.append({"text": alt_kume[i]["review"], "label": sinif_ds_label})
        for i in egitim_idx:
            egitim_metin.append(alt_kume[i]["review"][:512].lower())
            egitim_etiket.append(LABEL2ID[model_label])

        print(f"  {sinif_ds_label}: {len(egitim_idx)} eğitim, {len(held_out_idx)} held-out")

    import json
    with open(HELD_OUT_DOSYA, "w", encoding="utf-8") as f:
        json.dump(held_out, f, ensure_ascii=False)
    print(f"Held-out değerlendirme seti kaydedildi: {HELD_OUT_DOSYA} ({len(held_out)} örnek)")

    birlesik = list(zip(egitim_metin, egitim_etiket))
    random.shuffle(birlesik)
    egitim_metin, egitim_etiket = zip(*birlesik)
    print(f"\nEğitim örneklemi: {len(egitim_metin)} örnek (sınıf başına dengeli, ~{N_EGITIM_SINIF_BASI})")

    print(f"Taban model yükleniyor: {BASE_MODEL} ...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(BASE_MODEL)

    egitim_ds = Dataset.from_dict({"text": list(egitim_metin), "label": list(egitim_etiket)})

    def tokenize_et(ornekler):
        return tokenizer(ornekler["text"], truncation=True, max_length=128, padding="max_length")

    egitim_ds = egitim_ds.map(tokenize_et, batched=True)
    egitim_ds = egitim_ds.remove_columns(["text"])
    egitim_ds.set_format("torch")

    training_args = TrainingArguments(
        output_dir="./_egitim_gecici_v2",
        num_train_epochs=1,
        per_device_train_batch_size=16,
        learning_rate=2e-5,
        logging_steps=50,
        save_strategy="no",
        report_to=[],
        disable_tqdm=False,
    )

    trainer = Trainer(model=model, args=training_args, train_dataset=egitim_ds)

    print("\nEğitim başlıyor...\n")
    trainer.train()

    print(f"\nEğitim tamamlandı, model kaydediliyor: {CIKTI_DIZINI}")
    trainer.save_model(CIKTI_DIZINI)
    tokenizer.save_pretrained(CIKTI_DIZINI)

    sure = time.time() - t0
    print(f"\nToplam süre: {sure/60:.1f} dakika")


if __name__ == "__main__":
    main()
