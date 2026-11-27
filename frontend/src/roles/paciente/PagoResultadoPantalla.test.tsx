import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { describirMetodo, describirRechazo, formatearMonto } from '../../lib/mercadopago'
import { mockApi, renderApp, sentTo, startTestSession } from '../../test-utils'

const VUELTA = '/paciente/pago-resultado'
const CONFIRMAR = 'POST /presupuesto_pago/pago-mercadopago/confirmar'

// What Mercado Pago puts in the address the patient comes back to.
const VOLVIENDO = `${VUELTA}?collection_id=1001&collection_status=approved&payment_id=1001&status=approved&external_reference=genlab-study-1&payment_type=credit_card&preference_id=PREF-1&site_id=MLA`

const APROBADO = {
  resultado: 'aprobado',
  estudio_id: 1,
  estado_estudio: 'Pagado',
  estado_mp: 'approved',
  detalle_mp: null,
  importe_original_usd: 590,
  importe_usd: 472,
  cupon: 'CUP-0001',
  metodo: 'mercadopago_credit_card',
  cuotas: 3,
  valor_cuota: 157333.33,
  moneda: 'ARS',
  mp_payment_id: '1001',
  pagado_en: '2026-11-26T20:00:00Z',
  paciente_avisado: true,
}
const SIN_ACREDITAR = {
  resultado: 'pendiente',
  estudio_id: 1,
  estado_estudio: 'Creado',
  estado_mp: 'in_process',
  detalle_mp: 'pending_contingency',
  importe_original_usd: null,
  importe_usd: null,
  cupon: null,
  metodo: null,
  cuotas: null,
  valor_cuota: null,
  moneda: null,
  mp_payment_id: '1001',
  pagado_en: null,
  paciente_avisado: false,
}

afterEach(() => vi.unstubAllGlobals())
beforeEach(() => {
  localStorage.clear()
  startTestSession('paciente')
})

describe('Resultado del pago: aprobado', () => {
  it('confirma el pago por su id y muestra el plan de cuotas', async () => {
    const mock = mockApi({ [CONFIRMAR]: { body: APROBADO } })
    renderApp(VOLVIENDO)

    expect(screen.getByText('Confirmando tu pago con Mercado Pago…')).toBeInTheDocument()
    // While it loads the status is the loading indicator: wait for the result.
    await vi.waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent(
        'Pago aprobado. Tu estudio 1 está Pagado y ya podés sacar tu turno de extracción.',
      ),
    )
    expect(sentTo(mock, CONFIRMAR)).toEqual([{ payment_id: '1001' }])

    const plan = within(screen.getByRole('region', { name: 'Tu plan de pago' }))
    expect(plan.getByText('USD 472 (con el cupón CUP-0001)')).toBeInTheDocument()
    expect(plan.getByText('Tarjeta de crédito')).toBeInTheDocument()
    expect(plan.getByText(/3 cuotas de \$\s157\.333,33/)).toBeInTheDocument()
    expect(plan.getByText('1001')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'sacar tu turno de extracción' })).toHaveAttribute(
      'href',
      '/paciente/turno',
    )
  })

  it('muestra un pago en una sola cuota', async () => {
    mockApi({ [CONFIRMAR]: { body: { ...APROBADO, cuotas: 1, cupon: null, valor_cuota: 590000 } } })
    renderApp(VOLVIENDO)

    expect(await screen.findByText('Pago en una sola cuota')).toBeVisible()
  })

  it('usa collection_id cuando no viene payment_id', async () => {
    const mock = mockApi({ [CONFIRMAR]: { body: APROBADO } })
    renderApp(`${VUELTA}?collection_id=777&status=approved`)

    await screen.findByText(/Pago aprobado/)
    expect(sentTo(mock, CONFIRMAR)).toEqual([{ payment_id: '777' }])
  })

  it('confirma una sola vez aunque la pantalla se dibuje de nuevo', async () => {
    const mock = mockApi({ [CONFIRMAR]: { body: APROBADO } })
    renderApp(VOLVIENDO)

    await screen.findByText(/Pago aprobado/)
    expect(sentTo(mock, CONFIRMAR)).toHaveLength(1)
  })
})

