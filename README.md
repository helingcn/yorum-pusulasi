# Türkçe Duygu Analizi Projesi

cardiffnlp/twitter-xlm-roberta-base-sentiment'in gerçek Türkçe ürün
yorumlarıyla (TRSAv1) ve sentetik prosedürel nötr cümlelerle fine-tune
edilmiş hali kullanılarak müşteri yorumlarını olumlu/nötr/olumsuz olarak
sınıflandıran bir proje.

## Kurulum

```bash
# (Önerilir) Sanal ortam oluştur
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# Bağımlılıkları kur (CPU-only, disk alanından tasarruf için)
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

## Kullanım

**Terminalden hızlı test:**

```bash
python sentiment.py
```

`./duygu_finetuned_v3` klasörü varsa onu kullanır (fine-tuned, üretimdeki
model); yoksa taban modeli (~1.1 GB) indirir.

**Web arayüzü (Streamlit — hızlı prototip sürümü):**

```bash
streamlit run app.py
```

**Web arayüzü (React — bkz. [frontend/](frontend/), önerilen/güncel sürüm):**

Streamlit'in kendi DOM yapısına bağımlı CSS/JS hackleri sürdürülemez hâle
geldiği için aynı `api.py`'ye konuşan bağımsız bir React uygulaması
yazıldı. Streamlit sürümü referans/karşılaştırma için hâlâ duruyor, ama
yeni geliştirme React tarafında yapılmalı. Kurulum: [frontend/README.md](frontend/README.md).

**Bağımsız HTTP API (FastAPI):**

```bash
uvicorn api:app --reload --port 8000
```

API başladıktan sonra interaktif Swagger dokümantasyonu
`http://localhost:8000/docs` adresinde açılır. Sağlık kontrolü için
`GET /saglik`, tek yorum için `POST /analiz`, en fazla 500 yorumluk toplu
istek için `POST /toplu-analiz` kullanılabilir. Model, uygulama açılışında
önceden yüklenir (`modeli_hazirla()`) — yüklenemezse uygulama hiç ayağa
kalkmaz (fail-fast), `/saglik` bu yüzden kozmetik değil gerçek bir hazır
olma durumu bildirir.

Eşzamanlılık: `/analiz` ve `/toplu-analiz` artık tek bir global kilit
yerine CPU çekirdek sayısı kadar eşzamanlı çıkarıma izin veren bir semafor
kullanıyor (bkz. `sentiment.py`, `_CIKARIM_SEMAFORU`) — hem `api.py` hem
`app.py` (Streamlit) aynı korumadan geçiyor, ayrı ayrı kilit yönetmiyor.

Ortam değişkenleri (üretime almadan önce ayarlanmalı):

| Değişken | Açıklama | Ayarlanmazsa |
|---|---|---|
| `API_ANAHTARI` | `/analiz` ve `/toplu-analiz` için zorunlu `X-API-Key` başlığı değeri | Kimlik doğrulama devre dışı kalır (yalnızca yerel geliştirme için güvenli), açılışta uyarı loglanır |
| `IZINLI_ORIJINLER` | Virgülle ayrılmış, CORS'a izin verilen origin listesi (örn. `https://uygulamam.com,https://panel.uygulamam.com`) | Hiçbir cross-origin istek kabul edilmez |

Rate limit: `/analiz` dakikada 30, `/toplu-analiz` dakikada 5 istekle
sınırlı (IP bazlı, `slowapi`) — aşılırsa `429` döner.

```bash
curl -X POST http://localhost:8000/analiz \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <API_ANAHTARI ile aynı değer>" \
  -d '{"metin":"Ürün bugün kargoya verildi."}'
```

