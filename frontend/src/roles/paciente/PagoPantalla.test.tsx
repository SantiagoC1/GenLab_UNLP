import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { mockApi, renderApp, sentTo, startTestSession } from '../../test-utils'

const PATH = '/paciente/pago'
const ESTUDIOS = 'GET /presupuesto_pago/mis-estudios'
const PAGAR = 'POST /presupuesto_pago/mis-estudios/1/pago'

const CREADO = { id: 1, estado: 'Creado', cantidad_genes: 8, importe_usd: 590, cobertura: null }

afterEach(() => vi.unstubAllGlobals())
beforeEach(() => {
  localStorage.clear()
  startTestSession('paciente')
})

describe('Pagar el estudio', () => {
  it('informa el importe, paga con el método elegido y confirma', async () => {
    const mock = mockApi({
      [ESTUDIOS]: { body: [CREADO] },
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
      [PAGAR]: { status: 409, body: { detalle: 'El estudio ya está Pagado.' } },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Pagar USD 590' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('El estudio ya está Pagado.')
  })
})
