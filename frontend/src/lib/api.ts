import type { AnalizSonucu, Duygu, KelimeOnemi, KonuSonucu, SaglikDurumu, TopluAnalizSonucu } from './types'

// api.py'nin çalıştığı adres — Vite dev sunucusunda .env(.local) ile
// override edilebilir (bkz. .env.example). Ayarlanmazsa yerel geliştirme
// varsayımıyla 8000 portuna düşer (README'deki `uvicorn api:app --port 8000`
// komutuyla eşleşiyor).
const API_TABANI = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

// api.py'de API_ANAHTARI ortam değişkeni ayarlandıysa burada da aynı
// değerin girilmesi gerekir. NOT: bu, tarayıcıya gönderilen bir istemci
// kodudur — buraya konan anahtar gerçek bir sır DEĞİLDİR, herkese açık bir
// sitede bunu kullanmayın. Yalnızca yerel/iç kullanım için uygundur.
const API_ANAHTARI = import.meta.env.VITE_API_ANAHTARI as string | undefined

class ApiHatasi extends Error {
  durumKodu: number

  constructor(message: string, durumKodu: number) {
    super(message)
    this.name = 'ApiHatasi'
    this.durumKodu = durumKodu
  }
}

async function istekAt<T>(yol: string, secenekler: RequestInit = {}): Promise<T> {
  const basliklar: Record<string, string> = { ...(secenekler.headers as Record<string, string>) }
  if (API_ANAHTARI) basliklar['X-API-Key'] = API_ANAHTARI
  if (secenekler.body && !(secenekler.body instanceof FormData)) {
    basliklar['Content-Type'] = 'application/json'
  }

  const yanit = await fetch(`${API_TABANI}${yol}`, { ...secenekler, headers: basliklar })

  if (!yanit.ok) {
    let mesaj = `İstek başarısız oldu (HTTP ${yanit.status}).`
    try {
      const govde = await yanit.json()
      if (typeof govde.detail === 'string') mesaj = govde.detail
      else if (Array.isArray(govde.detail) && govde.detail[0]?.msg) mesaj = govde.detail[0].msg
    } catch {
      // JSON olmayan bir hata gövdesi — varsayılan mesaj kalsın.
    }
    throw new ApiHatasi(mesaj, yanit.status)
  }
  return yanit.json() as Promise<T>
}

export async function saglikKontrol(): Promise<SaglikDurumu> {
  return istekAt<SaglikDurumu>('/saglik')
}

export async function analizEt(metin: string): Promise<AnalizSonucu> {
  return istekAt<AnalizSonucu>('/analiz', { method: 'POST', body: JSON.stringify({ metin }) })
}

export async function kelimeOnemleriGetir(metin: string): Promise<KelimeOnemi[]> {
  const sonuc = await istekAt<{ kelimeler: KelimeOnemi[] }>('/kelime-onemleri', {
    method: 'POST',
    body: JSON.stringify({ metin }),
  })
  return sonuc.kelimeler
}

export async function konuAnaliziGetir(metin: string): Promise<KonuSonucu[]> {
  const sonuc = await istekAt<{ konular: KonuSonucu[] }>('/konu-analizi', {
    method: 'POST',
    body: JSON.stringify({ metin }),
  })
  return sonuc.konular
}

export async function geriBildirimKaydet(
  metin: string,
  tahmin: Duygu,
  guven: number,
  karar: 'doğru' | 'yanlış',
  dogruEtiket?: Duygu,
): Promise<void> {
  await istekAt('/geri-bildirim', {
    method: 'POST',
    body: JSON.stringify({ metin, tahmin, guven, karar, dogru_etiket: dogruEtiket }),
  })
}

export async function topluAnalizDosyadan(dosya: File): Promise<TopluAnalizSonucu> {
  const form = new FormData()
  form.append('dosya', dosya)
  return istekAt<TopluAnalizSonucu>('/toplu-analiz-dosya', { method: 'POST', body: form })
}

export async function pdfRaporuIndir(
  toplam: number,
  olumlu: number,
  notr: number,
  olumsuz: number,
  ortGuven: number,
  sonuclar: { metin: string; etiket: Duygu; guven: number }[],
): Promise<Blob> {
  const yanit = await fetch(`${API_TABANI}/pdf-raporu`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(API_ANAHTARI ? { 'X-API-Key': API_ANAHTARI } : {}),
    },
    body: JSON.stringify({ toplam, olumlu, notr, olumsuz, ort_guven: ortGuven, sonuclar }),
  })
  if (!yanit.ok) throw new ApiHatasi('PDF raporu oluşturulamadı.', yanit.status)
  return yanit.blob()
}

export { ApiHatasi }
