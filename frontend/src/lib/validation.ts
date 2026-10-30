import type { NewUserPayload } from './access'
import type { Rol } from '../roles/roles'

export const MIN_PASSWORD_LENGTH = 8

export interface PersonData {
  rol: Rol | ''
  firstName: string
  lastName: string
  phone: string
  email: string
  licenseNumber: string
  specialties: number[]
  province: string
}

export const EMPTY_PERSON: PersonData = {
  rol: '',
  firstName: '',
  lastName: '',
  phone: '',
  email: '',
  licenseNumber: '',
  specialties: [],
  province: '',
}

export type Errors = Partial<Record<string, string>>

const EMAIL_FORMAT = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

// Los mensajes son lo que lee la persona, así que van en español (vocabulario del LEL).

/** Valida lo que tienen en común el registro (escenario 1) y el alta del administrador (escenario 2). */
export function validatePerson(v: PersonData): Errors {
  const errors: Errors = {}
  if (!v.rol) errors.rol = 'Elegí un rol.'
  if (!v.firstName.trim()) errors.firstName = 'Completá el nombre.'
  if (!v.lastName.trim()) errors.lastName = 'Completá el apellido.'
  if (!v.phone.trim()) errors.phone = 'Completá el teléfono de contacto.'
  if (!v.email.trim()) errors.email = 'Completá el mail.'
  else if (!EMAIL_FORMAT.test(v.email.trim())) errors.email = 'El mail no es válido.'
  if (v.rol === 'medico_tratante') {
    if (!v.licenseNumber.trim()) errors.licenseNumber = 'Completá la matrícula.'
    if (v.specialties.length === 0) errors.specialties = 'Elegí al menos una especialidad.'
  }
  if (v.rol === 'transportista' && !v.province) {
    errors.province = 'Elegí la provincia que cubre.'
  }
  return errors
}

export function validateNewPassword(password: string): string | undefined {
  if (!password) return 'Definí una contraseña.'
  if (password.length < MIN_PASSWORD_LENGTH) {
    return `La contraseña debe tener al menos ${MIN_PASSWORD_LENGTH} caracteres.`
  }
}

/** Lo que se envía al backend: solo los campos que corresponden al rol. */
export function toPayload(v: PersonData): NewUserPayload {
  const rol = v.rol as Rol
  return {
    role: rol,
    first_name: v.firstName.trim(),
    last_name: v.lastName.trim(),
    phone: v.phone.trim(),
    email: v.email.trim().toLowerCase(),
    ...(rol === 'medico_tratante'
      ? { license_number: v.licenseNumber.trim(), specialties: v.specialties }
      : {}),
    ...(rol === 'transportista' ? { province: v.province } : {}),
  }
}
