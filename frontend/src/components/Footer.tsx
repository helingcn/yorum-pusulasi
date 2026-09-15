export function Footer() {
  return (
    <footer className="mt-14 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--border)] pt-5 text-[11.5px] text-[var(--text-muted)]">
      <span>Yorum Pusulası · Türkçe müşteri yorumları için 3 sınıflı duygu analizi</span>
      <div className="flex items-center gap-1.5 font-[var(--font-display)] italic">
        <svg viewBox="0 0 52 52" className="h-3.5 w-3.5" aria-hidden="true">
          <circle cx="26" cy="26" r="24" fill="none" stroke="var(--text-muted)" strokeWidth="2" />
          <circle cx="26" cy="26" r="1.8" fill="var(--brass)" />
        </svg>
        Kuzey her zaman yukarıda.
      </div>
    </footer>
  )
}
