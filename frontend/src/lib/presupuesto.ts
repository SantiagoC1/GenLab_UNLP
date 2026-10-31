import { useQuery } from '@tanstack/react-query'
import { api } from './api'

// REUTILIZABLE: las pantallas del paciente (cobertura, pago, demanda) leen estos estudios.

export interface Cobertura {
  obra_social: string
  porcentaje: number
  estado: 'Pendiente' | 'Autorizado' | 'Rechazado'
  motivo_rechazo: string | null
  demanda_enviada?: boolean
  demanda_nombre?: string | null
}

export interface CuponAplicado {
  codigo: string
  descuento: number
  importe_original_usd: number
  importe_con_descuento_usd: number
}

export interface EstudioDelPaciente {
  id: number
  estado: string
  cantidad_genes: number
  importe_usd: number | null
  cobertura: Cobertura | null
  cupon_aplicado?: CuponAplicado | null
}

export const MIS_ESTUDIOS_KEY = ['presupuesto', 'mis-estudios']

export function useMisEstudios() {
  return useQuery({
    queryKey: MIS_ESTUDIOS_KEY,
    queryFn: () => api<EstudioDelPaciente[]>('/presupuesto_pago/mis-estudios'),
  })
}
