import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { mockApi, renderApp, sentTo, startTestSession } from '../../test-utils'

const PATH = '/gerente_medico/generar-cupones'
const LISTA = 'GET /cupones'
const GENERAR = 'POST /cupones/generar'

const CUPON = {
  codigo: 'CUP-0001',
  descuento: 20,
  estado: 'Vigente',
  pdf_url: '/cupones/CUP-0001/pdf',
  qr: 'data:image/svg+xml;base64,PHN2Zy8+',
  medico: null,
  paciente: null,
}

afterEach(() => vi.unstubAllGlobals())
beforeEach(() => {
  localStorage.clear()
  startTestSession('gerente_medico')
})

async function completar(user: ReturnType<typeof userEvent.setup>) {
  await user.type(await screen.findByLabelText('Descuento (%)'), '20')
  await user.type(screen.getByLabelText('Cantidad de cupones'), '3')
}

describe('Generar cupones de descuento', () => {
  it('pide los cupones y los muestra Vigentes con su QR', async () => {
    let generados: unknown[] = []
    const mock = mockApi({
      [LISTA]: () => ({ body: generados }),
      [GENERAR]: () => {
        generados = [CUPON]
        return { status: 201, body: generados }
      },
    })
    renderApp(PATH)
    const user = userEvent.setup()
    expect(await screen.findByText('Todavía no hay cupones generados.')).toBeInTheDocument()

    await completar(user)
    await user.click(screen.getByRole('button', { name: 'Generar cupones' }))

    expect(await screen.findByRole('status')).toHaveTextContent('Se generaron 1 cupones Vigentes')
    expect(await screen.findByText('CUP-0001')).toBeInTheDocument()
    expect(screen.getByText('20% · Vigente')).toBeInTheDocument()
    expect(screen.getByAltText('QR del cupón CUP-0001')).toBeInTheDocument()
    expect(sentTo(mock, GENERAR)).toEqual([{ descuento: 20, cantidad: 3 }])
  })

  it('informa el error y no muestra cupones nuevos si el módulo los rechaza', async () => {
    mockApi({
      [LISTA]: { body: [] },
      [GENERAR]: {
        status: 502,
        body: { detalle: 'El módulo de cupones rechazó la solicitud: sin cupos.' },
      },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await completar(user)
    await user.click(screen.getByRole('button', { name: 'Generar cupones' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('rechazó la solicitud')
    expect(screen.getByText('Todavía no hay cupones generados.')).toBeInTheDocument()
  })

  it('no deja generar sin descuento o con un descuento fuera de rango', async () => {
    mockApi({ [LISTA]: { body: [] } })
    renderApp(PATH)
    const user = userEvent.setup()

    const boton = await screen.findByRole('button', { name: 'Generar cupones' })
    expect(boton).toBeDisabled()
    await user.type(screen.getByLabelText('Descuento (%)'), '150')
    await user.type(screen.getByLabelText('Cantidad de cupones'), '2')
    expect(boton).toBeDisabled()
  })
})
