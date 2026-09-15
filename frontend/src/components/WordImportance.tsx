import { useEffect, useState } from 'react'
import { kelimeOnemleriGetir } from '../lib/api'
import type { KelimeOnemi, Duygu } from '../lib/types'
import { DUYGU_BILGISI } from '../lib/durum'

interface WordImportanceProps {
  metin: string
  etiket: Duygu
}

export function WordImportance({ metin, etiket }: WordImportanceProps) {
  const [acik, setAcik] = useState(false)
  const [onemler, setOnemler] = useState<KelimeOnemi[] | null>(null)
  const [yukleniyor, setYukleniyor] = useState(false)

  useEffect(() => {
    if (acik && onemler === null && !yukleniyor) {
      setYukleniyor(true)
      kelimeOnemleriGetir(metin)
        .then(setOnemler)
        .finally(() => setYukleniyor(false))
    }
  }, [acik, metin, onemler, yukleniyor])

  const enYuksek = Math.max(0.0001, ...(onemler ?? []).map((o) => Math.max(o.onem, 0)))
  const bilgi = DUYGU_BILGISI[etiket]

  return (
    <details
      className="group"
      open={acik}
      onToggle={(e) => setAcik((e.target as HTMLDetailsElement).open)}
    >
      <summary className="flex cursor-pointer list-none items-center gap-1.5 text-[10.5px] font-bold tracking-[0.1em] text-[var(--text-muted)] uppercase">
        <span className="transition-transform group-open:rotate-90">›</span>
        Hangi kelimeler etkiledi?
      </summary>
      <div className="mt-2.5 pl-4">
        {yukleniyor && <p className="text-sm text-[var(--text-muted)]">Hesaplanıyor…</p>}
        {onemler && (
          <>
            <p className="font-[var(--font-display)] text-[15px] leading-[2.1] text-[var(--text-primary)] italic">
              {onemler.map((o, i) => {
                const yogunluk = Math.max(o.onem, 0) / enYuksek
                if (yogunluk <= 0.25) return <span key={i}> {o.kelime}</span>
                const opaklik = 12 + 50 * yogunluk
                return (
                  <span key={i} className="rounded px-1 not-italic" style={{ background: `color-mix(in oklch, ${bilgi.renk} ${opaklik}%, transparent)` }}>
                    {' '}
                    {o.kelime}
                  </span>
                )
              })}
            </p>
            <p className="mt-2 text-[12px] text-[var(--text-muted)]">
              Koyu renk vurgulu kelimeler, modelin &ldquo;{bilgi.baslik.toLowerCase()}&rdquo; kararını daha çok destekledi.
            </p>
          </>
        )}
      </div>
    </details>
  )
}
