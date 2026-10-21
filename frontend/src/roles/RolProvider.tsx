import { useState, type ReactNode } from 'react'
import { RolContext } from './rol-context'
import { ROLES, type Rol } from './roles'

const CLAVE = 'genlab.rol-dev'

function rolInicial(): Rol {
  const guardado = localStorage.getItem(CLAVE)
  return ROLES.find((r) => r === guardado) ?? 'paciente'
}

/**
 * Hasta que exista el ingreso real (tarea 1.4), el rol sale del selector de desarrollo.
 * TODO: reemplazar por el rol del usuario autenticado.
 */
export function RolProvider({ children }: { children: ReactNode }) {
  const [rol, setRolState] = useState<Rol>(rolInicial)
  const setRol = (nuevo: Rol) => {
    localStorage.setItem(CLAVE, nuevo)
    setRolState(nuevo)
  }
  return <RolContext.Provider value={{ rol, setRol }}>{children}</RolContext.Provider>
}
