import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { mockApi, renderApp, startTestSession } from '../../test-utils'

const PATH = '/paciente/turnos'
const MIS_TURNOS = 'GET /turnos/mis-turnos'
const CANCELAR = 'POST /turnos/7/cancelar'

const LAB = {
  id: 1,
  nombre: 'Laboratorio de extracción Córdoba 1',
  direccion: 'Av. San Martín 100, Córdoba',
  provincia: 'Córdoba',
  latitud: -31.42,
  longitud: -64.18,
  proximo_turno: null,
}
const TURNO = {
  id: 7,
  estudio_id: 1,
  laboratorio: LAB,
  inicio: '2026-11-03T09:15:00-03:00',
  estado: 'Programado',
  recordatorio_para: '2026-11-02T09:15:00-03:00',
  puede_cancelar: true,
  orden_extraccion_url: '/turnos/7/orden-extraccion',
  consentimiento_url: '/turnos/7/consentimiento-informado',
}

afterEach(() => vi.unstubAllGlobals())
beforeEach(() => {
  localStorage.clear()
  startTestSession('paciente')
})

describe('Mis turnos: cancelar', () => {
  it('pide confirmación y cancela un turno futuro', async () => {
    let turnos = [TURNO]
    const mock = mockApi({
      [MIS_TURNOS]: () => ({ body: turnos }),
      [CANCELAR]: () => {
        turnos = [{ ...TURNO, estado: 'Cancelado', puede_cancelar: false }]
        return { body: { turno: turnos[0], estudio_estado: 'Pagado' } }
      },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Cancelar el turno' }))
    expect(screen.getByText(/No tiene costo/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Sí, cancelar el turno' }))

    expect(await screen.findByRole('status')).toHaveTextContent('Cancelaste el turno, sin costo.')
    expect(await screen.findByText('Cancelado')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Cancelar el turno' })).not.toBeInTheDocument()
    expect(mock).toHaveBeenCalledWith(
      expect.stringContaining('/turnos/7/cancelar'),
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('se puede arrepentir antes de confirmar', async () => {
    const mock = mockApi({ [MIS_TURNOS]: { body: [TURNO] } })
    renderApp(PATH)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Cancelar el turno' }))
    await user.click(screen.getByRole('button', { name: 'No, conservarlo' }))

    expect(screen.getByRole('button', { name: 'Cancelar el turno' })).toBeInTheDocument()
    expect(mock.mock.calls.some(([, init]) => init?.method === 'POST')).toBe(false)
  })

  it('un turno cuya hora ya pasó no se puede cancelar', async () => {
    mockApi({ [MIS_TURNOS]: { body: [{ ...TURNO, puede_cancelar: false }] } })
    renderApp(PATH)

    expect(await screen.findByText(/El horario de este turno ya pasó/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Cancelar el turno' })).not.toBeInTheDocument()
  })

  it('muestra el error cuando el servidor no deja cancelar', async () => {
    mockApi({
      [MIS_TURNOS]: { body: [TURNO] },
      [CANCELAR]: {
        status: 409,
        body: { detalle: 'El horario del turno ya pasó: no se puede cancelar.' },
      },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Cancelar el turno' }))
    await user.click(screen.getByRole('button', { name: 'Sí, cancelar el turno' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('ya pasó')
  })

  it('invita a sacar un turno cuando todavía no hay ninguno', async () => {
    mockApi({ [MIS_TURNOS]: { body: [] } })
    renderApp(PATH)
    expect(await screen.findByText(/Todavía no sacaste ningún turno/)).toBeInTheDocument()
  })
})
