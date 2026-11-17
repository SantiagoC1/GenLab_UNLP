import { api } from './api'

export interface Symptom {
  code: string
  term: string
}

export interface SymptomPage {
  items: Symptom[]
  page: number
  has_more: boolean
}

// M3-RF1: el buscador consulta SNOMED desde 3 letras
export const MIN_SEARCH_LENGTH = 3

export function searchSymptoms(text: string, page: number, signal?: AbortSignal) {
  const params = new URLSearchParams({ q: text, page: String(page) })
  return api<SymptomPage>(`/consulta_medica/symptoms?${params}`, { signal })
}
