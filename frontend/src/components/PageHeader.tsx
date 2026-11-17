import type { ReactNode } from 'react'

interface Props {
  title: string
  /** Internal scenario reference. Only shown in development, never to the user. */
  reference?: string
  children?: ReactNode
}

export function PageHeader({ title, reference, children }: Props) {
  return (
    <header className="mb-6">
      <h1 className="text-title font-semibold text-ink">{title}</h1>
      {import.meta.env.DEV && reference && <p className="mt-1 text-sm text-muted">{reference}</p>}
      {children}
    </header>
  )
}
