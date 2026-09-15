# Yorum Pusulası — Frontend (React)

Streamlit sürümünün ([app.py](../app.py)) yerini alması için yazılan, `api.py`'ye
konuşan bağımsız bir React uygulaması. Streamlit sürümü silinmedi — ikisi de
aynı `api.py`/`sentiment.py`'yi kullanıyor, yan yana çalışabilirler.

**Neden:** Streamlit'in kendi DOM yapısına (`data-testid`, `st-emotion-cache`)
bağımlı CSS/JS hackleri sürdürülemez hâle gelmişti — her görsel düzeltme
başka bir yeri kırma riski taşıyordu (bkz. proje geçmişi). Burada CSS/layout
tamamen component'lerin kendi sorumluluğunda, gizli bir DOM'a bağımlılık yok.

## Kurulum

```bash
npm install
cp .env.example .env.local   # .env.local'ı kendi API adresine göre düzenle
npm run dev
```

`http://localhost:5173` adresinde açılır. `api.py`'nin ayrıca çalışıyor
olması gerekir (bkz. [ana README](../README.md#kurulum)):

```bash
# proje kök dizininde, ayrı bir terminalde
uvicorn api:app --port 8000
```

`.env.local`'da `VITE_API_BASE_URL` bu adrese işaret etmeli (varsayılan:
`http://localhost:8000`). `api.py`'de `IZINLI_ORIJINLER` ayarlanmadıysa CORS
otomatik olarak `http://localhost:5173`'e izin verir — ekstra yapılandırma
gerekmez.

## Mimari

- `src/lib/api.ts` — tüm backend çağrıları için tek, tipli istemci
- `src/lib/useDarkMode.ts` — karanlık mod: `<html class="dark">` + Tailwind
  `dark:` varyantı + localStorage. Streamlit sürümünde yaşanan "OS @media
  sorgusu ile manuel toggle çakışması" ve "toggle'ın görsel katmanı tıklamayı
  yutuyor" gibi sorunlar burada mimari olarak mümkün değil — tek kaynak, gerçek
  bir `<button>`.
- `src/components/SingleAnalysisTab.tsx` — tekil analiz: form + sonuç kartı +
  geri bildirim + kelime önemleri + konu bazlı analiz. Konu analizi sonuçla
  BİRLİKTE (paralel) çekiliyor ki "karma duygu" rozeti sonuç kartında hemen
  görünsün (Streamlit sürümünde bu özellik sayfanın en altında gömülü
  kalmıştı).
- `src/components/BatchAnalysisTab.tsx` — dosya yükleme (ayrıştırma backend'de,
  `/toplu-analiz-dosya`), özet istatistikler, arama/filtreli tablo, CSV
  (istemci tarafında) ve PDF (backend'den, `/pdf-raporu`) indirme.

## Bilinen sınırlama

Backend'deki model çıkarımı **tek seferde bir istek** ile sınırlı
(`sentiment.py`'deki `_CIKARIM_SEMAFORU`, kasıtlı olarak mutex'e
döndürüldü) — bu ortamda HuggingFace pipeline'ın gerçek eşzamanlı çağrılar
altında çökebildiği canlı olarak doğrulandı (bu frontend'in kendisi
`Promise.all` ile paralel istek attığında bulundu). Yani "Tekil analiz"
sekmesindeki `/analiz` ve `/konu-analizi` çağrıları paralel gönderiliyor
ama backend'de sıraya giriyor — pratikte fark edilmez (~birkaç yüz ms),
ama sunucu tarafında gerçek paralellik yok.
