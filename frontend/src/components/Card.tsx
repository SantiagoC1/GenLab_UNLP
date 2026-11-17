import type { ReactNode } from 'react'

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-card border border-line-soft bg-surface p-4 shadow-card sm:p-6 ${className}`}
    >
      {children}
    </div>
  )
}
