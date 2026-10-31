import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { mockApi, renderApp, sentTo, startTestSession } from '../../test-utils'

const PATH = '/gerente_medico/asignar-cupones-medicos'
const LISTA = 'GET /cupones'
const MEDICOS = 'GET /cupones/medicos'
const ASIGNAR = 'POST /cupones/asignar-a-medico'

const cupon = (codigo: string, extra = {}) => ({
  codigo,
  descuento: 20,
  estado: 'Vigente',
  pdf_url: `/cupones/${codigo}/pdf`,
  qr: null,
  medico: null,
  paciente: null,
  ...extra,
})
const ANA = { contacto: 'ana@example.com', nombre: 'Ana Pérez', matricula: 'MP-12345' }

afterEach(() => vi.unstubAllGlobals())
beforeEach(() => {
  localStorage.clear()
  startTestSession('gerente_medico')
})

async function buscarAAna(user: ReturnType<typeof userEvent.setup>) {
  await user.type(await screen.findByLabelText('Buscar médico por nombre o matrícula'), 'ana')
  await user.click(screen.getByRole('button', { name: 'Buscar' }))
  await user.click(await screen.findByRole('button', { name: /Ana Pérez/ }))
}

describe('Asignar cupones al médico tratante', () => {
  it('busca al médico, elige cupones Vigentes sin asignar y los asigna', async () => {
    const mock = mockApi({
      [LISTA]: {
        body: [
          cupon('CUP-0001'),
          cupon('CUP-0002'),
          cupon('CUP-0003', { medico: 'otro@example.com' }),
          cupon('CUP-0004', { estado: 'Usado' }),
        ],
      },
      [MEDICOS]: { body: [ANA] },
      [ASIGNAR]: { body: { medico: ANA, codigos: ['CUP-0001', 'CUP-0002'], medico_avisado: true } },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await buscarAAna(user)
    expect(screen.queryByText(/CUP-0003/)).not.toBeInTheDocument()
    expect(screen.queryByText(/CUP-0004/)).not.toBeInTheDocument()

    await user.click(screen.getByLabelText('CUP-0001 · 20%'))
    await user.click(screen.getByLabelText('CUP-0002 · 20%'))
    await user.click(screen.getByRole('button', { name: 'Asignar 2 cupones' }))

    expect(await screen.findByRole('status')).toHaveTextContent(
      'Se asignaron 2 cupones a Ana Pérez. El médico recibió un aviso.',
    )
    expect(sentTo(mock, ASIGNAR)).toEqual([
      { contacto_medico: 'ana@example.com', codigos: ['CUP-0001', 'CUP-0002'] },
    ])
  })

  it('avisa cuando no se encuentra ningún médico', async () => {
    mockApi({ [LISTA]: { body: [] }, [MEDICOS]: { body: [] } })
    renderApp(PATH)
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText('Buscar médico por nombre o matrícula'), 'zzz')
    await user.click(screen.getByRole('button', { name: 'Buscar' }))
    expect(await screen.findByText('No se encontró ningún médico.')).toBeInTheDocument()
  })

  it('no deja asignar sin elegir cupones y muestra el error del servidor', async () => {
    mockApi({
      [LISTA]: { body: [cupon('CUP-0001')] },
      [MEDICOS]: { body: [ANA] },
      [ASIGNAR]: { status: 409, body: { detalle: 'El cupón CUP-0001 no está Vigente.' } },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await buscarAAna(user)
    const asignar = screen.getByRole('button', { name: /^Asignar/ })
    expect(asignar).toBeDisabled()
    await user.click(screen.getByLabelText('CUP-0001 · 20%'))
    await user.click(screen.getByRole('button', { name: /^Asignar/ }))
    expect(await screen.findByRole('alert')).toHaveTextContent('no está Vigente')
  })
})
