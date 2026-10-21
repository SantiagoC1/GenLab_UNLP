import { clearSession, readSession } from './session'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'


export const SESSION_EXPIRED_EVENT = 'genlab:session-expired'

export interface FieldError {
  field: string
  message: string
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code?: string,
    public errors: FieldError[] = [],
  ) {
    super(message)
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const session = readSession()
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(session ? { Authorization: `Bearer ${session.token}` } : {}),
      ...init?.headers,
    },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    if (response.status === 401 && body.code === 'invalid_session') {
      clearSession()
      window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT))
    }
    // `detalle` is the error format of the whole backend (core/errors.py)
    const message = body.detalle ?? body.detail ?? response.statusText
    throw new ApiError(response.status, message, body.code, body.errors)
  }
  return response.json() as Promise<T>
}

/** JSON body for api(): api('/path', { method: 'POST', ...json({ a: 1 }) }) */
export function json(body: unknown): { body: string } {
  return { body: JSON.stringify(body) }
}