Tarayıcıda açılan sayfada tek yorumu yazıp Enter'a basabilir (Shift+Enter
yeni satır açar), ya da bir CSV/Excel(.xlsx)/JSON dosyası yükleyip toplu
analiz yapabilirsin — dosyada `yorum` adında bir sütun/alan olması yeterli
(JSON için düz string listesi de kabul edilir). Toplu analiz sırasında
gerçek zamanlı ilerleme çubuğu ("47/200 yorum işlendi...") gösterilir. Tek
yorum sekmesinde hangi kelimelerin kararı etkilediği de vurgulanır, ayrıca
"Kargo hızlıydı ama kalite kötüydü" gibi karışık yorumlar **konu bazında**
(kargo/kalite/fiyat/beden/renk/müşteri hizmetleri) ayrıştırılıp ayrı ayrı
analiz edilir; toplu analizde sonuçları CSV olarak indirebilirsin.

**Testleri çalıştırmak:**

```bash
pytest test_sentiment.py test_api.py test_app.py -v
```

- `test_sentiment.py` — gerçek modeli kullanır (mock yok), `analiz_et`,
  `toplu_analiz`, `kelime_onemleri` ve `ETIKET_MAP` için 15 test
- `test_api.py` — FastAPI sözleşme testleri
- `test_app.py` — Streamlit arayüzü için `streamlit.testing.v1.AppTest` ile
  gerçek tarayıcı açmadan widget etkileşimi testleri (boş yorum uyarısı,
  analiz akışı, geri bildirim kaydı). Önceden 877+ satırlık `app.py`'nin
  hiç otomatik testi yoktu; bu dosya yazılırken bile gerçek bir çökme
  bulunup düzeltildi (`st.toast` geçersiz emoji ikonuyla çöküyordu).

## Model performansı

Model, iki ayrı test setiyle ölçüldü — biri Wikipedia kaynaklı nötr
örnekler içeriyor (winvoker), diğeri gerçek ürün yorumu (TRSAv1):

