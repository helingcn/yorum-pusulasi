import { useState } from 'react'
import { analizEt, konuAnaliziGetir, ApiHatasi } from '../lib/api'
import type { AnalizSonucu, KonuSonucu } from '../lib/types'
import { ResultCard } from './ResultCard'
import { FeedbackForm } from './FeedbackForm'
import { WordImportance } from './WordImportance'
import { TopicAnalysis } from './TopicAnalysis'

export function SingleAnalysisTab() {
  const [metin, setMetin] = useState('')
  const [analizEdilenMetin, setAnalizEdilenMetin] = useState('')
  const [sonuc, setSonuc] = useState<AnalizSonucu | null>(null)
  const [konular, setKonular] = useState<KonuSonucu[]>([])
  const [yukleniyor, setYukleniyor] = useState(false)
  const [hata, setHata] = useState<string | null>(null)

  const analizYap = async () => {
    if (!metin.trim()) {
      setHata('Lütfen bir yorum gir.')
      return
    }
    setHata(null)
    setYukleniyor(true)
    try {
      // Konu analizi, sonuç kartındaki "karma yön" rozetini gösterebilmek
      // için sonuçla birlikte, önceden hesaplanıyor.
      const [analizSonucu, konuSonuclari] = await Promise.all([analizEt(metin), konuAnaliziGetir(metin)])
      setAnalizEdilenMetin(metin)
      setSonuc(analizSonucu)
      setKonular(konuSonuclari)
    } catch (e) {
      setHata(e instanceof ApiHatasi ? e.message : 'Analiz sırasında beklenmeyen bir hata oluştu.')
    } finally {
      setYukleniyor(false)
    }
  }

  const yeniAnaliz = () => {
    setMetin('')
    setSonuc(null)
    setKonular([])
    setHata(null)
  }

  const karmaYonVar = new Set(konular.map((k) => k.etiket)).size > 1

  return (
    <div className="grid items-stretch gap-7 md:grid-cols-2">
      <div className="flex flex-col">
        <div className="mb-1.5 font-[var(--font-display)] text-[19px] font-semibold text-[var(--text-primary)]">Yorumu incele</div>
        <p className="mb-4 text-[13.5px] text-[var(--text-secondary)]">Müşterinin yazdığı geri bildirimi aşağıya yapıştır.</p>
        <textarea
          value={metin}
          onChange={(e) => setMetin(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) analizYap()
          }}
          placeholder="Örn: Kargo çok hızlıydı ama ürünün kalitesi beklediğim gibi değildi."
          rows={6}
          style={{ backgroundImage: 'repeating-linear-gradient(transparent, transparent 27px, var(--gridline) 28px)', backgroundPositionY: '4px' }}
          className="mb-4 w-full flex-1 resize-none rounded border border-[var(--border)] bg-[var(--page-plane)] p-4 font-[var(--font-display)] text-[15px] text-[var(--text-primary)] italic focus:border-[var(--accent)] focus:outline-none"
        />
        {hata && <p className="mb-3 text-sm text-[var(--critical-text)]">{hata}</p>}
        <div className="flex gap-2.5">
          <button
            type="button"
            onClick={analizYap}
            disabled={yukleniyor}
            className="flex h-[46px] flex-[1.6] items-center justify-center gap-2 rounded bg-[var(--accent)] text-[14px] font-semibold text-[var(--accent-ink)] transition hover:brightness-110 disabled:opacity-60"
          >
            {yukleniyor ? 'Analiz ediliyor…' : 'Analiz Et'}
            {!yukleniyor && (
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
                <path d="M5 12h14M13 6l6 6-6 6" />
              </svg>
            )}
          </button>
          <button
            type="button"
            onClick={yeniAnaliz}
            className="h-[46px] flex-1 rounded border border-[var(--accent)] text-[14px] font-semibold text-[var(--accent)]"
          >
            Yeni Kayıt
          </button>
        </div>
      </div>

      {sonuc ? (
        <div className="sonuc-animasyonu flex flex-col gap-5">
          <ResultCard metin={analizEdilenMetin} sonuc={sonuc} karmaYonVar={karmaYonVar} />
          <TopicAnalysis konular={konular} varsayilanAcik={karmaYonVar} />
          <WordImportance metin={analizEdilenMetin} etiket={sonuc.etiket} />
          <FeedbackForm metin={analizEdilenMetin} tahmin={sonuc.etiket} guven={sonuc.guven} />
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center rounded border border-dashed border-[var(--border)] p-8 text-center">
          <svg viewBox="0 0 52 52" className="mb-4 h-11 w-11 opacity-70" aria-hidden="true">
            <circle cx="26" cy="26" r="24" fill="none" stroke="var(--accent)" strokeWidth="1.4" />
            <circle cx="26" cy="26" r="1.8" fill="var(--brass)" />
            <path d="M26 4 L29.5 23 L26 26 L22.5 23 Z" fill="var(--accent)" />
          </svg>
          <div className="mb-1 font-[var(--font-display)] text-[17px] font-semibold text-[var(--text-primary)]">Kayıt burada oluşacak</div>
          <p className="max-w-[280px] text-[13px] text-[var(--text-muted)]">
            Yorumunu giriş alanına yapıştır, Analiz Et'e bas, duygu ve konu sonuçlarını incele.
          </p>
        </div>
      )}
    </div>
  )
}
