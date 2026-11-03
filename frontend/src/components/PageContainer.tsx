import type { ReactNode } from 'react'

/** Centered content column with a max width, used by every screen. `wide` is for tables. */
export function PageContainer({ children, wide = false }: { children: ReactNode; wide?: boolean }) {
  return (
    <section className={`mx-auto w-full animate-fade-in ${wide ? 'max-w-5xl' : 'max-w-3xl'}`}>
      {children}
    </section>
  )
}
