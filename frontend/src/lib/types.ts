export type Duygu = 'olumlu' | 'nötr' | 'olumsuz'

export interface AnalizSonucu {
  etiket: Duygu
  guven: number
  olasiliklar: Record<Duygu, number>
}

export interface TopluSonucSatiri {
  metin: string
  etiket: Duygu
  guven: number
}

export interface TopluAnalizSonucu {
  toplam: number
  sonuclar: TopluSonucSatiri[]
}

export interface KelimeOnemi {
  kelime: string
  onem: number
}

export interface KonuSonucu {
  konu: string
  parca: string
  etiket: Duygu
  guven: number
}

export interface SaglikDurumu {
  durum: string
  model: string
  model_yuklu: boolean
}
