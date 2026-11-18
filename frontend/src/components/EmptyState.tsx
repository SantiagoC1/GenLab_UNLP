import type { ReactNode } from 'react'

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-card border border-dashed border-line bg-surface p-6 text-center text-sm text-muted sm:p-10">
      {children}
    </div>
  )
}
