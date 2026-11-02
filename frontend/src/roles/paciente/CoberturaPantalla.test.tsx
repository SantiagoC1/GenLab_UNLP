import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { mockApi, renderApp, sentTo, startTestSession } from '../../test-utils'

const PATH = '/paciente/cobertura'
const ESTUDIOS = 'GET /presupuesto_pago/mis-estudios'
const OBRAS = 'GET /presupuesto_pago/obras-sociales'
const ELEGIR = 'POST /presupuesto_pago/mis-estudios/1/cobertura'

const ESTUDIO = {
  id: 1,
  estado: 'Creado',
  cantidad_genes: 3,
  importe_usd: 500,
  cobertura: null,
}
const LISTA = [
  { nombre: 'OSDE', cobertura: 80 },
  { nombre: 'Swiss Medical', cobertura: 60 },
]

afterEach(() => vi.unstubAllGlobals())
beforeEach(() => {
  localStorage.clear()
  startTestSession('paciente')
})

describe('Elegir la cobertura por obra social', () => {
  it('muestra el porcentaje de la obra social y deja el estudio a la espera', async () => {
    const mock = mockApi({
      [ESTUDIOS]: { body: [ESTUDIO] },
      [OBRAS]: { body: LISTA },
      [ELEGIR]: { status: 201, body: ESTUDIO },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    expect(await screen.findByText('USD 500')).toBeInTheDocument()
    await user.selectOptions(await screen.findByLabelText('Obra social'), 'OSDE')
    expect(screen.getByText('80%')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Dejar a la espera de la autorización' }))
    expect(await screen.findByRole('status')).toHaveTextContent('a la espera de la autorización')
    expect(sentTo(mock, ELEGIR)).toEqual([{ obra_social: 'OSDE' }])
  })

  it('si la obra social no figura, ofrece solo el pago particular', async () => {
    mockApi({ [ESTUDIOS]: { body: [ESTUDIO] }, [OBRAS]: { body: LISTA } })
    renderApp(PATH)
    const user = userEvent.setup()

    await user.selectOptions(
      await screen.findByLabelText('Obra social'),
      'Mi obra social no figura en la lista',
    )
    expect(screen.getByText(/solo podés pagar de forma particular/)).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Dejar a la espera de la autorización' }),
    ).toBeDisabled()
  })

  it('muestra el error que devuelve el servidor', async () => {
    mockApi({
      [ESTUDIOS]: { body: [ESTUDIO] },
      [OBRAS]: { body: LISTA },
      [ELEGIR]: { status: 409, body: { detalle: 'Ya elegiste una cobertura para este estudio.' } },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await user.selectOptions(await screen.findByLabelText('Obra social'), 'OSDE')
    await user.click(screen.getByRole('button', { name: 'Dejar a la espera de la autorización' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Ya elegiste una cobertura')
  })
})
