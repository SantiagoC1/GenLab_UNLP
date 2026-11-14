import { useMutation } from '@tanstack/react-query'
import { api, json } from './api'
import type { Symptom } from './symptoms'
import type { Errors } from './validation'

export type SuspicionType = 'clinica' | 'familiar'

/** Los datos del formulario de alta de paciente, tal como se escriben en pantalla. */
export interface PatientForm {
  dni: string
  firstName: string
  lastName: string
  birthDate: string
  phone: string
  email: string
  suspicionType: SuspicionType | ''
  pathologyIds: number[]
  clinicalSummary: string
  symptoms: Symptom[]
}

export const EMPTY_PATIENT_FORM: PatientForm = {
  dni: '',
  firstName: '',
  lastName: '',
  birthDate: '',
  phone: '',
  email: '',
  suspicionType: '',
  pathologyIds: [],
  clinicalSummary: '',
  symptoms: [],
}

/** La respuesta del backend al buscar o al dar de alta a un paciente. */
export interface Patient {
  id: string
  dni: string
  first_name: string
  last_name: string
  birth_date: string
}

export interface CreatedPatient extends Patient {
  account_created: boolean
}

export const AGE_OF_MAJORITY = 18
export const MAX_NAME_LENGTH = 100
export const MAX_PHONE_LENGTH = 30
export const MAX_EMAIL_LENGTH = 254
export const MAX_SUMMARY_LENGTH = 5000
const DNI_FORMAT = /^[0-9]{7,8}$/
const EMAIL_FORMAT = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

/**
 * Indica si la fecha (AAAA-MM-DD) corresponde a un menor de 18 años. Sirve para avisar en
 * pantalla que el mail es el de los padres. `today` se puede pasar para probarla con fechas fijas.
 */
export function isMinor(birthDate: string, today: Date = new Date()): boolean {
  const birth = new Date(`${birthDate}T00:00:00`)
  if (Number.isNaN(birth.getTime())) return false
  const hadBirthday =
    today.getMonth() > birth.getMonth() ||
    (today.getMonth() === birth.getMonth() && today.getDate() >= birth.getDate())
  const age = today.getFullYear() - birth.getFullYear() - (hadBirthday ? 0 : 1)
  return age < AGE_OF_MAJORITY
}

/** Devuelve la fecha de hoy como AAAA-MM-DD (hora local). Se usa para limitar el campo de fecha. */
export function todayAsIso(today: Date = new Date()): string {
  const month = String(today.getMonth() + 1).padStart(2, '0')
  const day = String(today.getDate()).padStart(2, '0')
  return `${today.getFullYear()}-${month}-${day}`
}

/** Indica si el DNI tiene el formato que acepta el backend: 7 u 8 dígitos. */
export function isValidDni(dni: string): boolean {
  return DNI_FORMAT.test(dni.trim())
}

/**
 * Valida el formulario antes de enviarlo. El backend repite estas reglas (y es el que manda): acá
 * se hacen para avisar rápido y campo por campo. Los mensajes de formato son los mismos que los
 * del backend; los de campo vacío son más cortos ("Completá el nombre.").
 *
 * En una sospecha familiar los síntomas pueden faltar (P1), por eso solo se exigen en la clínica.
 * Los topes de largo no se validan acá: los campos de la pantalla ya traen `maxLength`.
 */
export function validatePatient(form: PatientForm, today: Date = new Date()): Errors {
  const errors: Errors = {}
  if (!form.dni.trim()) errors.dni = 'Completá el DNI.'
  else if (!isValidDni(form.dni)) errors.dni = 'El DNI tiene que tener 7 u 8 dígitos.'
  if (!form.firstName.trim()) errors.firstName = 'Completá el nombre.'
  if (!form.lastName.trim()) errors.lastName = 'Completá el apellido.'
  if (!form.birthDate) errors.birthDate = 'Completá la fecha de nacimiento.'
  else if (form.birthDate > todayAsIso(today)) {
    errors.birthDate = 'La fecha de nacimiento no puede ser futura.'
  }
  if (!form.phone.trim()) errors.phone = 'Completá el teléfono.'
  if (!form.email.trim()) errors.email = 'Completá el mail.'
  else if (!EMAIL_FORMAT.test(form.email.trim()))
    errors.email = 'El mail no tiene un formato válido.'
  if (!form.suspicionType) errors.suspicionType = 'Elegí el tipo de sospecha.'
  if (form.pathologyIds.length === 0) {
    errors.pathologyIds = 'Elegí al menos un diagnóstico presuntivo.'
  }
  if (!form.clinicalSummary.trim()) {
    errors.clinicalSummary = 'Completá el resumen de historia clínica.'
  }
  if (form.suspicionType === 'clinica' && form.symptoms.length === 0) {
    errors.symptoms = 'En una sospecha clínica cargá al menos un síntoma.'
  }
  return errors
}

/** Lo que se envía al backend: los nombres de los campos son los de la API. */
export function toPayload(form: PatientForm) {
  return {
    dni: form.dni.trim(),
    first_name: form.firstName.trim(),
    last_name: form.lastName.trim(),
    birth_date: form.birthDate,
    phone: form.phone.trim(),
    email: form.email.trim().toLowerCase(),
    suspicion_type: form.suspicionType,
    pathology_ids: form.pathologyIds,
    clinical_summary: form.clinicalSummary.trim(),
    symptoms: form.symptoms,
  }
}

/** Busca un paciente por DNI. Si no existe, el backend responde 404. */
export function findPatientByDni(dni: string) {
  const params = new URLSearchParams({ dni: dni.trim() })
  return api<Patient>(`/consulta_medica/patients?${params}`)
}

/** Hook de TanStack Query para buscar por DNI cuando el médico aprieta el botón (no al escribir). */
export function useFindPatient() {
  return useMutation({ mutationFn: findPatientByDni })
}

/** Hook de TanStack Query que envía el alta del paciente con los datos ya validados. */
export function useCreatePatient() {
  return useMutation({
    mutationFn: (form: PatientForm) =>
      api<CreatedPatient>('/consulta_medica/patients', {
        method: 'POST',
        ...json(toPayload(form)),
      }),
  })
}
