import { useEffect, useState } from 'react'
import type { AnalizSonucu, Duygu } from '../lib/types'
import { DUYGU_BILGISI, GUVEN_NOT_STILI, guvenDurumu } from '../lib/durum'

interface ResultCardProps {
  metin: string
  sonuc: AnalizSonucu
  karmaYonVar: boolean
}

const SIRALI_ETIKETLER: Duygu[] = ['olumlu', 'nötr', 'olumsuz']
const CEVRE = 2 * Math.PI * 17

export function ResultCard({ metin, sonuc, karmaYonVar }: ResultCardProps) {
  const [kopyalandi, setKopyalandi] = useState(false)
  const [halkaDoldu, setHalkaDoldu] = useState(false)
  const bilgi = DUYGU_BILGISI[sonuc.etiket]
  const yuzde = Math.round(sonuc.guven * 1000) / 10
  const guven = guvenDurumu(sonuc.guven)

  // The confidence ring fills from 0 to the real value (a micro-animation
  // specified during the design pass) — transitions to the target right after mount.
  useEffect(() => {
    const zamanlayici = requestAnimationFrame(() => setHalkaDoldu(true))
    return () => cancelAnimationFrame(zamanlayici)
  }, [metin])

  const kopyala = async () => {
    const metinKopyala = `Duygu: ${bilgi.baslik}\nModel güveni: %${yuzde}\nYorum: ${metin}`
    try {
      await navigator.clipboard.writeText(metinKopyala)
      setKopyalandi(true)
      setTimeout(() => setKopyalandi(false), 2000)
    } catch {
      // Silently ignore if clipboard access isn't permitted.
    }
  }

  return (
    <div
      className="relative rounded-md p-5.5"
      style={{
        border: `1px solid color-mix(in oklch, ${bilgi.renk} 35%, var(--border))`,
        background: `color-mix(in oklch, ${bilgi.renk} 6%, var(--surface-1))`,
      }}
    >
      <div className="absolute top-[-1px] left-5.5 h-[3px] w-[30px]" style={{ background: bilgi.renk }} />

      <div className="mb-4.5 flex items-center gap-4.5">
        <svg width="58" height="58" viewBox="0 0 40 40" className="shrink-0">
          <circle cx="20" cy="20" r="17" fill="none" stroke="var(--gridline)" strokeWidth="3" />
          <circle
            cx="20"
            cy="20"
            r="17"
            fill="none"
            stroke={bilgi.renk}
            strokeWidth="3"
            strokeLinecap="round"
            transform="rotate(-90 20 20)"
            strokeDasharray={CEVRE}
            strokeDashoffset={halkaDoldu ? CEVRE * (1 - sonuc.guven) : CEVRE}
            className="transition-[stroke-dashoffset] duration-500 ease-out motion-reduce:transition-none"
          />
          <text x="20" y="24" textAnchor="middle" fontSize="10" fontFamily="Work Sans" fontWeight="700" fill="var(--text-primary)">
            {yuzde}%
          </text>
        </svg>
        <div>
          <div className="mb-1 text-[10.5px] font-bold tracking-[0.1em] uppercase" style={{ color: bilgi.renk }}>
            Baskın Yön
          </div>
          <div className="font-[var(--font-display)] text-[25px] leading-none font-semibold" style={{ color: bilgi.renk }}>
            {bilgi.baslik}
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-2 border-t pt-4" style={{ borderColor: `color-mix(in oklch, ${bilgi.renk} 25%, transparent)` }}>
        {SIRALI_ETIKETLER.map((etiket) => {
          const b = DUYGU_BILGISI[etiket]
          const pct = Math.round((sonuc.olasiliklar[etiket] ?? 0) * 1000) / 10
          return (
            <div key={etiket} className="flex items-center gap-2.5 text-xs text-[var(--text-secondary)]">
              <span className="w-[52px]">{b.baslik}</span>
              <div className="h-[5px] flex-1 overflow-hidden rounded-full bg-[var(--gridline)]">
                <div className="h-full min-w-[2px] rounded-full transition-[width] duration-500" style={{ width: `${pct}%`, background: b.barRengi }} />
              </div>
              <span className="w-9 text-right tabular-nums" style={{ fontWeight: etiket === sonuc.etiket ? 700 : 400, color: etiket === sonuc.etiket ? 'var(--text-primary)' : undefined }}>
                %{pct}
              </span>
            </div>
          )
        })}
      </div>

      {karmaYonVar && (
        <div className="mt-4 flex items-start gap-2 rounded p-3" style={{ background: 'color-mix(in oklch, var(--brass) 12%, var(--surface-1))', border: '1px solid color-mix(in oklch, var(--brass) 40%, transparent)' }}>
          <svg width="14" height="14" viewBox="0 0 52 52" className="mt-0.5 shrink-0">
            <circle cx="26" cy="26" r="23" fill="none" stroke="var(--brass-text)" strokeWidth="3" />
            <path d="M26 6 L32 26 L26 46 L20 26 Z" fill="var(--brass-text)" />
          </svg>
          <div>
            <div className="mb-0.5 font-[var(--font-display)] text-[13px] font-semibold text-[var(--brass-text)] italic">Karma yön tespit edildi</div>
            <p className="text-xs leading-relaxed text-[var(--text-secondary)]">
              Bu yorumda konuya göre farklı tonlar var — aşağıdaki konu bazlı kayıtta ayrıştırılmış hâlini bulabilirsin.
            </p>
          </div>
        </div>
      )}

      <div className={`mt-4 rounded border p-3 text-[13px] leading-relaxed ${GUVEN_NOT_STILI[guven.sinif]}`}>
        <strong className="mb-0.5 block">
          {guven.baslik} · %{yuzde}
        </strong>
        {guven.aciklama}
      </div>

      <button
        type="button"
        onClick={kopyala}
        className="mt-4 h-9 rounded border border-[var(--accent)] px-4 text-xs font-semibold text-[var(--accent)]"
      >
        {kopyalandi ? 'Kopyalandı ✓' : 'Sonucu kopyala'}
      </button>
    </div>
  )
}
