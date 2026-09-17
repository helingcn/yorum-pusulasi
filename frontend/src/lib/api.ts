import type { AnalizSonucu, Duygu, KelimeOnemi, KonuSonucu, SaglikDurumu, TopluAnalizSonucu } from './types'

// The address api.py runs on — overridable in the Vite dev server via
// .env(.local) (see .env.example). Falls back to port 8000 by local dev
// convention if not set (matches the `uvicorn api:app --port 8000` command
// in the README).
const API_TABANI = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

// If the API_ANAHTARI environment variable is set in api.py, the same
// value must be entered here too. NOTE: this is client-side code shipped to
// the browser — the key placed here is NOT a real secret, don't use this on
// a publicly accessible site. Only suitable for local/internal use.
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
      // A non-JSON error body — keep the default message.
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
