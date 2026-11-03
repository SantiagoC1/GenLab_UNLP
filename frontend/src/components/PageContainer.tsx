import type { ReactNode } from 'react'

/** Centered content column with a max width, used by every screen. */
export function PageContainer({ children }: { children: ReactNode }) {
  return <section className="mx-auto w-full max-w-3xl animate-fade-in">{children}</section>
}
