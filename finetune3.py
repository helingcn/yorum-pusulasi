"""
3. tur fine-tuning: finetune2.py (v2) ile aynı olumlu/olumsuz verisi (TRSAv1,
6000/sınıf), ama nötr sınıfına gerçek TRSAv1 örneklerinin yanına sentetik
"prosedürel nötr" cümleler de karıştırılıyor (sentetik_notr.py).

Neden: v2'de "sipariş verildi", "kutunun içinde X vardı", "fatura",
"fotoğraftakiyle aynı" gibi saf işlemsel/nesnel cümleler hâlâ olumsuza
kayıyordu (bkz. SKILL.md Gotchas). Kök neden: gerçek yorum verisinde saf
prosedürel nötr cümleler zaten nadir (insanlar yorum yazınca genelde bir
fikir de ekliyor) — TRSAv1'in tamamında bile az. Gerçek veride bulmak yerine
şablonla üretip çeşitlendirerek bu boşluğu dolduruyoruz.

Nötr karışımı: 4500 gerçek TRSAv1 + 1500 sentetik = 6000 (v2 ile aynı
toplam boyut, adil karşılaştırma için).

Bu sürüm ayrıca kısa/doğrudan yorum hata sınıfı için 216 hedefli örnek ekler.
Çıktı: ./duygu_finetuned_v5_full — üretimdeki v4 silinmez; aday model ancak
ayrı regresyon seti ve TRSAv1 held-out değerlendirmesini geçerse üretime alınır.

Çalıştırmak için: python finetune3.py
"""

import json
import random
import time

from datasets import Dataset, load_dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

from sentetik_notr import uret as sentetik_uret
from hedefli_kisa_yorumlar import egitim_ornekleri as hedefli_kisa_yorumlar

BASE_MODEL = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
CIKTI_DIZINI = "./duygu_finetuned_v5_full"
HELD_OUT_DOSYA = "./trsav1_held_out.json"  # finetune2.py ile AYNI dosya/mantık — tutarlı karşılaştırma
KISA_REGRESYON_DOSYA = "./kisa_yorum_regresyon.json"

N_EGITIM_SINIF_BASI = 6000
N_HELD_OUT_SINIF_BASI = 150
N_SENTETIK_NOTR = 1500  # 6000 nötr içindeki sentetik pay; kalan 4500 gerçek TRSAv1

LABEL2ID = {"negative": 0, "neutral": 1, "positive": 2}
TRSAV1_LABEL_TO_MODEL = {"Negative": "negative", "Neutral": "neutral", "Positive": "positive"}


def main(ek_hedefli_ornekler=None, cikti_dizini=CIKTI_DIZINI, gecici_dizin="./_egitim_gecici_v3"):
    t0 = time.time()
    print("TRSAv1 veri seti yükleniyor...")
    ds = load_dataset("maydogan/Turkish_SentimentAnalysis_TRSAv1")["train"]

    random.seed(99)  # finetune2.py ile AYNI seed -> AYNI held-out/eğitim ayrımı (tutarlılık)

    egitim_metin, egitim_etiket = [], []
    held_out = []

    for sinif_ds_label, model_label in TRSAV1_LABEL_TO_MODEL.items():
        alt_kume = ds.filter(lambda x, s=sinif_ds_label: x["score"] == s)
        idx = list(range(len(alt_kume)))
        random.shuffle(idx)

        held_out_idx = idx[:N_HELD_OUT_SINIF_BASI]
        n_gercek = N_EGITIM_SINIF_BASI - N_SENTETIK_NOTR if sinif_ds_label == "Neutral" else N_EGITIM_SINIF_BASI
        egitim_idx = idx[N_HELD_OUT_SINIF_BASI:N_HELD_OUT_SINIF_BASI + n_gercek]

        for i in held_out_idx:
            held_out.append({"text": alt_kume[i]["review"], "label": sinif_ds_label})
        for i in egitim_idx:
            egitim_metin.append(alt_kume[i]["review"][:512].lower())
            egitim_etiket.append(LABEL2ID[model_label])

        print(f"  {sinif_ds_label}: {len(egitim_idx)} gerçek eğitim, {len(held_out_idx)} held-out")

    sentetik_cumleler = sentetik_uret(N_SENTETIK_NOTR, seed=42)
    for c in sentetik_cumleler:
        egitim_metin.append(c.lower())
        egitim_etiket.append(LABEL2ID["neutral"])
    print(f"  Neutral: +{len(sentetik_cumleler)} sentetik prosedürel cümle eklendi")

    hedefli_ornekler = hedefli_kisa_yorumlar()
    with open(KISA_REGRESYON_DOSYA, encoding="utf-8") as f:
        regresyon_ornekleri = json.load(f)
    hedefli_metinler = {ornek["text"].lower().strip() for ornek in hedefli_ornekler}
    regresyon_metinler = {ornek["text"].lower().strip() for ornek in regresyon_ornekleri}
    cakisma = hedefli_metinler & regresyon_metinler
    if cakisma:
        raise ValueError(f"Eğitim ve regresyon seti çakışıyor: {sorted(cakisma)}")
    for ornek in hedefli_ornekler:
        egitim_metin.append(ornek["text"].lower())
        egitim_etiket.append(LABEL2ID[ornek["label"]])
    print(f"  Hedefli kısa yorumlar: +{len(hedefli_ornekler)} örnek (regresyon setiyle çakışmasız)")

    if ek_hedefli_ornekler:
        normal = lambda metin: metin.casefold().strip().rstrip(".")
        ek_metinler = {normal(ornek["text"]) for ornek in ek_hedefli_ornekler}
        korunan_metinler = {normal(ornek["text"]) for ornek in regresyon_ornekleri + held_out}
        mevcut_hedefli = {normal(ornek["text"]) for ornek in hedefli_ornekler}
        if ek_metinler & korunan_metinler:
            raise ValueError("Ek hedefli eğitim verisi değerlendirme setiyle çakışıyor.")
        if ek_metinler & mevcut_hedefli:
            raise ValueError("Ek hedefli eğitim verisi mevcut hedefli veriyle çakışıyor.")
        for ornek in ek_hedefli_ornekler:
            egitim_metin.append(ornek["text"].lower())
            egitim_etiket.append(LABEL2ID[ornek["label"]])
        print(f"  Ek hedefli karşıt örnekler: +{len(ek_hedefli_ornekler)} örnek (çakışmasız)")

    with open(HELD_OUT_DOSYA, "w", encoding="utf-8") as f:
        json.dump(held_out, f, ensure_ascii=False)
    print(f"Held-out değerlendirme seti kaydedildi: {HELD_OUT_DOSYA} ({len(held_out)} örnek, finetune2.py ile aynı)")

    birlesik = list(zip(egitim_metin, egitim_etiket))
    random.shuffle(birlesik)
    egitim_metin, egitim_etiket = zip(*birlesik)
    print(f"\nEğitim örneklemi: {len(egitim_metin)} örnek")

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
        output_dir=gecici_dizin,
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

    print(f"\nEğitim tamamlandı, model kaydediliyor: {cikti_dizini}")
    trainer.save_model(cikti_dizini)
    tokenizer.save_pretrained(cikti_dizini)

    sure = time.time() - t0
    print(f"\nToplam süre: {sure/60:.1f} dakika")


if __name__ == "__main__":
    main()
