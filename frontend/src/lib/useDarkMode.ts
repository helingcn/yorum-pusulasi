import { useCallback, useEffect, useState } from 'react'

const DEPOLAMA_ANAHTARI = 'yorum-pusulasi-tema'

function baslangicDegeriniBul(): boolean {
  try {
    const kayitli = localStorage.getItem(DEPOLAMA_ANAHTARI)
    if (kayitli === 'karanlik') return true
    if (kayitli === 'aydinlik') return false
  } catch {
    // localStorage isn't accessible (private tab, etc.) — fall back to OS preference.
  }
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
}

/**
 * Manages dark mode via the <html class="dark"> class — Tailwind's `dark:`
 * variant picks this up automatically. Issues we hit in the Streamlit
 * version, like "the OS @media query colliding with the manual toggle" and
 * "the toggle's visual layer swallowing clicks," are architecturally
 * impossible here: a single source of truth (this state), a real
 * <button>, no third-party switch component.
 */
export function useDarkMode(): [boolean, () => void] {
  const [karanlik, setKaranlik] = useState<boolean>(baslangicDegeriniBul)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', karanlik)
    try {
      localStorage.setItem(DEPOLAMA_ANAHTARI, karanlik ? 'karanlik' : 'aydinlik')
    } catch {
      // May not be writable to persistent storage — not a problem, still works for this session.
    }
  }, [karanlik])

  const degistir = useCallback(() => setKaranlik((onceki) => !onceki), [])

  return [karanlik, degistir]
}