describe('Resultado del pago: pendiente', () => {
  it('explica que todavía no se acreditó y deja volver a consultar', async () => {
    let consultas = 0
    const mock = mockApi({
      [CONFIRMAR]: () => {
        consultas += 1
        return { body: consultas === 1 ? SIN_ACREDITAR : APROBADO }
      },
    })
    renderApp(VOLVIENDO)
    const user = userEvent.setup()

    await screen.findByText(/Tu pago está pendiente de acreditación/)
    expect(screen.getByRole('status')).toHaveTextContent('Todavía no se registró ningún pago.')
    expect(screen.queryByRole('region', { name: 'Tu plan de pago' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Volver a consultar' }))

    expect(await screen.findByText(/Pago aprobado/)).toBeVisible()
    expect(sentTo(mock, CONFIRMAR)).toHaveLength(2)
  })

  it('lleva a mis estudios', async () => {
    mockApi({
      [CONFIRMAR]: { body: SIN_ACREDITAR },
      'GET /presupuesto_pago/mis-estudios': { body: [] },
    })
    renderApp(VOLVIENDO)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Ir a mis estudios' }))

    expect(await screen.findByRole('heading', { name: /estudios/i })).toBeVisible()
  })
})

describe('Resultado del pago: rechazado', () => {
  const RECHAZADO = {
    ...SIN_ACREDITAR,
    resultado: 'rechazado',
    estado_mp: 'rejected',
    detalle_mp: 'cc_rejected_insufficient_amount',
  }

  it('dice por qué y ofrece reintentar el pago', async () => {
    mockApi({
      [CONFIRMAR]: { body: RECHAZADO },
      'GET /presupuesto_pago/mis-estudios': { body: [] },
    })
    renderApp(VOLVIENDO)
    const user = userEvent.setup()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'El pago no se realizó. La tarjeta no tiene fondos suficientes. No se registró ningún pago y tu estudio sigue sin pagar.',
    )
    await user.click(screen.getByRole('button', { name: 'Reintentar el pago' }))

    expect(await screen.findByRole('heading', { name: 'Pagar con Mercado Pago' })).toBeVisible()
  })

  it('usa un texto general cuando no se sabe el motivo', async () => {
    mockApi({ [CONFIRMAR]: { body: { ...RECHAZADO, detalle_mp: 'otro_motivo' } } })
    renderApp(VOLVIENDO)

    expect(await screen.findByRole('alert')).toHaveTextContent('Mercado Pago no aprobó el pago.')
  })
})

describe('Resultado del pago: sin pago y con errores', () => {
  it.each([`${VUELTA}`, `${VUELTA}?status=null&payment_id=null&collection_id=null`])(
    'si no hay pago (%s) no consulta nada y ofrece volver a intentar',
    async (direccion) => {
      const mock = mockApi({})
      renderApp(direccion)
      const user = userEvent.setup()

      expect(await screen.findByRole('status')).toHaveTextContent('No se realizó el pago')
      expect(screen.getByRole('status')).toHaveTextContent('No se te cobró nada')
      expect(sentTo(mock, CONFIRMAR)).toEqual([])
      await user.click(screen.getByRole('button', { name: 'Volver a intentar el pago' }))
      expect(await screen.findByRole('heading', { name: 'Pagar con Mercado Pago' })).toBeVisible()
    },
  )

  it('muestra el error del servidor y deja reintentar', async () => {
    let consultas = 0
    mockApi({
      [CONFIRMAR]: () => {
        consultas += 1
        return consultas === 1
          ? {
              status: 409,
              body: {
                detalle:
                  'El monto del pago no coincide con el importe del estudio: no se registró el pago.',
              },
            }
          : { body: APROBADO }
      },
    })
    renderApp(VOLVIENDO)
    const user = userEvent.setup()

    expect(await screen.findByRole('alert')).toHaveTextContent('El monto del pago no coincide')
    await user.click(screen.getByRole('button', { name: 'Reintentar' }))

    expect(await screen.findByText(/Pago aprobado/)).toBeVisible()
  })

  it('muestra el error cuando Mercado Pago no responde', async () => {
    mockApi({
      [CONFIRMAR]: {
        status: 503,
        body: { detalle: "El módulo externo 'mercadopago' no está disponible." },
      },
    })
    renderApp(VOLVIENDO)

    expect(await screen.findByRole('alert')).toHaveTextContent('no está disponible')
  })

  it('no aparece en el menú, pero tiene su dirección', async () => {
    mockApi({ [CONFIRMAR]: { body: APROBADO } })
    renderApp(VOLVIENDO)

    await screen.findByText(/Pago aprobado/)
    expect(
      screen.queryByRole('link', { name: 'Resultado del pago con Mercado Pago' }),
    ).not.toBeInTheDocument()
  })
})

describe('Textos del pago con Mercado Pago', () => {
  it('nombra los medios de pago', () => {
    expect(describirMetodo('mercadopago_credit_card')).toBe('Tarjeta de crédito')
    expect(describirMetodo('mercadopago_debit_card')).toBe('Tarjeta de débito')
    expect(describirMetodo('mercadopago_account_money')).toBe('Dinero en cuenta de Mercado Pago')
    expect(describirMetodo('mercadopago_otro')).toBe('Mercado Pago')
    expect(describirMetodo(null)).toBe('Mercado Pago')
  })

  it('explica el rechazo, o dice algo general', () => {
    expect(describirRechazo('cc_rejected_call_for_authorize')).toBe(
      'Tenés que autorizar el pago con tu banco.',
    )
    expect(describirRechazo('algo_nuevo')).toBe('Mercado Pago no aprobó el pago.')
    expect(describirRechazo(null)).toBe('Mercado Pago no aprobó el pago.')
  })

  it('da formato al monto en su moneda', () => {
    expect(formatearMonto(1000, 'ARS')).toMatch(/1\.000,00/)
    expect(formatearMonto(500, 'USD')).toMatch(/500,00/)
  })
})
