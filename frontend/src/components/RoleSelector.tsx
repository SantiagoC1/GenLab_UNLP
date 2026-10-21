import { useNavigate } from 'react-router-dom'
import { initialScreen } from '../roles/pantallas'
import { useRol } from '../roles/rol-context'
import { ETIQUETA_ROL, ROLES, type Rol } from '../roles/roles'

/** Solo en modo desarrollo: permite recorrer la aplicación como cualquier rol. */
export function SelectorDeRol() {
  const { rol, setRol, session } = useRol()
  const navegar = useNavigate()
  if (!import.meta.env.DEV || session) return null

  const cambiar = (nuevo: Rol) => {
    setRol(nuevo)
    const inicio = initialScreen(nuevo)
    navegar(inicio ? `/${nuevo}/${inicio}` : '/')
  }

  return (
    <label className="flex items-center gap-2 text-xs text-amber-900">
      <span className="rounded bg-amber-200 px-1.5 py-0.5 font-medium">DEV</span>
      <select
        aria-label="Rol de desarrollo"
        value={rol}
        onChange={(e) => cambiar(e.target.value as Rol)}
        className="rounded border border-amber-300 bg-white px-2 py-1 text-sm text-slate-900"
      >
        {ROLES.map((r) => (
          <option key={r} value={r}>
            {ETIQUETA_ROL[r]}
          </option>
        ))}
      </select>
    </label>
  )
}
