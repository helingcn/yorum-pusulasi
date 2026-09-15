import { useCallback, useEffect, useState } from 'react'

const DEPOLAMA_ANAHTARI = 'yorum-pusulasi-tema'

function baslangicDegeriniBul(): boolean {
  try {
    const kayitli = localStorage.getItem(DEPOLAMA_ANAHTARI)
    if (kayitli === 'karanlik') return true
    if (kayitli === 'aydinlik') return false
  } catch {
    // localStorage erişilemiyor (gizli sekme vb.) — OS tercihine düş.
  }
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
}

/**
 * Karanlık modu <html class="dark"> üzerinden yönetir — Tailwind'in
 * `dark:` varyantı bunu otomatik kullanır. Streamlit sürümünde yaşanan
 * "OS @media sorgusu ile manuel toggle'ın çakışması" ve "toggle'ın görsel
 * katmanının tıklamayı yutması" gibi sorunlar burada mimari olarak
 * mümkün değil: tek kaynak (bu state), gerçek bir <button>, üçüncü parti
 * bir switch bileşeni yok.
 */
export function useDarkMode(): [boolean, () => void] {
  const [karanlik, setKaranlik] = useState<boolean>(baslangicDegeriniBul)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', karanlik)
    try {
      localStorage.setItem(DEPOLAMA_ANAHTARI, karanlik ? 'karanlik' : 'aydinlik')
    } catch {
      // Kalıcı hafızaya yazılamıyor olabilir — sorun değil, bu oturumda çalışır.
    }
  }, [karanlik])

  const degistir = useCallback(() => setKaranlik((onceki) => !onceki), [])

  return [karanlik, degistir]
}
