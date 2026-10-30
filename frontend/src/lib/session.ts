import { ROLES, type Rol } from '../roles/roles'

export interface Session {
  token: string
  rol: Rol
  mustChangePassword: boolean
}

const SESSION_KEY = 'genlab.session'
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
