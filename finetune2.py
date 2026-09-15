"""
2. tur fine-tuning: cardiffnlp taban modelini TRSAv1 (maydogan/Turkish_
SentimentAnalysis_TRSAv1) üzerinde, DENGELİ bir dağılımla eğitir.

1. turdan (finetune.py) farkı: 1. turda nötr örnekler winvoker veri setinden
geliyordu ve hepsi Wikipedia kaynaklıydı (gerçek ürün yorumu değil) — bu da
gerçek dünya nötr tespitinde gerilemeye yol açtı (test_sentiment.py ve elle
testlerle doğrulandı). TRSAv1'in nötr örnekleri GERÇEK ürün yorumları
("fena değil ama...", "cilt tipine göre değişebilir" gibi çekimser
ifadeler), bu yüzden bu turda dengeli bir dağılım (6000+6000+6000) kullanıyoruz.

Taban modelden (duygu_finetuned değil, orijinal cardiffnlp) yeniden
başlıyoruz — 1. turun olası tuhaf yan etkilerini biriktirmemek için.

Diskte sadece tek final model kaydedilir. Çıktı ./duygu_finetuned_v2 —
mevcut ./duygu_finetuned (1. tur) karşılaştırma için silinmiyor, ikisini de
evaluate.py + TRSAv1 held-out setiyle test edip hangisini kullanacağımıza
öyle karar vereceğiz.

Çalıştırmak için: python finetune2.py
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
HELD_OUT_DOSYA = "./trsav1_held_out.json"  # sonraki değerlendirme için ayrılan örnekler

N_EGITIM_SINIF_BASI = 6000
N_HELD_OUT_SINIF_BASI = 150

LABEL2ID = {"negative": 0, "neutral": 1, "positive": 2}
TRSAV1_LABEL_TO_MODEL = {"Negative": "negative", "Neutral": "neutral", "Positive": "positive"}


def main():
    t0 = time.time()
    print("TRSAv1 veri seti yükleniyor...")
    ds = load_dataset("maydogan/Turkish_SentimentAnalysis_TRSAv1")["train"]

    random.seed(99)  # finetune.py'deki seed'lerden farklı, karışmasın

    egitim_metin, egitim_etiket = [], []
    held_out = []  # {"text":..., "label":...} — sonraki değerlendirme için

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
