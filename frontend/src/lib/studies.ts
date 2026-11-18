import { useMutation, useQuery } from '@tanstack/react-query'
import { api, json } from './api'
import { useDebouncedValue } from './useDebouncedValue'

export type GeneOrigin = 'patologia' | 'hallazgo_secundario' | 'manual'

export interface StudyGene {
  gene: string
  origin: GeneOrigin
}

/** El estudio recién creado, tal como lo devuelve el backend. */
export interface CreatedStudy {
  id: number
  state: string
  pompe_urgent: boolean
  secondary_findings: boolean
  genes: StudyGene[]
}

export interface StudyRequest {
  patient_id: string
  pathology_ids: number[]
  secondary_findings: boolean
  manual_genes: string[]
}

export const ORIGIN_LABELS: Record<GeneOrigin, string> = {
  patologia: 'De la patología',
  hallazgo_secundario: 'Hallazgo secundario',
  manual: 'Agregado por el médico',
}

/** Deja el gen como lo guarda el backend: sin espacios y en mayúsculas. */
export function normalizeGene(text: string): string {
  return text.trim().toUpperCase()
}

/** Pide los genes de las patologías elegidas. No reintenta, para que un 503 se vea enseguida. */
export function useStudyGenes(pathologyIds: number[], secondaryFindings: boolean) {
  const params = new URLSearchParams({
    pathology_ids: pathologyIds.join(','),
    secondary_findings: String(secondaryFindings),
  })
  return useQuery({
    queryKey: ['study-genes', pathologyIds, secondaryFindings],
    queryFn: () => api<{ genes: StudyGene[] }>(`/consulta_medica/studies/genes?${params}`),
    enabled: pathologyIds.length > 0,
    retry: false,
  })
}

/** Sugiere genes de Apigen que empiezan con lo que escribe el médico, para agregar uno a mano. */
export function useGeneSuggestions(text: string) {
  const prefix = useDebouncedValue(normalizeGene(text))
  const query = useQuery({
    queryKey: ['gene-search', prefix],
    queryFn: () =>
      api<{ genes: string[] }>(
        `/consulta_medica/studies/gene-search?${new URLSearchParams({ q: prefix })}`,
      ),
    enabled: /^[A-Z0-9-]{1,20}$/.test(prefix),
    retry: false,
  })
  return query.data?.genes ?? []
}

/** Hook de TanStack Query que solicita el estudio. */
export function useCreateStudy() {
  return useMutation({
    mutationFn: (request: StudyRequest) =>
      api<CreatedStudy>('/consulta_medica/studies', { method: 'POST', ...json(request) }),
  })
}
