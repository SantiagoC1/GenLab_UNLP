import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { navigation } from '../../lib/mercadopago'
import { mockApi, renderApp, startTestSession } from '../../test-utils'

const PATH = '/paciente/pagar-con-mercadopago'
const ESTUDIOS = 'GET /presupuesto_pago/mis-estudios'
const CONDICIONES = 'GET /presupuesto_pago/mis-estudios/1/pago-mercadopago'
const CREAR = 'POST /presupuesto_pago/mis-estudios/1/pago-mercadopago'
const INIT_POINT = 'https://www.mercadopago.com.ar/checkout/v1/redirect?pref_id=PREF-1'

const CREADO = { id: 1, estado: 'Creado', cantidad_genes: 8, importe_usd: 590, cobertura: null }
const CONDICIONES_SIN_CUPON = {
  estudio_id: 1,
  importe_original_usd: 590,
  importe_usd: 590,
  cupon: null,
  moneda: 'ARS',
  importe: 590000,
  cuotas_maximas: 6,
}
const CHECKOUT = { ...CONDICIONES_SIN_CUPON, init_point: INIT_POINT, preference_id: 'PREF-1' }

afterEach(() => vi.restoreAllMocks())
beforeEach(() => {
  localStorage.clear()
  startTestSession('paciente')
})

