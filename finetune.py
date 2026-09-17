"""
Fine-tunes cardiffnlp/twitter-xlm-roberta-base-sentiment on the
winvoker/turkish-sentiment-analysis-dataset, quickly and with weight
skewed toward the negative class (one epoch, ~15-20K examples).

Only a single final model is saved to disk (NO intermediate checkpoints,
no optimizer state is saved) — see .claude/skills/run-duygu-analizi/SKILL.md.

The 500-example test set used by evaluate.py (same seed=42, same sampling
order) is EXCLUDED here to avoid leakage — so evaluate.py, unchanged, can
give a fair before/after fine-tuning comparison.

Run with: python finetune.py
Output: ./duygu_finetuned/ (new model, ~1.1-1.3GB)
"""

import random
import time

import numpy as np
from datasets import load_dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

BASE_MODEL = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
CIKTI_DIZINI = "./duygu_finetuned"

N_NEGATIF = 8000
N_POZITIF = 5000
N_NOTR = 3000

LABEL2ID = {"negative": 0, "neutral": 1, "positive": 2}
DATASET_LABEL_TO_MODEL = {"Negative": "negative", "Notr": "neutral", "Positive": "positive"}


def evaluate_py_ile_ayni_orneklem_indeksleri(pozitif, negatif, notr):
    """Samples with the EXACT same order and seed as evaluate.py's
    orneklem_olustur(), and returns which indices were used for eval —
    we'll exclude these from training."""
    random.seed(42)

    def rastgele_sec_idx(bolum, n):
        return set(random.sample(range(len(bolum)), min(n, len(bolum))))

    pozitif_idx = rastgele_sec_idx(pozitif, 200)
    negatif_idx = rastgele_sec_idx(negatif, 200)
    notr_idx = rastgele_sec_idx(notr, 100)
    return pozitif_idx, negatif_idx, notr_idx


def main():
    t0 = time.time()
    print("Veri seti yükleniyor...")
    ds = load_dataset("winvoker/turkish-sentiment-analysis-dataset")["train"]
    urun = ds.filter(lambda x: x["dataset"] in ("urun_yorumlari", "magaza_yorumlari"))
    pozitif = urun.filter(lambda x: x["label"] == "Positive")
    negatif = urun.filter(lambda x: x["label"] == "Negative")
    notr = ds.filter(lambda x: x["label"] == "Notr")

    # Determine the 500 examples used by evaluate.py (to prevent leakage)
    eval_poz_idx, eval_neg_idx, eval_notr_idx = evaluate_py_ile_ayni_orneklem_indeksleri(
        pozitif, negatif, notr
    )
    print(f"evaluate.py'nin test setiyle çakışmaması için hariç tutulan: "
          f"{len(eval_poz_idx)} olumlu, {len(eval_neg_idx)} olumsuz, {len(eval_notr_idx)} nötr")

    # Training pool = everything else not used in eval
    random.seed(7)  # a different seed for the training sample

    def egitim_havuzu_sec(bolum, haric_idx, n):
        aday = [i for i in range(len(bolum)) if i not in haric_idx]
        secilen = random.sample(aday, min(n, len(aday)))
        return [bolum[i]["text"][:512] for i in secilen]

    negatif_metinler = egitim_havuzu_sec(negatif, eval_neg_idx, N_NEGATIF)
    pozitif_metinler = egitim_havuzu_sec(pozitif, eval_poz_idx, N_POZITIF)
    notr_metinler = egitim_havuzu_sec(notr, eval_notr_idx, N_NOTR)

    metinler = negatif_metinler + pozitif_metinler + notr_metinler
    etiketler = (
        [LABEL2ID["negative"]] * len(negatif_metinler)
        + [LABEL2ID["positive"]] * len(pozitif_metinler)
        + [LABEL2ID["neutral"]] * len(notr_metinler)
    )
    metinler = [m.lower() for m in metinler]  # preprocessing consistent with the production code

    birlesik = list(zip(metinler, etiketler))
    random.shuffle(birlesik)
    metinler, etiketler = zip(*birlesik)
    print(f"Eğitim örneklemi: {len(metinler)} örnek "
          f"({len(negatif_metinler)} olumsuz, {len(pozitif_metinler)} olumlu, {len(notr_metinler)} nötr)")

    print(f"Taban model yükleniyor: {BASE_MODEL} ...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(BASE_MODEL)

    from datasets import Dataset
    egitim_ds = Dataset.from_dict({"text": list(metinler), "label": list(etiketler)})

    def tokenize_et(ornekler):
        return tokenizer(ornekler["text"], truncation=True, max_length=128, padding="max_length")

    egitim_ds = egitim_ds.map(tokenize_et, batched=True)
    egitim_ds = egitim_ds.remove_columns(["text"])
    egitim_ds.set_format("torch")

    training_args = TrainingArguments(
        output_dir="./_egitim_gecici",  # nothing gets written here since save_strategy="no"
        num_train_epochs=1,
        per_device_train_batch_size=16,
        learning_rate=2e-5,
        logging_steps=50,
        save_strategy="no",       # NO intermediate checkpoints — critical for disk safety
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
