import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, json } from './api'

export type MotivoRemuestreo = 'mala_calidad_de_muestra' | 'adn_desnaturalizado'

/** Los dos motivos por los que el administrativo pide un remuestreo. */
export const MOTIVOS_REMUESTREO: { value: MotivoRemuestreo; label: string }[] = [
  { value: 'mala_calidad_de_muestra', label: 'La muestra llegó con mala calidad' },
  { value: 'adn_desnaturalizado', label: 'ADN insuficiente o desnaturalizado' },
]

/** El largo del detalle que acepta el backend. */
export const DETALLE_MINIMO = 3
export const DETALLE_MAXIMO = 300

export interface RemuestreoPendiente {
  remuestreo_id: number
  motivo: string
  detalle: string
  pedido_en: string
}

/** Un estudio sobre el que se puede pedir un remuestreo. */
export interface EstudioRemuestreable {
  estudio_id: number
  paciente: string
  dni: string
  estado: string
  remuestreo_pendiente: RemuestreoPendiente | null
}

export interface RemuestreoPedido {
  remuestreo_id: number
  estudio_id: number
  estado: string
  motivo: string
  detalle: string
  medico_avisado: boolean
  paciente_avisado: boolean
}

export interface PedidoDeRemuestreo {
  estudioId: number
  motivo: MotivoRemuestreo
  detalle: string
}

const REMUESTREABLES_KEY = ['turnos', 'remuestreables']

/** Los estudios En viaje a Corea o En el área de bioinformática. */
export function useEstudiosRemuestreables() {
  return useQuery({
    queryKey: REMUESTREABLES_KEY,
    queryFn: () => api<EstudioRemuestreable[]>('/turnos/estudios/remuestreables'),
  })
}

/** Pide el remuestreo. Después, con o sin error, la lista se vuelve a pedir: el estado cambió. */
export function usePedirRemuestreo() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ estudioId, motivo, detalle }: PedidoDeRemuestreo) =>
      api<RemuestreoPedido>(`/turnos/estudios/${estudioId}/remuestreo-administrativo`, {
        method: 'POST',
        ...json({ motivo, detalle: detalle.trim() }),
      }),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['turnos'] }),
  })
}

/** A quién se le avisó, para el mensaje de éxito. */
export function describirAvisos(pedido: RemuestreoPedido): string {
  if (pedido.medico_avisado && pedido.paciente_avisado) {
    return 'Se avisó al médico tratante y al paciente.'
  }
  if (pedido.paciente_avisado)
    return 'Se avisó al paciente, pero no se pudo avisar al médico tratante.'
  if (pedido.medico_avisado)
    return 'Se avisó al médico tratante, pero no se pudo avisar al paciente.'
  return 'No se pudo avisar ni al médico tratante ni al paciente.'
}
