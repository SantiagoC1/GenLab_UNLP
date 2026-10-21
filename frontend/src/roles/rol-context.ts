import { createContext, useContext } from 'react'
import type { Rol } from './roles'

interface RolContextValue {
  rol: Rol
  setRol: (rol: Rol) => void
}

export const RolContext = createContext<RolContextValue | null>(null)

export function useRol(): RolContextValue {
  const ctx = useContext(RolContext)
  if (!ctx) throw new Error('useRol debe usarse dentro de RolProvider')
  return ctx
}
