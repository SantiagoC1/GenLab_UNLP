import type { ReactNode } from 'react'

type Kind = 'error' | 'success' | 'info'

const COLORS: Record<Kind, string> = {
  error: 'border-red-300 bg-red-50 text-red-900',
  success: 'border-teal-300 bg-teal-50 text-teal-900',
  info: 'border-slate-300 bg-slate-100 text-slate-800',
}

export function Alert({ kind = 'info', children }: { kind?: Kind; children: ReactNode }) {
  return (
    <div
      role={kind === 'error' ? 'alert' : 'status'}
      className={`rounded-md border px-3 py-2 text-sm ${COLORS[kind]}`}
    >
      {children}
    </div>
  )
}
