interface HeaderProps {
  karanlik: boolean
  onTemaDegistir: () => void
}

export function Header({ karanlik, onTemaDegistir }: HeaderProps) {
  return (
    <header className="flex items-center justify-between gap-4 border-b border-[var(--border)] py-6">
      <div className="flex items-center gap-3.5">
        <svg viewBox="0 0 52 52" className="h-9 w-9 shrink-0" aria-hidden="true">
          <circle cx="26" cy="26" r="24" fill="none" stroke="var(--accent)" strokeWidth="1.4" />
          <circle cx="26" cy="26" r="1.8" fill="var(--brass)" />
          <path d="M26 4 L29.5 23 L26 26 L22.5 23 Z" fill="var(--accent)" />
          <path d="M26 48 L22.5 29 L26 26 L29.5 29 Z" fill="none" stroke="var(--accent)" strokeWidth="1" />
          <path d="M4 26 L23 22.5 L26 26 L23 29.5 Z" fill="none" stroke="var(--accent)" strokeWidth="1" />
          <path d="M48 26 L29 29.5 L26 26 L29 22.5 Z" fill="none" stroke="var(--accent)" strokeWidth="1" />
        </svg>
        <div>
          <div className="font-[var(--font-display)] text-xl leading-none font-semibold tracking-tight text-[var(--text-primary)]">Yorum Pusulası</div>
          <div className="mt-0.5 font-[var(--font-display)] text-[11px] text-[var(--text-muted)] italic">Müşteri sesine yön bul</div>
        </div>
      </div>

      <div className="flex items-center gap-6">
        <button
          type="button"
          role="switch"
          aria-checked={karanlik}
          onClick={onTemaDegistir}
          className="flex items-center gap-2 rounded-full border border-[var(--border)] py-1.5 pr-3.5 pl-1.5 text-xs font-medium text-[var(--text-secondary)]"
        >
          <span
            className="relative inline-flex h-[19px] w-[34px] shrink-0 items-center rounded-full p-0.5 transition-colors"
            style={{ background: karanlik ? 'var(--brass)' : 'var(--gridline)' }}
          >
            <span
              className="inline-block h-[15px] w-[15px] rounded-full bg-[var(--page-plane)] shadow transition-transform"
              style={{ transform: karanlik ? 'translateX(15px)' : 'translateX(0)' }}
            />
          </span>
          Gece rotası
        </button>
      </div>
    </header>
  )
}
