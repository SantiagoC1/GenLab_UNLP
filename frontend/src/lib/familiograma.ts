import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, json } from './api'
import { isValidDni, type Sex } from './patients'
import type { Symptom } from './symptoms'
import type { Errors } from './validation'

export const MAX_RELATIVES = 30
export const MAX_AGE = 120
export const MAX_NAME_LENGTH = 100

export interface Kinship {
  id: number
  name: string
}

export interface RelativePathology {
  id: number
  code: string
  name: string
}

/** Un familiar tal como lo devuelve el backend. */
export interface Relative {
  kinship_id: number
  first_name: string
  last_name: string
  dni: string | null
  linked_patient_id: string | null
  sex: Sex
  age: number | null
  deceased: boolean
  symptoms: Symptom[]
  pathologies: RelativePathology[]
}

/** Un familiar tal como se escribe en pantalla. `key` distingue las filas del formulario. */
export interface RelativeForm {
  key: number
  kinshipId: string
  firstName: string
  lastName: string
  dni: string
  sex: Sex | ''
  age: string
  deceased: boolean
  symptoms: Symptom[]
  pathologyIds: number[]
}

export interface FamilyTree {
  warnings: string[]
  svg_base64: string
}

/** Un familiar vacío para que el médico lo complete. */
export function emptyRelativeForm(key: number): RelativeForm {
  return {
    key,
    kinshipId: '',
    firstName: '',
    lastName: '',
    dni: '',
    sex: '',
    age: '',
    deceased: false,
    symptoms: [],
    pathologyIds: [],
  }
}

/** Pasa un familiar guardado al formulario, para poder corregirlo. */
export function relativeToForm(relative: Relative, key: number): RelativeForm {
  return {
    key,
    kinshipId: String(relative.kinship_id),
    firstName: relative.first_name,
    lastName: relative.last_name,
    dni: relative.dni ?? '',
    sex: relative.sex,
    age: relative.age === null ? '' : String(relative.age),
    deceased: relative.deceased,
    symptoms: relative.symptoms,
    pathologyIds: relative.pathologies.map((pathology) => pathology.id),
  }
}

/**
 * Valida un familiar antes de enviarlo, para avisar campo por campo. El backend repite las reglas
 * y es el que manda. La edad y el DNI pueden quedar vacíos.
 */
export function validateRelative(form: RelativeForm): Errors {
  const errors: Errors = {}
  if (!form.kinshipId) errors.kinshipId = 'Elegí el parentesco.'
  if (!form.firstName.trim()) errors.firstName = 'Completá el nombre.'
  if (!form.lastName.trim()) errors.lastName = 'Completá el apellido.'
  if (form.dni.trim() !== '' && !isValidDni(form.dni)) {
    errors.dni = 'El DNI tiene que tener 7 u 8 dígitos.'
  }
  if (!form.sex) errors.sex = 'Elegí el sexo.'
  if (form.age.trim() !== '') {
    const age = Number(form.age)
    if (Number.isNaN(age) || age < 0 || age > MAX_AGE) {
      errors.age = `La edad tiene que estar entre 0 y ${MAX_AGE} años.`
    }
  }
  return errors
}

/** Los errores de cada familiar con problemas, por la `key` de su fila. */
export function validateRelatives(forms: RelativeForm[]): Record<number, Errors> {
  const found: Record<number, Errors> = {}
  for (const form of forms) {
    const errors = validateRelative(form)
    if (Object.keys(errors).length > 0) found[form.key] = errors
  }
  return found
}

/** Lo que se envía al backend: los nombres de los campos son los de la API. */
export function toPayload(forms: RelativeForm[]) {
  return {
    relatives: forms.map((form) => ({
      kinship_id: Number(form.kinshipId),
      first_name: form.firstName.trim(),
      last_name: form.lastName.trim(),
      dni: form.dni.trim() === '' ? null : form.dni.trim(),
      sex: form.sex,
      age: form.age.trim() === '' ? null : Number(form.age),
      deceased: form.deceased,
      symptoms: form.symptoms,
      pathology_ids: form.pathologyIds,
    })),
  }
}

/** Pide los parentescos del módulo de familiograma, sin el del paciente. */
export function useKinships() {
  return useQuery({
    queryKey: ['kinships'],
    queryFn: () => api<Kinship[]>('/familiograma/kinships'),
    retry: false,
  })
}

/** Pide los familiares guardados del paciente. */
export function useRelatives(patientId: string | undefined) {
  return useQuery({
    queryKey: ['relatives', patientId],
    queryFn: () => api<Relative[]>(`/familiograma/patients/${patientId}/relatives`),
    enabled: patientId !== undefined,
  })
}

/** Guarda la lista completa de familiares y deja la respuesta en el caché. */
export function useSaveRelatives(patientId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (forms: RelativeForm[]) =>
      api<Relative[]>(`/familiograma/patients/${patientId}/relatives`, {
        method: 'PUT',
        ...json(toPayload(forms)),
      }),
    onSuccess: (saved) => queryClient.setQueryData(['relatives', patientId], saved),
  })
}

/** Genera el familiograma con los familiares guardados. */
export function useFamilyTree(patientId: string) {
  return useMutation({
    mutationFn: () => api<FamilyTree>(`/familiograma/patients/${patientId}/family-tree`),
  })
}
