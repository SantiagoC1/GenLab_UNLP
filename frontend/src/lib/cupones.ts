// REUTILIZABLE: lo que comparten las pantallas de cupones (gerente médico, médico tratante, paciente).

export interface Cupon {
  codigo: string
  descuento: number
  estado: string
  pdf_url: string
  qr: string | null
  medico: string | null
  paciente: string | null
}

export const CUPONES_KEY = ['cupones', 'lista']
