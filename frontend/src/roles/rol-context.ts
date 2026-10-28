import { createContext, useContext } from 'react'
import type { Session } from '../lib/session'
import type { Rol } from './roles'

interface RolContextValue {
  /** Role of the session. Without a session (development only), the one in the dev selector. */
  rol: Rol

  setRol: (rol: Rol) => void
  session: Session | null
  startSession: (session: Session) => void
  endSession: () => void
}

export const RolContext = createContext<RolContextValue | null>(null)

export function useRol(): RolContextValue {
  const ctx = useContext(RolContext)
  if (!ctx) throw new Error('useRol debe usarse dentro de RolProvider')
  return ctx
}
