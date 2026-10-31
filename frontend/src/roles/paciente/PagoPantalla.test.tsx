import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { mockApi, renderApp, sentTo, startTestSession } from '../../test-utils'

const PATH = '/paciente/pago'
const ESTUDIOS = 'GET /presupuesto_pago/mis-estudios'
const PAGAR = 'POST /presupuesto_pago/mis-estudios/1/pago'
const CUPONES = 'GET /cupones/asignados'
const CUPON = 'POST /presupuesto_pago/mis-estudios/1/cupon'
const CUPON_PDF = 'POST /presupuesto_pago/mis-estudios/1/cupon-pdf'

const CREADO = { id: 1, estado: 'Creado', cantidad_genes: 8, importe_usd: 590, cobertura: null }

const CON_CUPON = {
  ...CREADO,
  cupon_aplicado: {
    codigo: 'CUP-0001',
    descuento: 20,
    importe_original_usd: 590,
    importe_con_descuento_usd: 472,
  },
}

afterEach(() => vi.unstubAllGlobals())
beforeEach(() => {
  localStorage.clear()
  startTestSession('paciente')
})

describe('Pagar el estudio', () => {
  it('informa el importe, paga con el método elegido y confirma', async () => {
    const mock = mockApi({
      [ESTUDIOS]: { body: [CREADO] },
      [CUPONES]: { body: [] },
      [PAGAR]: { status: 201, body: { estudio_id: 1, estado: 'Pagado', importe_usd: 590 } },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    expect(await screen.findByText('USD 590', { selector: 'strong' })).toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('Método de pago'), 'transferencia')
    await user.click(screen.getByRole('button', { name: 'Pagar USD 590' }))

    expect(await screen.findByRole('status')).toHaveTextContent('Pago registrado: USD 590')
    expect(sentTo(mock, PAGAR)).toEqual([{ metodo: 'transferencia' }])
  })

  it('no ofrece pagar un estudio con la cobertura de una obra social en curso', async () => {
    mockApi({
      [CUPONES]: { body: [] },
      [ESTUDIOS]: {
        body: [
          {
            ...CREADO,
            cobertura: { obra_social: 'OSDE', porcentaje: 80, estado: 'Pendiente' },
          },
        ],
      },
    })
    renderApp(PATH)
    expect(await screen.findByText('No tenés estudios para pagar.')).toBeInTheDocument()
  })

  it('muestra el error cuando el pago no se puede registrar', async () => {
    mockApi({
      [ESTUDIOS]: { body: [CREADO] },
      [CUPONES]: { body: [] },
      [PAGAR]: { status: 409, body: { detalle: 'El estudio ya está Pagado.' } },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Pagar USD 590' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('El estudio ya está Pagado.')
  })

  it('publica los cupones que el médico le asignó al paciente', async () => {
    mockApi({
      [ESTUDIOS]: { body: [CREADO] },
      [CUPONES]: {
        body: [
          {
            codigo: 'CUP-0007',
            descuento: 20,
            estado: 'Vigente',
            pdf_url: '/cupones/CUP-0007/pdf',
            qr: 'data:image/svg+xml;base64,PHN2Zy8+',
            medico: 'ana@example.com',
            paciente: 'lucia@example.com',
          },
        ],
      },
    })
    renderApp(PATH)

    expect(await screen.findByText('CUP-0007')).toBeInTheDocument()
    expect(screen.getByText('20% de descuento · Vigente')).toBeInTheDocument()
    expect(screen.getByAltText('QR del cupón CUP-0007')).toBeInTheDocument()
  })

  it('aplica un cupón por su código y muestra el nuevo importe', async () => {
    let estudio: object = CREADO
    const mock = mockApi({
      [ESTUDIOS]: () => ({ body: [estudio] }),
      [CUPONES]: { body: [] },
      [CUPON]: () => {
        estudio = CON_CUPON
        return { body: CON_CUPON.cupon_aplicado }
      },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText('Código del cupón'), 'CUP-0001')
    await user.click(screen.getByRole('button', { name: 'Aplicar cupón' }))

    expect(await screen.findByText('USD 472', { selector: 'strong' })).toBeInTheDocument()
    expect(screen.getByText('Cupón CUP-0001: 20% de descuento')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Pagar USD 472' })).toBeInTheDocument()
    expect(sentTo(mock, CUPON)).toEqual([{ codigo: 'CUP-0001' }])
  })

  it('adjunta el PDF del cupón', async () => {
    let estudio: object = CREADO
    const mock = mockApi({
      [ESTUDIOS]: () => ({ body: [estudio] }),
      [CUPONES]: { body: [] },
      [CUPON_PDF]: () => {
        estudio = CON_CUPON
        return { body: CON_CUPON.cupon_aplicado }
      },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    const archivo = new File(['%PDF-1.4'], 'cupon.pdf', { type: 'application/pdf' })
    await user.upload(await screen.findByLabelText('O adjuntá el PDF del cupón'), archivo)

    expect(await screen.findByText('USD 472', { selector: 'strong' })).toBeInTheDocument()
    const [, init] = mock.mock.calls.find(([url]) => String(url).endsWith('/cupon-pdf'))!
    expect(init?.headers).toMatchObject({ 'Content-Type': 'application/pdf' })
  })

  it('si el cupón no está Vigente muestra el motivo y mantiene el importe', async () => {
    mockApi({
      [ESTUDIOS]: { body: [CREADO] },
      [CUPONES]: { body: [] },
      [CUPON]: {
        status: 409,
        body: { detalle: 'El cupón CUP-0001 no se puede aplicar: su estado es Usado.' },
      },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText('Código del cupón'), 'CUP-0001')
    await user.click(screen.getByRole('button', { name: 'Aplicar cupón' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('su estado es Usado')
    expect(screen.getByText('USD 590', { selector: 'strong' })).toBeInTheDocument()
  })

  it('al pagar con cupón informa el uso del cupón', async () => {
    mockApi({
      [ESTUDIOS]: { body: [CON_CUPON] },
      [CUPONES]: { body: [] },
      [PAGAR]: {
        status: 201,
        body: { estudio_id: 1, estado: 'Pagado', importe_usd: 472, cupon: 'CUP-0001' },
      },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Pagar USD 472' }))
    expect(await screen.findByRole('status')).toHaveTextContent(
      'Pago registrado: USD 472. Se informó el uso del cupón CUP-0001.',
    )
  })

  it('permite usar uno de los cupones que le asignó el médico', async () => {
    const mock = mockApi({
      [ESTUDIOS]: { body: [CREADO] },
      [CUPONES]: {
        body: [
          {
            codigo: 'CUP-0001',
            descuento: 20,
            estado: 'Vigente',
            pdf_url: '/cupones/CUP-0001/pdf',
            qr: null,
            medico: 'ana@example.com',
            paciente: 'lucia@example.com',
          },
        ],
      },
      [CUPON]: { body: CON_CUPON.cupon_aplicado },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Usar este cupón' }))
    await vi.waitFor(() => expect(sentTo(mock, CUPON)).toEqual([{ codigo: 'CUP-0001' }]))
  })
})
