import { api, json } from './api'
import { getDeviceId, type Session } from './session'
import type { Rol } from '../roles/roles'

// Types mirror the JSON of the backend (modules/acceso/schemas.py), hence the snake_case.

export interface SessionResponse {
  access_token: string
  role: Rol
  must_change_password: boolean
}

export interface LoginResponse {
  state: 'code_sent' | 'authenticated'
  session: SessionResponse | null
}

export interface Specialty {
  id: number
  name: string
}

export interface Catalogs {
  specialties: Specialty[]
  provinces: string[]
}

export interface User {
  id: string
  first_name: string
  last_name: string
  email: string
  phone: string
  role: Rol
  province: string | null
  license_number: string | null
  blocked: boolean
}

export interface NewUserPayload {
  role: Rol
  first_name: string
  last_name: string
  phone: string
  email: string
  license_number?: string
  specialties?: number[]
  province?: string
}

export const toSession = (s: SessionResponse): Session => ({
  token: s.access_token,
  rol: s.role,
  mustChangePassword: s.must_change_password,
})

export const getCatalogs = () => api<Catalogs>('/acceso/catalogs')

export const register = (payload: NewUserPayload & { password: string }) =>
  api<SessionResponse>('/acceso/register', {
    method: 'POST',
    ...json({ ...payload, device_id: getDeviceId() }),
  })

export const login = (email: string, password: string) =>
  api<LoginResponse>('/acceso/login', {
    method: 'POST',
    ...json({ email, password, device_id: getDeviceId() }),
  })

export const verifyCode = (email: string, code: string) =>
  api<SessionResponse>('/acceso/verify-code', {
    method: 'POST',
    ...json({ email, code, device_id: getDeviceId() }),
  })

export const changePassword = (current: string, newPassword: string, confirmation: string) =>
  api<{ state: string }>('/acceso/change-password', {
    method: 'POST',
    ...json({ current_password: current, new_password: newPassword, confirmation }),
  })

export const listUsers = () => api<User[]>('/acceso/users')

export const createUser = (payload: NewUserPayload) =>
  api<User>('/acceso/users', { method: 'POST', ...json(payload) })
