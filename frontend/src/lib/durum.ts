import type { Duygu } from './types'

export const DUYGU_BILGISI: Record<Duygu, { renk: string; baslik: string; barRengi: string }> = {
  olumlu: { renk: 'var(--good)', baslik: 'Olumlu', barRengi: 'var(--good)' },
  nötr: { renk: 'var(--brass-text)', baslik: 'Nötr', barRengi: 'var(--brass)' },
  olumsuz: { renk: 'var(--critical-text)', baslik: 'Olumsuz', barRengi: 'var(--critical)' },
}

export function guvenDurumu(guven: number): { baslik: string; sinif: 'low' | 'medium' | 'high'; aciklama: string } {
  if (guven < 0.65) {
    return {
      baslik: 'İnceleme önerilir',
      sinif: 'low',
      aciklama: 'Model bu yorumda kararsız. Sonucu manuel olarak kontrol etmeni öneririz.',
    }
  }
  if (guven < 0.8) {
    return {
      baslik: 'Orta güven',
      sinif: 'medium',
      aciklama: 'Sonuç kullanılabilir; önemli kararlar için yorumu da incelemeni öneririz.',
    }
  }
  return { baslik: 'Yüksek güven', sinif: 'high', aciklama: 'Modelin bu sınıflandırmaya güveni yüksek.' }
}

export const GUVEN_NOT_STILI: Record<'low' | 'medium' | 'high', string> = {
  low: 'bg-[color-mix(in_oklch,var(--critical)_12%,var(--surface-1))] text-[var(--critical-text)] border-[color-mix(in_oklch,var(--critical)_35%,transparent)]',
  medium: 'bg-[color-mix(in_oklch,var(--brass)_16%,var(--surface-1))] text-[var(--brass-text)] border-[color-mix(in_oklch,var(--brass)_45%,transparent)]',
  high: 'bg-[color-mix(in_oklch,var(--good)_12%,var(--surface-1))] text-[var(--good)] border-[color-mix(in_oklch,var(--good)_35%,transparent)]',
}