| | winvoker testi | TRSAv1 testi (gerçek yorum) |
|---|---|---|
| Taban model (fine-tune'suz) | %74.4 | %63.6 |
| v3 (3. tur, terfi etti) | %73.2 | %81.6 |

TRSAv1 testi gerçek kullanımı çok daha iyi temsil ediyor (winvoker'ın nötr
örnekleri Wikipedia cümlesi, gerçek ürün yorumu değil), ve orada taban
modele göre büyük bir kazanç var — nötr recall %13.3 → %64.0, ayrıca
"sipariş verildi", "kutunun içinde fatura vardı" gibi saf prosedürel
cümleler artık %99+ güvenle doğru sınıflandırılıyor (bkz. aşağıdaki
sınırlama notu ve `.claude/skills/run-duygu-analizi/SKILL.md` Gotchas —
3 fine-tuning turunun tam hikayesi orada).

v3'ten sonra iki tur daha yapıldı: **v4_full** ve **v5_full**, ikisi de
aynı `finetune3.py` tarifiyle (birer küçük iyileştirmeyle — hedefli kısa
yorum örnekleri) yeniden eğitilip kendi seleflerine karşı `gold_test_seti.json`
üzerinde ölçülüp geçtiler. **Üretimdeki model artık v5_full** (450 örnekli
gold sette %90.2 doğruluk, %90.7 nötr recall) — `sentiment.py` bunu ilk
sırada arar, bulamazsa v4_full'e, o da yoksa v3'e düşer (bkz.
`sentiment.py`'deki `_FINETUNED_YOL` zinciri).

Ayrıca bir **v6_full adayı** denendi (hedefli nötr karşıt örnekleriyle) ama
`model_karsilastir.py --uretim v5_full --aday v6_full` karşılaştırmasında
v5_full'ün gerisinde kaldı (doğruluk -3.1 puan, nötr recall -8.3 puan) —
**reddedildi ve silindi**. v5_full üretimde kalmaya devam ediyor.

## Dosyalar

- `sentiment.py` — Çekirdek analiz fonksiyonları (`analiz_et`, `toplu_analiz`, `kelime_onemleri`, `konu_analizi`) + paylaşılan modelin eşzamanlılık koruması (`_CIKARIM_SEMAFORU`)
- `test_sentiment.py` — Birim testleri (pytest)
- `app.py` — Streamlit web arayüzü (hızlı prototip sürümü, hâlâ duruyor ama artık aktif geliştirilmiyor)
- `test_app.py` — Streamlit arayüz testleri (`streamlit.testing.v1.AppTest`, gerçek tarayıcı gerektirmez)
- `frontend/` — React web arayüzü (önerilen/güncel sürüm) — bkz. [frontend/README.md](frontend/README.md)
- `api.py` — FastAPI HTTP API katmanı: `/analiz`, `/toplu-analiz`, `/toplu-analiz-dosya`, `/kelime-onemleri`, `/konu-analizi`, `/geri-bildirim`, `/pdf-raporu` (auth, CORS, rate limit, loglama, açılışta model ön yükleme)
- `test_api.py` — API sözleşme testleri (pytest)
- `geri_bildirim.py` — Kullanıcı geri bildirimlerini SQLite'a kaydeder/okur (`geri_bildirimler.db`) — CSV'den taşındı
- `pdf_raporu.py` — Toplu analiz için PDF rapor üretimi (Streamlit'ten bağımsız, test edilebilir) — Türkçe karakter desteği için repo içine gömülü `fonts/DejaVuSans.ttf` kullanır (önceden sabit bir macOS sistem yoluydu, Linux/Docker/Windows'ta çökerdi)
- `evaluate.py` — Modeli winvoker veri setine (Wikipedia nötr) karşı test eder
- `evaluate_trsav1.py` — Modeli TRSAv1 held-out setine (gerçek ürün yorumu nötr) karşı test eder
- `finetune3.py` — v3/v4_full/v5_full'ü üreten fine-tuning tarifi (TRSAv1 + sentetik nötr, `cikti_dizini` parametreli)
- `finetune_v6.py` — Reddedilen v6 adayının tarifi (hedefli nötr karşıt örnekleri ekler) — bkz. SKILL.md Gotchas
- `model_karsilastir.py` — Bir aday modeli gold test setinde üretimdeki modele karşı ölçüp terfi/red kararı verir
- `sentetik_notr.py` — "sipariş verildi" tarzı prosedürel nötr cümleleri şablonla üretir
- `finetune.py`, `finetune2.py`, `finetune4.py` — Önceki (terk edilmiş/reddedilen) turlar — bkz. SKILL.md Gotchas, neden yetersiz kaldıkları
- `duygu_finetuned_v5_full/` — **Üretimdeki fine-tuned model** (~1.1GB, git'e eklenmemeli)
- `duygu_finetuned_v4_full/`, `duygu_finetuned_v3/` — Sırayla fallback (v5_full bulunamazsa kullanılır)
- `trsav1_held_out.json` — `evaluate_trsav1.py`'nin kullandığı, eğitimden hariç tutulmuş 450 örnek
- `ornek_yorumlar.csv`, `test_yorumlar*.csv` — Test için örnek Türkçe yorumlar
- `requirements.txt` — Gerekli Python paketleri

## Bilinen sınırlama (kasıtlı olarak çözülmedi)

Nötr recall %64.0 (TRSAv1 testinde) — mükemmel değil. "sipariş verildi"
tarzı prosedürel cümleler sentetik veriyle düzeltildi, ama "fatura" gibi
tekil kelimeler hâlâ sorunlu: gerçek veride bağlamdan bağımsız güçlü bir
kutupla ilişkili (ör. "fatura" geçen yorumların %84'ü olumsuz — TRSAv1'in
tamamında, sadece bizim örneklemimizde değil). **Daha fazla eğitim verisi
bunu çözmez** — denemeden önce doğrulandı. Gerçek çözüm (hedefli
karşı-örnek dengeleme) maliyet/fayda açısından şu an değmiyor; bilinen bir
sınırlama olarak bırakıldı. Detaylar: SKILL.md Gotchas.

## Sonraki Adımlar (geliştirme fikirleri)

- Sonuçları bir veritabanına kaydedip zaman içindeki trend grafiği çıkarma
