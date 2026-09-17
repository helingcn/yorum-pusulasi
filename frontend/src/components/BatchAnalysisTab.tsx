import { useMemo, useState } from 'react'
import { topluAnalizDosyadan, pdfRaporuIndir, ApiHatasi } from '../lib/api'
import type { Duygu, TopluSonucSatiri } from '../lib/types'
import { DUYGU_BILGISI } from '../lib/durum'

export function BatchAnalysisTab() {
  const [dosya, setDosya] = useState<File | null>(null)
  const [sonuclar, setSonuclar] = useState<TopluSonucSatiri[] | null>(null)
  const [yukleniyor, setYukleniyor] = useState(false)
  const [hata, setHata] = useState<string | null>(null)
  const [arama, setArama] = useState('')
  const [duyguFiltre, setDuyguFiltre] = useState<Duygu | ''>('')

  const analizYap = async () => {
    if (!dosya) return
    setHata(null)
    setYukleniyor(true)
    try {
      const sonuc = await topluAnalizDosyadan(dosya)
      setSonuclar(sonuc.sonuclar)
    } catch (e) {
      setHata(e instanceof ApiHatasi ? e.message : 'Dosya işlenirken beklenmeyen bir hata oluştu.')
    } finally {
      setYukleniyor(false)
    }
  }

  const yeniAnaliz = () => {
    setDosya(null)
    setSonuclar(null)
    setHata(null)
    setArama('')
    setDuyguFiltre('')
  }

  const ozet = useMemo(() => {
    if (!sonuclar) return null
    const toplam = sonuclar.length
    const olumlu = sonuclar.filter((s) => s.etiket === 'olumlu').length
    const notr = sonuclar.filter((s) => s.etiket === 'nötr').length
    const olumsuz = sonuclar.filter((s) => s.etiket === 'olumsuz').length
    const ortGuven = toplam ? Math.round((sonuclar.reduce((t, s) => t + s.guven, 0) / toplam) * 1000) / 10 : 0
    return { toplam, olumlu, notr, olumsuz, ortGuven }
  }, [sonuclar])

  const filtreliSonuclar = useMemo(() => {
    if (!sonuclar) return []
    const q = arama.toLocaleLowerCase('tr')
    return sonuclar.filter((s) => {
      if (duyguFiltre && s.etiket !== duyguFiltre) return false
      return !q || s.metin.toLocaleLowerCase('tr').includes(q)
    })
  }, [sonuclar, arama, duyguFiltre])

  const csvIndir = () => {
    if (!sonuclar) return
    const satirlar = [
      ['Yorum', 'Sonuç', 'Güven'],
      ...sonuclar.map((s) => [s.metin, s.etiket, `%${Math.round(s.guven * 1000) / 10}`]),
    ]
    const csv = satirlar.map((satir) => satir.map((h) => `"${h.replace(/"/g, '""')}"`).join(',')).join('\n')
    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' })
    indirBlob(blob, 'duygu_analizi_sonuclari.csv')
  }

  const pdfIndir = async () => {
    if (!sonuclar || !ozet) return
    try {
      const blob = await pdfRaporuIndir(ozet.toplam, ozet.olumlu, ozet.notr, ozet.olumsuz, ozet.ortGuven, sonuclar)
      indirBlob(blob, 'duygu_analizi_raporu.pdf')
    } catch {
      setHata('PDF raporu oluşturulamadı.')
    }
  }

  return (
    <div className="flex flex-col gap-7">
      {/* Upload */}
      <div className="flex items-center gap-5 rounded border-[1.5px] border-dashed border-[var(--brass)] p-6" style={{ background: 'color-mix(in oklch, var(--brass) 8%, var(--surface-1))' }}>
        <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="var(--brass-text)" strokeWidth="1.6" className="shrink-0">
          <path d="M12 3v12M7 8l5-5 5 5M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2" />
        </svg>
        <div className="flex-1">
          {dosya ? (
            <>
              <div className="font-[var(--font-display)] text-[16px] font-semibold text-[var(--text-primary)]">{dosya.name}</div>
              <div className="mt-0.5 text-[12px] text-[var(--text-muted)]">
                CSV, Excel (.xlsx) veya JSON kabul edilir, <strong>yorum</strong> adlı sütun aranır.
              </div>
            </>
          ) : (
            <>
              <div className="font-[var(--font-display)] text-[16px] font-semibold text-[var(--text-primary)]">Bir yorum manifestosu yükle</div>
              <div className="mt-0.5 text-[12px] text-[var(--text-muted)]">
                CSV, Excel (.xlsx) veya JSON dosyanı analiz edebilirsin. Dosyada <strong>yorum</strong> adlı bir sütun bulunmalı.
              </div>
            </>
          )}
        </div>
        <label className="h-[42px] cursor-pointer rounded bg-[var(--accent)] px-5 text-[13.5px] font-semibold text-[var(--accent-ink)] flex items-center">
          <input type="file" accept=".csv,.xlsx,.json" className="hidden" onChange={(e) => setDosya(e.target.files?.[0] ?? null)} />
          Dosya Seç
        </label>
      </div>

      {hata && <p className="text-sm text-[var(--critical-text)]">{hata}</p>}
      {dosya && !sonuclar && (
        <div className="-mt-3 flex gap-2.5">
          <button
            type="button"
            onClick={analizYap}
            disabled={yukleniyor}
            className="h-11 flex-[1.6] rounded bg-[var(--accent)] text-sm font-semibold text-[var(--accent-ink)] disabled:opacity-60"
          >
            {yukleniyor ? 'Analiz ediliyor…' : 'Kaydı Aç — Toplu Analiz'}
          </button>
          <button type="button" onClick={yeniAnaliz} className="h-11 flex-1 rounded border border-[var(--accent)] text-sm font-semibold text-[var(--accent)]">
            Vazgeç
          </button>
        </div>
      )}

      {ozet && (
        <>
          {/* Summary */}
          <div className="grid grid-cols-2 gap-px overflow-hidden rounded border border-[var(--border)] bg-[var(--border)] sm:grid-cols-5">
            {[
              { etiket: 'Toplam Kayıt', deger: ozet.toplam, renk: undefined },
              { etiket: 'Olumlu', deger: ozet.olumlu, renk: 'var(--good)' },
              { etiket: 'Nötr', deger: ozet.notr, renk: 'var(--brass-text)' },
              { etiket: 'Olumsuz', deger: ozet.olumsuz, renk: 'var(--critical-text)' },
              { etiket: 'Ort. Güven', deger: `%${ozet.ortGuven}`, renk: undefined },
            ].map((kart) => (
              <div key={kart.etiket} className="bg-[var(--surface-1)] p-4.5">
                <div className="mb-2 text-[10px] font-bold tracking-[0.1em] text-[var(--text-muted)] uppercase">{kart.etiket}</div>
                <div className="font-[var(--font-display)] text-[26px] font-semibold" style={{ color: kart.renk ?? 'var(--text-primary)' }}>
                  {kart.deger}
                </div>
              </div>
            ))}
          </div>

          {/* Distribution */}
          <div className="flex flex-col gap-2.5">
            {(['olumlu', 'nötr', 'olumsuz'] as Duygu[]).map((etiket) => {
              const sayi = etiket === 'olumlu' ? ozet.olumlu : etiket === 'nötr' ? ozet.notr : ozet.olumsuz
              const maks = Math.max(ozet.olumlu, ozet.notr, ozet.olumsuz, 1)
              const bilgi = DUYGU_BILGISI[etiket]
              return (
                <div key={etiket} className="flex items-center gap-3.5 text-[12.5px] text-[var(--text-secondary)]">
                  <span className="w-14">{bilgi.baslik}</span>
                  <div className="h-5.5 flex-1 overflow-hidden rounded bg-[var(--gridline)]">
                    <div className="h-full rounded transition-[width] duration-500" style={{ width: `${(sayi / maks) * 100}%`, background: bilgi.barRengi }} />
                  </div>
                  <span className="w-7 text-right font-semibold text-[var(--text-primary)]">{sayi}</span>
                </div>
              )
            })}
          </div>

          {/* Table */}
          <div>
            <div className="mb-3.5 flex items-center justify-between">
              <div className="font-[var(--font-display)] text-[18px] font-semibold text-[var(--text-primary)]">Manifest — Detaylı Kayıtlar</div>
              <div className="flex gap-2.5">
                <input
                  type="search"
                  value={arama}
                  onChange={(e) => setArama(e.target.value)}
                  placeholder="Yorumlarda ara…"
                  className="h-9 rounded border border-[var(--border)] bg-[var(--surface-1)] px-3 text-[12.5px] text-[var(--text-primary)]"
                />
                <select
                  value={duyguFiltre}
                  onChange={(e) => setDuyguFiltre(e.target.value as Duygu | '')}
                  className="h-9 w-[135px] rounded border border-[var(--border)] bg-[var(--surface-1)] px-2 text-[12.5px] text-[var(--text-primary)]"
                >
                  <option value="">Tüm yönler</option>
                  <option value="olumlu">Olumlu</option>
                  <option value="nötr">Nötr</option>
                  <option value="olumsuz">Olumsuz</option>
                </select>
              </div>
            </div>
            <div className="max-h-[700px] overflow-auto rounded border border-[var(--border)]">
              <table className="w-full text-[13.5px]">
                <thead className="sticky top-0 bg-[var(--surface-2)]">
                  <tr>
                    <th className="px-4.5 py-3 text-left text-[10.5px] font-bold tracking-[0.08em] text-[var(--text-muted)] uppercase">Yorum</th>
                    <th className="w-[130px] px-4.5 py-3 text-left text-[10.5px] font-bold tracking-[0.08em] text-[var(--text-muted)] uppercase">Yön</th>
                    <th className="w-[95px] px-4.5 py-3 text-right text-[10.5px] font-bold tracking-[0.08em] text-[var(--text-muted)] uppercase">Güven</th>
                  </tr>
                </thead>
                <tbody className="font-[var(--font-display)] italic">
                  {filtreliSonuclar.map((s, i) => {
                    const bilgi = DUYGU_BILGISI[s.etiket]
                    return (
                      <tr key={i} className="border-t border-[var(--border)]">
                        <td className="px-4.5 py-3 text-[var(--text-primary)]">&ldquo;{s.metin}&rdquo;</td>
                        <td className="px-4.5 py-3">
                          <span
                            className="inline-flex items-center rounded-full px-2.5 py-1 text-[10.5px] font-bold not-italic"
                            style={{ background: `color-mix(in oklch, ${bilgi.renk} 15%, transparent)`, color: bilgi.renk }}
                          >
                            {bilgi.baslik}
                          </span>
                        </td>
                        <td className="px-4.5 py-3 text-right font-[var(--font-sans)] font-semibold not-italic tabular-nums text-[var(--text-secondary)]">
                          %{Math.round(s.guven * 1000) / 10}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            <div className="mt-4.5 flex gap-2.5">
              <button type="button" onClick={csvIndir} className="h-10 rounded border border-[var(--accent)] px-4 text-[13px] font-semibold text-[var(--accent)]">
                Manifesti indir (CSV)
              </button>
              <button type="button" onClick={pdfIndir} className="h-10 rounded border border-[var(--accent)] px-4 text-[13px] font-semibold text-[var(--accent)]">
                Rapor indir (PDF)
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function indirBlob(blob: Blob, dosyaAdi: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = dosyaAdi
  a.click()
  URL.revokeObjectURL(url)
}
