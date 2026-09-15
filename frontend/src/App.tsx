import { useState } from 'react'
import { Header } from './components/Header'
import { Footer } from './components/Footer'
import { SingleAnalysisTab } from './components/SingleAnalysisTab'
import { BatchAnalysisTab } from './components/BatchAnalysisTab'
import { useDarkMode } from './lib/useDarkMode'

type Sekme = 'tekil' | 'dosya'

function App() {
  const [karanlik, temaDegistir] = useDarkMode()
  const [sekme, setSekme] = useState<Sekme>('tekil')

  return (
    <div className="mx-auto min-h-screen max-w-[1312px] px-6 sm:px-8">
      <Header karanlik={karanlik} onTemaDegistir={temaDegistir} />

      <div className="mt-10">
        <h1 className="font-[var(--font-display)] text-[32px] font-medium tracking-tight text-[var(--text-primary)] sm:text-[44px]">
          Yorumların ne söylüyor?
        </h1>
        <p className="mt-3 mb-8 max-w-xl text-[15px] leading-relaxed text-[var(--text-secondary)]">
          Tek bir geri bildirimi keşfet ya da dosyanı yükleyip müşteri duygusunun genel görünümünü çıkar.
        </p>

        <div className="relative z-10 -mb-px flex gap-0.5">
          {(
            [
              ['tekil', 'Tekil analiz'],
              ['dosya', 'Dosya analizi'],
            ] as const
          ).map(([deger, etiket]) => (
            <button
              key={deger}
              type="button"
              onClick={() => setSekme(deger)}
              className={`rounded-t-md border px-6 py-3 text-[13.5px] font-semibold transition-colors ${
                sekme === deger
                  ? 'border-[var(--border)] border-b-[var(--surface-1)] bg-[var(--surface-1)] text-[var(--accent)]'
                  : 'border-transparent text-[var(--text-muted)]'
              }`}
            >
              {etiket}
            </button>
          ))}
        </div>

        <div className="rounded-b-xl rounded-tr-xl border border-[var(--border)] bg-[var(--surface-1)] p-8">
          {sekme === 'tekil' ? <SingleAnalysisTab /> : <BatchAnalysisTab />}
        </div>
      </div>

      <Footer />
    </div>
  )
}

export default App
