import type { KonuSonucu } from '../lib/types'
import { DUYGU_BILGISI } from '../lib/durum'

interface TopicAnalysisProps {
  konular: KonuSonucu[]
  varsayilanAcik: boolean
}

export function TopicAnalysis({ konular, varsayilanAcik }: TopicAnalysisProps) {
  if (konular.length === 0) return null

  return (
    <details className="group" open={varsayilanAcik}>
      <summary className="mb-2.5 flex cursor-pointer list-none items-center gap-1.5 text-[10.5px] font-bold tracking-[0.1em] text-[var(--text-muted)] uppercase">
        <span className="transition-transform group-open:rotate-90">›</span>
        Konu Bazlı Kayıt
      </summary>
      <div className="flex flex-col gap-2.5 pl-4">
        {konular.map((k, i) => {
          const bilgi = DUYGU_BILGISI[k.etiket]
          return (
            <div key={i} className="flex flex-wrap items-center gap-2.5 text-[12.5px]">
              <span className="w-[60px] font-semibold text-[var(--text-primary)] capitalize">{k.konu}</span>
              <span className="flex-1 text-[var(--text-secondary)] italic">&ldquo;{k.parca}&rdquo;</span>
              <span
                className="rounded-full px-2.5 py-1 text-[10.5px] font-bold whitespace-nowrap"
                style={{ background: `color-mix(in oklch, ${bilgi.renk} 16%, transparent)`, color: bilgi.renk }}
              >
                {bilgi.baslik}
              </span>
            </div>
          )
        })}
      </div>
    </details>
  )
}
