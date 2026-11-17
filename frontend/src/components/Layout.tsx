import { useEffect, useRef, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { isMockRole, useMockActor, type MockRole } from '../lib/mockIdentity'
import { PANTALLAS } from '../roles/pantallas'
import { useRol } from '../roles/rol-context'
import { ETIQUETA_ROL } from '../roles/roles'
import { ChatbotPopup } from './ChatbotPopup'
import { SelectorDeRol } from './RoleSelector'

type NoticeSummary = {
  total: number
  pending_count: number
  has_pending: boolean
  simulated: boolean
}

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `flex min-h-11 items-center rounded-control px-3 py-2 text-sm transition-colors duration-150 ${
    isActive ? 'bg-brand font-medium text-white' : 'text-ink-soft hover:bg-page'
  }`

function NoticeMenuLink({ role }: { role: MockRole }) {
  const [actorId] = useMockActor(role)
  // The count is stored with the key it was fetched for, so it disappears when role, actor or route change
  // without resetting state synchronously inside the effect.
  const [pending, setPending] = useState<{ key: string; count: number } | null>(null)
  const location = useLocation()
  const key = `${role}:${actorId}:${location.pathname}`
  const pendingCount = pending?.key === key ? pending.count : null

  useEffect(() => {
    let active = true

    async function refresh() {
      try {
        const params = new URLSearchParams({
          role,
          actor_id: actorId,
        })

        const data = await api<NoticeSummary>(`/notifications/summary?${params.toString()}`)

        if (active) setPending({ key, count: data.pending_count })
      } catch {
        if (active) setPending(null)
      }
    }

    void refresh()

    const interval = window.setInterval(() => void refresh(), 15000)

    return () => {
      active = false
      window.clearInterval(interval)
    }
  }, [role, actorId, key])

  return (
    <NavLink to="/avisos" className={linkClass}>
      <span className="flex items-center justify-between gap-2">
        <span>Avisos</span>
        {pendingCount !== null && pendingCount > 0 && (
          <span
            aria-label={`${pendingCount} avisos pendientes`}
            className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-900"
          >
            {pendingCount}
          </span>
        )}
      </span>
    </NavLink>
  )
}

export function Layout() {
  const { rol, session, endSession } = useRol()
  const navigate = useNavigate()
  const location = useLocation()
  const [open, setOpen] = useState(false)
  const menuButton = useRef<HTMLButtonElement>(null)
  const panel = useRef<HTMLElement>(null)
  const menu = PANTALLAS.filter((p) => p.rol === rol)

  const close = (restoreFocus: boolean) => {
    setOpen(false)
    if (restoreFocus) menuButton.current?.focus()
  }

  // Esc closes the panel; focus moves into it when it opens (below 1024px it is a drawer).
  useEffect(() => {
    if (!open) return
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close(true)
    }
    window.addEventListener('keydown', onKeyDown)
    panel.current?.querySelector<HTMLElement>('a, button')?.focus()
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open])

  // Lock page scroll behind the open drawer.
  useEffect(() => {
    document.body.style.overflow = open ? 'hidden' : ''
    return () => {
      document.body.style.overflow = ''
    }
  }, [open])

  return (
    <div className="min-h-dvh lg:flex">
      <header className="sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-line-soft bg-surface px-4 py-2 pt-[max(0.5rem,env(safe-area-inset-top))] lg:hidden">
        <span className="text-lg font-semibold text-brand-strong">GenLab</span>
        <button
          ref={menuButton}
          type="button"
          aria-label="Abrir menú"
          aria-expanded={open}
          aria-controls="main-navigation"
          onClick={() => setOpen((v) => !v)}
          className="min-h-11 min-w-11 rounded-control border border-line px-3 text-sm font-medium text-ink transition-colors duration-150 hover:bg-page"
        >
          Menú
        </button>
      </header>

      {open && (
        <div
          aria-hidden="true"
          onClick={() => close(true)}
          className="fixed inset-0 z-40 animate-fade-in bg-ink/40 lg:hidden"
        />
      )}

      <aside
        id="main-navigation"
        ref={panel}
        className={`${open ? 'animate-slide-in' : 'invisible'} fixed inset-y-0 left-0 z-50 flex w-72 max-w-[85vw] flex-col overflow-y-auto border-r border-line-soft bg-surface p-4 pb-[max(1rem,env(safe-area-inset-bottom))] lg:visible lg:sticky lg:top-0 lg:z-auto lg:h-dvh lg:w-64 lg:max-w-none lg:shrink-0 lg:animate-none`}
      >
        <div className="mb-4 flex items-start justify-between gap-2">
          <div>
            <p className="text-lg font-semibold text-brand-strong">GenLab</p>
            <p className="text-sm text-muted">{ETIQUETA_ROL[rol]}</p>
          </div>
          <button
            type="button"
            aria-label="Cerrar menú"
            onClick={() => close(true)}
            className="min-h-11 min-w-11 rounded-control text-xl leading-none text-muted hover:bg-page lg:hidden"
          >
            ×
          </button>
        </div>

        <nav aria-label="Principal" className="space-y-1" onClick={() => close(false)}>
          {menu.map((p) => (
            <NavLink key={p.ruta} to={`/${p.rol}/${p.ruta}`} className={linkClass}>
              {p.titulo}
            </NavLink>
          ))}

          {isMockRole(rol) ? (
            <NoticeMenuLink role={rol} />
          ) : (
            <NavLink to="/avisos" className={linkClass}>
              Avisos
            </NavLink>
          )}
        </nav>

        <div className="mt-auto space-y-3 pt-6">
          <SelectorDeRol />
          {session && (
            <button
              type="button"
              onClick={() => {
                endSession()
                navigate('/ingresar')
              }}
              className="min-h-11 w-full rounded-control border border-line px-3 py-2 text-left text-sm text-ink-soft transition-colors duration-150 hover:bg-page"
            >
              Cerrar sesión
            </button>
          )}
        </div>
      </aside>

      <main key={location.pathname} className="min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-10 lg:py-8">
        <Outlet />
        {/* Room so the floating chatbot button never covers the last action of a screen */}
        {rol === 'paciente' && <div aria-hidden="true" className="h-20" />}
      </main>

      {rol === 'paciente' && <ChatbotPopup />}
    </div>
  )
}
