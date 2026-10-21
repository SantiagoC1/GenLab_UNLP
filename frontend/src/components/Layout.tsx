import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { PANTALLAS } from '../roles/pantallas'
import { useRol } from '../roles/rol-context'
import { ETIQUETA_ROL } from '../roles/roles'
import { SelectorDeRol } from './SelectorDeRol'

const claseLink = ({ isActive }: { isActive: boolean }) =>
  `block rounded-md px-3 py-2 text-sm ${
    isActive ? 'bg-teal-700 text-white' : 'text-slate-700 hover:bg-slate-100'
  }`

export function Layout() {
  const { rol } = useRol()
  const [abierto, setAbierto] = useState(false)
  const menu = PANTALLAS.filter((p) => p.rol === rol)

  return (
    <div className="min-h-screen bg-slate-50 md:flex">
      <header className="flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3 md:hidden">
        <span className="font-semibold text-teal-800">GenLab</span>
        <SelectorDeRol />
        <button
          type="button"
          aria-label="Abrir menú"
          aria-expanded={abierto}
          onClick={() => setAbierto((v) => !v)}
          className="rounded border border-slate-300 px-3 py-1 text-sm"
        >
          Menú
        </button>
      </header>

      <aside
        className={`${abierto ? 'block' : 'hidden'} border-b border-slate-200 bg-white p-4 md:block md:w-64 md:shrink-0 md:border-b-0 md:border-r`}
      >
        <div className="mb-4 hidden md:block">
          <p className="text-lg font-semibold text-teal-800">GenLab</p>
          <p className="text-xs text-slate-500">{ETIQUETA_ROL[rol]}</p>
        </div>
        <nav aria-label="Principal" className="space-y-1" onClick={() => setAbierto(false)}>
          {menu.map((p) => (
            <NavLink key={p.ruta} to={`/${p.rol}/${p.ruta}`} className={claseLink}>
              {p.titulo}
            </NavLink>
          ))}
          <NavLink to="/avisos" className={claseLink}>
            Avisos
          </NavLink>
        </nav>
        <div className="mt-6 hidden md:block">
          <SelectorDeRol />
        </div>
      </aside>

      <main className="flex-1 p-4 sm:p-6 lg:p-8">
        <Outlet />
      </main>
    </div>
  )
}
