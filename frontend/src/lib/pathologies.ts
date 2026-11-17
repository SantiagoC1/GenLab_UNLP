import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, json } from './api'
import type { Symptom } from './symptoms'

export interface Pathology {
  id: number
  name: string
  cardinal: Symptom | null
  secondary: Symptom[]
}

export interface PathologySymptoms {
  cardinal: Symptom
  secondary: Symptom[]
}

// Supuesto S8: la regla de correspondencia pide el cardinal o dos secundarios
export const MIN_SECONDARY_SYMPTOMS = 2

export type CdssStrategy =
  'sintomas_coincidentes' | 'sintomas_cardinales_coincidentes' | 'menor_diferencia'

export const CDSS_STRATEGIES: { value: CdssStrategy; label: string; description: string }[] = [
  {
    value: 'sintomas_coincidentes',
    label: 'Más síntomas coincidentes',
    description: 'Elige la patología que comparte más síntomas con el paciente.',
  },
  {
    value: 'sintomas_cardinales_coincidentes',
    label: 'Más síntomas cardinales coincidentes',
    description: 'Elige la patología cuyo síntoma cardinal coincide con los del paciente.',
  },
  {
    value: 'menor_diferencia',
    label: 'Menor diferencia',
    description: 'Elige la patología cuyos síntomas menos se diferencian de los del paciente.',
  },
]

const PATHOLOGIES_KEY = ['pathologies']
const STRATEGY_KEY = ['cdss-strategy']

export function usePathologies() {
  return useQuery({
    queryKey: PATHOLOGIES_KEY,
    queryFn: () => api<Pathology[]>('/config_medica/pathologies'),
  })
}

export function useCreatePathology() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: PathologySymptoms & { name: string }) =>
      api<Pathology>('/config_medica/pathologies', { method: 'POST', ...json(data) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PATHOLOGIES_KEY }),
  })
}

export function useReplacePathologySymptoms(pathologyId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: PathologySymptoms) =>
      api<Pathology>(`/config_medica/pathologies/${pathologyId}/symptoms`, {
        method: 'PUT',
        ...json(data),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PATHOLOGIES_KEY }),
  })
}

export function useCdssStrategy() {
  return useQuery({
    queryKey: STRATEGY_KEY,
    queryFn: () => api<{ strategy: CdssStrategy }>('/config_medica/cdss-strategy'),
  })
}

export function useSaveCdssStrategy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (strategy: CdssStrategy) =>
      api<{ strategy: CdssStrategy }>('/config_medica/cdss-strategy', {
        method: 'PUT',
        ...json({ strategy }),
      }),
    // Se guarda la respuesta en la caché: así el radio no vuelve un instante al valor anterior
    onSuccess: (saved) => queryClient.setQueryData(STRATEGY_KEY, saved),
  })
}
