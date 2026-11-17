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
    <label className="block rounded-control border border-warning-line bg-warning-soft p-2 text-xs text-warning">
      <span className="mb-1 block font-semibold">DEV · rol</span>
      <select
        aria-label="Rol de desarrollo"
        value={rol}
        onChange={(e) => cambiar(e.target.value as Rol)}
        className="block min-h-11 w-full min-w-0 rounded-control border border-warning-line bg-surface px-2 py-1 text-base text-ink"
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
