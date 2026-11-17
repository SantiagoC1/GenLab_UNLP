import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { mockApi, renderApp, sentTo, startTestSession } from '../../test-utils'

const PATH = '/medico_tratante/asignar-cupon'
const MIS_CUPONES = 'GET /cupones/mis-cupones'
const PACIENTES = 'GET /cupones/mis-pacientes'
const ASIGNAR = 'POST /cupones/asignar-a-paciente'

const cupon = (codigo: string) => ({
  codigo,
  descuento: 20,
  estado: 'Vigente',
  pdf_url: `/cupones/${codigo}/pdf`,
  qr: null,
  medico: 'ana@example.com',
  paciente: null,
})
const LUCIA = { contacto: 'lucia@example.com', nombre: 'Lucía Fernández' }

afterEach(() => vi.unstubAllGlobals())
beforeEach(() => {
  localStorage.clear()
  startTestSession('medico_tratante')
})

describe('Asignar un cupón de descuento al paciente', () => {
  it('asigna un cupón disponible a un paciente y descuenta de los disponibles', async () => {
    let disponibles = [cupon('CUP-0001'), cupon('CUP-0002')]
    const mock = mockApi({
      [MIS_CUPONES]: () => ({ body: { cantidad: disponibles.length, cupones: disponibles } }),
      [PACIENTES]: { body: [LUCIA] },
      [ASIGNAR]: () => {
        disponibles = [cupon('CUP-0002')]
        return {
          body: {
            paciente: LUCIA,
            cupon: cupon('CUP-0001'),
            disponibles: 1,
            paciente_avisado: true,
          },
        }
      },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    expect(await screen.findByText('2')).toBeInTheDocument()
    await screen.findByRole('option', { name: 'Lucía Fernández' })
    await user.selectOptions(screen.getByLabelText('Paciente'), 'lucia@example.com')
    await user.selectOptions(screen.getByLabelText('Cupón'), 'CUP-0001')
    await user.click(screen.getByRole('button', { name: 'Asignar el cupón' }))

    expect(await screen.findByRole('status')).toHaveTextContent(
      'El cupón CUP-0001 ya figura en la vista de Lucía Fernández. Te quedan 1 cupones disponibles.',
    )
    expect(sentTo(mock, ASIGNAR)).toEqual([
      { contacto_paciente: 'lucia@example.com', codigo: 'CUP-0001' },
    ])
    expect(await screen.findByText('1')).toBeInTheDocument()
  })

  it('deshabilita la asignación si el médico no tiene cupones', async () => {
    mockApi({
      [MIS_CUPONES]: { body: { cantidad: 0, cupones: [] } },
      [PACIENTES]: { body: [LUCIA] },
    })
    renderApp(PATH)

    expect(await screen.findByText(/No tenés cupones disponibles/)).toBeInTheDocument()
    expect(screen.getByLabelText('Paciente')).toBeDisabled()
    expect(screen.getByLabelText('Cupón')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Asignar el cupón' })).toBeDisabled()
  })

  it('muestra el error cuando el servidor rechaza la asignación', async () => {
    mockApi({
      [MIS_CUPONES]: { body: { cantidad: 1, cupones: [cupon('CUP-0001')] } },
      [PACIENTES]: { body: [LUCIA] },
      [ASIGNAR]: { status: 409, body: { detalle: 'El cupón CUP-0001 no está Vigente.' } },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await screen.findByRole('option', { name: 'Lucía Fernández' })
    await screen.findByRole('option', { name: /CUP-0001/ })
    await user.selectOptions(screen.getByLabelText('Paciente'), 'lucia@example.com')
    await user.selectOptions(screen.getByLabelText('Cupón'), 'CUP-0001')
    await user.click(screen.getByRole('button', { name: 'Asignar el cupón' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('no está Vigente')
  })
})
