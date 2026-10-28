import { useEffect, useState, type ReactNode } from 'react'
import { SESSION_EXPIRED_EVENT } from '../lib/api'
import { clearSession, readSession, saveSession, type Session } from '../lib/session'
import { RolContext } from './rol-context'
import { ROLES, type Rol } from './roles'

const CLAVE = 'genlab.rol-dev'

function rolInicial(): Rol {
  const guardado = localStorage.getItem(CLAVE)
  return ROLES.find((r) => r === guardado) ?? 'paciente'
}

export function RolProvider({ children }: { children: ReactNode }) {
  const [devRol, setDevRol] = useState<Rol>(rolInicial)
  const [session, setSession] = useState<Session | null>(readSession)

  useEffect(() => {
    const onExpired = () => setSession(null)
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired)
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired)
  }, [])

  const setRol = (nuevo: Rol) => {
    localStorage.setItem(CLAVE, nuevo)
    setDevRol(nuevo)
  }
  const startSession = (next: Session) => {
    saveSession(next)
    setSession(next)
  }
  const endSession = () => {
    clearSession()
    setSession(null)
  }

  const rol = session?.rol ?? devRol
  return (
    <RolContext.Provider value={{ rol, setRol, session, startSession, endSession }}>
      {children}
    </RolContext.Provider>
  )
}