describe('Pagar con Mercado Pago: antes de pagar', () => {
  it('muestra el importe, las cuotas y el medio de pago', async () => {
    mockApi({ [ESTUDIOS]: { body: [CREADO] }, [CONDICIONES]: { body: CONDICIONES_SIN_CUPON } })
    renderApp(PATH)

    expect(await screen.findByText('USD 590', { selector: 'strong' })).toBeInTheDocument()
    expect(screen.getByText(/Mercado Pago te cobra/)).toHaveTextContent('$ 590.000,00')
    expect(screen.getByText(/hasta 6 cuotas con tarjeta de crédito/)).toBeInTheDocument()
    expect(screen.getByText(/Elegís la cantidad al pagar en Mercado Pago/)).toBeInTheDocument()
    expect(screen.getByText(/tarjeta de crédito o de débito, o dinero en tu cuenta/)).toBeVisible()
    expect(screen.getByRole('button', { name: 'Pagar con Mercado Pago' })).toBeEnabled()
    expect(
      within(screen.getByRole('main')).getByRole('link', { name: 'Pagar el estudio' }),
    ).toHaveAttribute('href', '/paciente/pago')
  })

  it('muestra el importe con el cupón aplicado', async () => {
    mockApi({
      [ESTUDIOS]: { body: [CREADO] },
      [CONDICIONES]: {
        body: {
          ...CONDICIONES_SIN_CUPON,
          cupon: 'CUP-0001',
          importe_usd: 472,
          importe: 472000,
        },
      },
    })
    renderApp(PATH)

    expect(await screen.findByText('USD 472', { selector: 'strong' })).toBeInTheDocument()
    expect(screen.getByText('USD 590', { selector: 's' })).toBeInTheDocument()
    expect(screen.getByText('Cupón CUP-0001 aplicado.')).toBeInTheDocument()
    expect(screen.getByText(/Mercado Pago te cobra/)).toHaveTextContent('$ 472.000,00')
  })

  it('muestra que está cargando', async () => {
    mockApi({ [ESTUDIOS]: { body: [CREADO] }, [CONDICIONES]: { body: CONDICIONES_SIN_CUPON } })
    renderApp(PATH)

    expect(screen.getByText('Cargando tus estudios…')).toBeInTheDocument()
    await screen.findByText('USD 590', { selector: 'strong' })
    expect(screen.queryByText('Cargando tus estudios…')).not.toBeInTheDocument()
  })

  it('avisa cuando no hay estudios para pagar', async () => {
    mockApi({ [ESTUDIOS]: { body: [{ ...CREADO, estado: 'Pagado' }] } })
    renderApp(PATH)

    expect(await screen.findByText('No tenés estudios para pagar con Mercado Pago.')).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Pagar con Mercado Pago' })).not.toBeInTheDocument()
  })

  it('no ofrece pagar un estudio con la cobertura de una obra social en curso', async () => {
    mockApi({
      [ESTUDIOS]: {
        body: [
          { ...CREADO, cobertura: { obra_social: 'OSDE', porcentaje: 80, estado: 'Pendiente' } },
        ],
      },
    })
    renderApp(PATH)

    expect(await screen.findByText('No tenés estudios para pagar con Mercado Pago.')).toBeVisible()
  })

  it('muestra el error al cargar los estudios y deja reintentar', async () => {
    let pedidos = 0
    mockApi({
      [ESTUDIOS]: () => {
        pedidos += 1
        return pedidos === 1
          ? { status: 503, body: { detalle: 'El servicio no responde.' } }
          : { body: [CREADO] }
      },
      [CONDICIONES]: { body: CONDICIONES_SIN_CUPON },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    expect(await screen.findByRole('alert')).toHaveTextContent('El servicio no responde.')
    await user.click(screen.getByRole('button', { name: 'Reintentar' }))

    expect(await screen.findByText('USD 590', { selector: 'strong' })).toBeInTheDocument()
  })

  it('muestra el error del importe y no deja pagar', async () => {
    mockApi({
      [ESTUDIOS]: { body: [CREADO] },
      [CONDICIONES]: {
        status: 409,
        body: { detalle: 'El estudio ya está Pagado: no hay nada más para pagar.' },
      },
    })
    renderApp(PATH)

    expect(await screen.findByRole('alert')).toHaveTextContent('El estudio ya está Pagado')
    expect(screen.getByRole('button', { name: 'Pagar con Mercado Pago' })).toBeDisabled()
  })

  it('deja elegir el estudio cuando hay más de uno', async () => {
    const mock = mockApi({
      [ESTUDIOS]: { body: [CREADO, { ...CREADO, id: 2, importe_usd: 500 }] },
      [CONDICIONES]: { body: CONDICIONES_SIN_CUPON },
      'GET /presupuesto_pago/mis-estudios/2/pago-mercadopago': {
        body: { ...CONDICIONES_SIN_CUPON, estudio_id: 2, importe_usd: 500, importe: 500000 },
      },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await screen.findByText('USD 590', { selector: 'strong' })
    await user.selectOptions(screen.getByLabelText('Estudio'), '2')

    expect(await screen.findByText('USD 500', { selector: 'strong' })).toBeInTheDocument()
    expect(mock).toHaveBeenCalledWith(
      expect.stringContaining('/mis-estudios/2/pago-mercadopago'),
      expect.anything(),
    )
  })
})

describe('Pagar con Mercado Pago: ir a pagar', () => {
  it('crea el cobro y lleva al paciente al checkout de Mercado Pago', async () => {
    const go = vi.spyOn(navigation, 'go').mockImplementation(() => {})
    mockApi({
      [ESTUDIOS]: { body: [CREADO] },
      [CONDICIONES]: { body: CONDICIONES_SIN_CUPON },
      [CREAR]: { status: 201, body: CHECKOUT },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Pagar con Mercado Pago' }))

    await vi.waitFor(() => expect(go).toHaveBeenCalledWith(INIT_POINT))
    expect(go).toHaveBeenCalledTimes(1)
    expect(await screen.findByText('Te llevamos a Mercado Pago…')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Pagar con Mercado Pago' })).toBeDisabled()
  })

  it('deshabilita el botón mientras se crea el cobro y no lo crea dos veces', async () => {
    const go = vi.spyOn(navigation, 'go').mockImplementation(() => {})
    let terminar: (respuesta: Response) => void = () => {}
    let creaciones = 0
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const { pathname } = new URL(String(input), 'http://localhost')
        if (init?.method === 'POST' && pathname.endsWith('/pago-mercadopago')) {
          creaciones += 1
          return new Promise<Response>((resolver) => {
            terminar = resolver
          })
        }
        const cuerpo = pathname.endsWith('/pago-mercadopago') ? CONDICIONES_SIN_CUPON : [CREADO]
        return Promise.resolve(new Response(JSON.stringify(cuerpo)))
      }),
    )
    renderApp(PATH)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Pagar con Mercado Pago' }))

    const boton = screen.getByRole('button', { name: 'Pagar con Mercado Pago' })
    expect(boton).toBeDisabled()
    expect(boton).toHaveAttribute('aria-busy', 'true')
    await user.click(boton)
    expect(creaciones).toBe(1)

    terminar(new Response(JSON.stringify(CHECKOUT), { status: 201 }))
    await vi.waitFor(() => expect(go).toHaveBeenCalledWith(INIT_POINT))
    vi.unstubAllGlobals()
  })

  it('muestra el error cuando Mercado Pago no responde y deja volver a intentar', async () => {
    const go = vi.spyOn(navigation, 'go').mockImplementation(() => {})
    mockApi({
      [ESTUDIOS]: { body: [CREADO] },
      [CONDICIONES]: { body: CONDICIONES_SIN_CUPON },
      [CREAR]: {
        status: 503,
        body: { detalle: "El módulo externo 'mercadopago' no está disponible." },
      },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Pagar con Mercado Pago' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      "El módulo externo 'mercadopago' no está disponible.",
    )
    expect(go).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Pagar con Mercado Pago' })).toBeEnabled()
  })

  it('tiene su entrada en el menú del paciente', async () => {
    mockApi({ [ESTUDIOS]: { body: [] } })
    renderApp(PATH)

    const enlaces = await screen.findAllByRole('link', { name: 'Pagar con Mercado Pago' })
    expect(enlaces[0]).toHaveAttribute('href', '/paciente/pagar-con-mercadopago')
  })
})
