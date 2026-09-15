import { useState } from 'react'
import { geriBildirimKaydet } from '../lib/api'
import type { Duygu } from '../lib/types'

interface FeedbackFormProps {
  metin: string
  tahmin: Duygu
  guven: number
}

const TUM_ETIKETLER: Duygu[] = ['olumlu', 'nötr', 'olumsuz']

export function FeedbackForm({ metin, tahmin, guven }: FeedbackFormProps) {
  const [karar, setKarar] = useState<'doğru' | 'yanlış'>('doğru')
  const [dogruEtiket, setDogruEtiket] = useState<Duygu>(TUM_ETIKETLER.find((e) => e !== tahmin) ?? 'nötr')
  const [durum, setDurum] = useState<'boşta' | 'kaydediliyor' | 'kaydedildi' | 'hata'>('boşta')

  const kaydet = async () => {
    setDurum('kaydediliyor')
    try {
      await geriBildirimKaydet(metin, tahmin, guven, karar, karar === 'yanlış' ? dogruEtiket : undefined)
      setDurum('kaydedildi')
    } catch {
      setDurum('hata')
    }
  }

  const duzeltmeSecenekleri = TUM_ETIKETLER.filter((e) => e !== tahmin)

  return (
    <div className="rounded border border-[var(--border)] p-5">
      <div className="mb-1 font-[var(--font-display)] text-[15px] font-semibold text-[var(--text-primary)]">Bu kayıt doğru mu?</div>
      <p className="mb-4 text-[12.5px] leading-relaxed text-[var(--text-muted)]">
        Yanlış tahminler, sonraki model eğitiminde kullanılabilecek ayrı bir düzeltme kaydına eklenir.
      </p>

      <div className="mb-4 flex gap-5 text-sm text-[var(--text-secondary)]">
        {(['doğru', 'yanlış'] as const).map((secenek) => (
          <label key={secenek} className="flex items-center gap-1.5 capitalize">
            <input type="radio" name="karar" checked={karar === secenek} onChange={() => setKarar(secenek)} className="accent-[var(--accent)]" />
            {secenek === 'doğru' ? 'Doğru' : 'Yanlış'}
          </label>
        ))}
      </div>

      {karar === 'yanlış' && (
        <div className="mb-4">
          <label className="mb-1.5 block text-[12.5px] font-semibold text-[var(--text-primary)]">Yanlışsa doğru sonuç</label>
          <select
            value={dogruEtiket}
            onChange={(e) => setDogruEtiket(e.target.value as Duygu)}
            className="h-10 w-full rounded border border-[var(--border)] bg-[var(--page-plane)] px-3 text-sm text-[var(--text-primary)]"
          >
            {duzeltmeSecenekleri.map((e) => (
              <option key={e} value={e}>
                {e}
              </option>
            ))}
          </select>
        </div>
      )}

      <button
        type="button"
        onClick={kaydet}
        disabled={durum === 'kaydediliyor'}
        className="h-11 w-full rounded bg-[var(--accent)] text-sm font-semibold text-[var(--accent-ink)] transition hover:brightness-110 disabled:opacity-60"
      >
        {durum === 'kaydediliyor' ? 'Kaydediliyor…' : 'Kaydı Güncelle'}
      </button>
      {durum === 'kaydedildi' && <p className="mt-2 text-[12.5px] text-[var(--good)]">Kaydedildi. Teşekkürler!</p>}
      {durum === 'hata' && <p className="mt-2 text-[12.5px] text-[var(--critical-text)]">Kaydedilemedi, lütfen tekrar dene.</p>}
    </div>
  )
}
