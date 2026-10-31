
import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import {isMockRole, useMockActor, type MockRole } from '../lib/mockIdentity'
import { PANTALLAS } from '../roles/pantallas'
import { useRol } from '../roles/rol-context'
import { ETIQUETA_ROL } from '../roles/roles'
import { SelectorDeRol } from './RoleSelector'

type NoticeSummary = {
  total: number
  pending_count: number
  has_pending: boolean
  simulated: boolean
}

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `block rounded-md px-3 py-2 text-sm ${
    isActive ? 'bg-teal-700 text-white' : 'text-slate-700 hover:bg-slate-100'
  }`

function NoticeMenuLink({ role }: { role: MockRole }) {
  const [actorId] = useMockActor(role)
  const [pendingCount, setPendingCount] = useState<number | null>(null)
  const location = useLocation()

  useEffect(() => {
    let active = true

    async function refresh() {
      try {
        const params = new URLSearchParams({
          role,
          actor_id: actorId,
        })

        const data = await api<NoticeSummary>(
          `/notifications/summary?${params.toString()}`,
        )

        if (active) setPendingCount(data.pending_count)
      } catch {
        if (active) setPendingCount(null)
      }
    }

    setPendingCount(null)
    void refresh()

    const interval = window.setInterval(() => void refresh(), 15000)

    return () => {
      active = false
      window.clearInterval(interval)
    }
  }, [role, actorId, location.pathname])

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
  const [open, setOpen] = useState(false)
  const menu = PANTALLAS.filter((screen) => screen.rol === rol)

  return (
    <div className="min-h-screen bg-slate-50 md:flex">
      <header className="flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3 md:hidden">
        <span className="font-semibold text-teal-800">GenLab</span>
        <SelectorDeRol />
        <button
          type="button"
          aria-label="Abrir menú"
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
          className="rounded border border-slate-300 px-3 py-1 text-sm"
        >
          Menú
        </button>
      </header>

      <aside
        className={`${open ? 'block' : 'hidden'} border-b border-slate-200 bg-white p-4 md:block md:w-64 md:shrink-0 md:border-b-0 md:border-r`}
      >
        <div className="mb-4 hidden md:block">
          <p className="text-lg font-semibold text-teal-800">GenLab</p>
          <p className="text-xs text-slate-500">{ETIQUETA_ROL[rol]}</p>
        </div>

        <nav
          aria-label="Principal"
          className="space-y-1"
          onClick={() => setOpen(false)}
        >
          {menu.map((screen) => (
            <NavLink
              key={screen.ruta}
              to={`/${screen.rol}/${screen.ruta}`}
              className={linkClass}
            >
              {screen.titulo}
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

        <div className="mt-6 hidden md:block">
          <SelectorDeRol />
        </div>

        {session && (
          <button
            type="button"
            onClick={() => {
              endSession()
              navigate('/ingresar')
            }}
            className="mt-4 w-full rounded-md border border-slate-300 px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-100"
          >
            Cerrar sesión
          </button>
        )}
      </aside>

      <main className="flex-1 p-4 sm:p-6 lg:p-8">
        <Outlet />
      </main>
    </div>
  )
}
