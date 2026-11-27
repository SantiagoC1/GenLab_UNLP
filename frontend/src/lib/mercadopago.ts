import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, json } from './api'
import { MIS_ESTUDIOS_KEY } from './presupuesto'

// Pago con Mercado Pago (Checkout Pro). Las cuotas las elige y las maneja Mercado Pago: la
// plataforma recibe un único pago aprobado y guarda el plan que eligió el paciente.

/** Lo que se cobraría por Mercado Pago, antes de ir a pagar. */
export interface CondicionesDePago {
  estudio_id: number
  importe_original_usd: number
  importe_usd: number
  cupon: string | null
  /** Lo que cobra Mercado Pago, en su moneda (el presupuesto está en USD). */
  moneda: string
  importe: number
  cuotas_maximas: number
}

export interface Checkout extends CondicionesDePago {
  init_point: string
  preference_id: string
}

export type ResultadoDelPago = 'aprobado' | 'pendiente' | 'rechazado'

export interface ConfirmacionDePago {
  resultado: ResultadoDelPago
  estudio_id: number
  estado_estudio: string
  estado_mp: string
  detalle_mp: string | null
  importe_original_usd: number | null
  importe_usd: number | null
  cupon: string | null
  metodo: string | null
  cuotas: number | null
  valor_cuota: number | null
  moneda: string | null
  mp_payment_id: string | null
  pagado_en: string | null
  paciente_avisado: boolean
}

/** Ir a otra dirección. Está aparte para poder reemplazarlo en los tests. */
export const navigation = {
  go: (url: string) => window.location.assign(url),
}

export function useCondicionesDePago(estudioId: number | undefined) {
  return useQuery({
    queryKey: ['mercadopago', 'condiciones', estudioId],
    queryFn: () =>
      api<CondicionesDePago>(`/presupuesto_pago/mis-estudios/${estudioId}/pago-mercadopago`),
    enabled: estudioId !== undefined,
    retry: false,
  })
}

/** Crea el cobro y manda al paciente al checkout de Mercado Pago. */
export function useIrAPagarConMercadoPago() {
  return useMutation({
    mutationFn: (estudioId: number) =>
      api<Checkout>(`/presupuesto_pago/mis-estudios/${estudioId}/pago-mercadopago`, {
        method: 'POST',
      }),
    onSuccess: (checkout) => navigation.go(checkout.init_point),
  })
}

/**
 * Al volver de Mercado Pago: confirma el pago por su id. Confirmar dos veces el mismo pago
 * devuelve el mismo resultado, así que recargar la pantalla no repite nada.
 */
export function useConfirmarPago(paymentId: string | null) {
  const queryClient = useQueryClient()
  return useQuery({
    queryKey: ['mercadopago', 'confirmacion', paymentId],
    queryFn: async () => {
      const confirmacion = await api<ConfirmacionDePago>(
        '/presupuesto_pago/pago-mercadopago/confirmar',
        { method: 'POST', ...json({ payment_id: paymentId }) },
      )
      // The study may be Pagado now, and the coupon used.
      void queryClient.invalidateQueries({ queryKey: MIS_ESTUDIOS_KEY })
      void queryClient.invalidateQueries({ queryKey: ['cupones', 'asignados'] })
      return confirmacion
    },
    enabled: paymentId !== null,
    retry: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    staleTime: Infinity,
  })
}

/** El monto en su moneda: "$ 1.000,00" en pesos, "US$ 500,00" en dólares. */
export function formatearMonto(monto: number, moneda: string): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: moneda }).format(monto)
}

const METODOS: Record<string, string> = {
  mercadopago_credit_card: 'Tarjeta de crédito',
  mercadopago_debit_card: 'Tarjeta de débito',
  mercadopago_account_money: 'Dinero en cuenta de Mercado Pago',
}

/** El medio con el que se pagó, para el paciente. */
export function describirMetodo(metodo: string | null): string {
  return (metodo && METODOS[metodo]) || 'Mercado Pago'
}

const MOTIVOS_DE_RECHAZO: Record<string, string> = {
  cc_rejected_insufficient_amount: 'La tarjeta no tiene fondos suficientes.',
  cc_rejected_bad_filled_card_number: 'El número de la tarjeta está mal cargado.',
  cc_rejected_bad_filled_date: 'La fecha de vencimiento está mal cargada.',
  cc_rejected_bad_filled_security_code: 'El código de seguridad está mal cargado.',
  cc_rejected_call_for_authorize: 'Tenés que autorizar el pago con tu banco.',
  cc_rejected_card_disabled: 'La tarjeta está inactiva.',
  cc_rejected_blacklist: 'No pudimos procesar la tarjeta.',
  cc_rejected_max_attempts: 'Llegaste al límite de intentos con esa tarjeta.',
}

/** Por qué Mercado Pago no aprobó el pago, si se sabe. */
export function describirRechazo(detalle: string | null): string {
  return (detalle && MOTIVOS_DE_RECHAZO[detalle]) || 'Mercado Pago no aprobó el pago.'
}
