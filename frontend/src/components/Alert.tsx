import type { ReactNode } from 'react'

type Kind = 'error' | 'success' | 'info' | 'warning'

const COLORS: Record<Kind, string> = {
  error: 'border-danger-line bg-danger-soft text-danger',
  success: 'border-success-line bg-success-soft text-success',
  warning: 'border-warning-line bg-warning-soft text-warning',
  info: 'border-line bg-page text-ink-soft',
}

// Color is never the only signal: each kind also has a symbol.
const SYMBOLS: Record<Kind, string> = { error: '!', success: '✓', warning: '!', info: 'i' }

export function Alert({ kind = 'info', children }: { kind?: Kind; children: ReactNode }) {
  return (
    <div
      role={kind === 'error' ? 'alert' : 'status'}
      className={`flex gap-3 rounded-control border px-3 py-2.5 text-sm ${COLORS[kind]}`}
    >
      <span
        aria-hidden="true"
        className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full border border-current text-xs font-bold"
      >
        {SYMBOLS[kind]}
      </span>
      <div className="min-w-0 flex-1 break-words">{children}</div>
    </div>
  )
}
