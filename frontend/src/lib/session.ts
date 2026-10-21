import { ROLES, type Rol } from '../roles/roles'

export interface Session {
  token: string
  rol: Rol
  mustChangePassword: boolean
}

const SESSION_KEY = 'genlab.session'
const DEVICE_KEY = 'genlab.device'

/** The session lives only in the tab (sessionStorage): closing it means logging in again. */
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
 * Identifier of this browser. The backend uses it, together with the network, to decide whether
 * a verification code is needed (M1-RF8). Kept in localStorage so it survives closing the tab.
 */
export function getDeviceId(): string {
  let id = localStorage.getItem(DEVICE_KEY)
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem(DEVICE_KEY, id)
  }
  return id
}
