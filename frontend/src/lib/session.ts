import { ROLES, type Rol } from '../roles/roles'

export interface Session {
  token: string
  rol: Rol
  mustChangePassword: boolean
}

const SESSION_KEY = 'genlab.session'
/** Rol elegido en el selector DEV (solo desarrollo). */
export const DEV_ROLE_KEY = 'genlab.rol-dev'
/** Cuenta opcional para el modo DEV: se manda como X-Dev-User. */
export const DEV_USER_KEY = 'genlab.user-dev'
const DEVICE_KEY = 'genlab.device'

/** La sesión vive solo en la pestaña (sessionStorage): al cerrarla hay que volver a ingresar. */
export function readSession(): Session | null {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY)
    if (!raw) return null
    const session = JSON.parse(raw) as Session
    const validRole = (ROLES as readonly string[]).includes(session.rol)
    return session.token && validRole ? session : null
  } catch {
    return null
  }
}

/**
 * Solo en desarrollo y sin sesión real: encabezados que el backend acepta cuando tiene
 * DEV_AUTH=true. En un build de producción (`import.meta.env.DEV` falso) no manda nada.
 */
export function devHeaders(): Record<string, string> {
  if (!import.meta.env.DEV || readSession()) return {}
  const guardado = localStorage.getItem(DEV_ROLE_KEY)
  const rol = ROLES.find((r) => r === guardado) ?? 'paciente'
  const usuario = localStorage.getItem(DEV_USER_KEY)
  return { 'X-Dev-Role': rol, ...(usuario ? { 'X-Dev-User': usuario } : {}) }
}

export function saveSession(session: Session): void {
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(session))
}

export function clearSession(): void {
  sessionStorage.removeItem(SESSION_KEY)
}

/**
 * Identificador de este navegador. El backend lo usa para decidir si hace falta el código de
 * verificación (M1-RF8: solo se mira el dispositivo, no la red). Queda en localStorage para que
 * sobreviva al cierre de la pestaña.
 */
export function getDeviceId(): string {
  let id = localStorage.getItem(DEVICE_KEY)
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem(DEVICE_KEY, id)
  }
  return id
}
