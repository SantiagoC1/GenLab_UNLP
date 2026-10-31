// REUTILIZABLE: lo que comparten las pantallas de turnos del paciente.

export interface Laboratorio {
  id: number
  nombre: string
  direccion: string
  provincia: string
  latitud: number
  longitud: number
  proximo_turno: string | null
}

export interface Turno {
  id: number
  estudio_id: number
  laboratorio: Laboratorio
  inicio: string
  estado: string
  recordatorio_para: string | null
  puede_cancelar: boolean
  orden_extraccion_url: string | null
  consentimiento_url: string | null
}

export const MIS_TURNOS_KEY = ['turnos', 'mis-turnos']
export const HABILITADOS_KEY = ['turnos', 'habilitados']

/** Con este número de inasistencias se le avisa al paciente (no hay bloqueo todavía). */
export const LIMITE_INASISTENCIAS = 5

export interface Habilitado {
  estudio_id: number
  estado: string
  motivo: 'pagado' | 'autorizado' | 'nueva_reserva'
  inasistencias: number
}

const ZONA = 'America/Argentina/Buenos_Aires'

export function formatearHora(iso: string): string {
  return new Date(iso).toLocaleTimeString('es-AR', {
    timeZone: ZONA,
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

export function formatearFecha(iso: string): string {
  return new Date(iso).toLocaleDateString('es-AR', {
    timeZone: ZONA,
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

export function formatearFechaHora(iso: string): string {
  return `${formatearFecha(iso)}, ${formatearHora(iso)}`
}

/** Hoy en Argentina, como AAAA-MM-DD (lo que espera un campo de fecha). */
export function hoyEnArgentina(): string {
  return new Date().toLocaleDateString('en-CA', { timeZone: ZONA })
}

export function sumarDias(dia: string, dias: number): string {
  const fecha = new Date(`${dia}T12:00:00Z`)
  fecha.setUTCDate(fecha.getUTCDate() + dias)
  return fecha.toISOString().slice(0, 10)
}

export const HORIZONTE_DIAS = 60
