import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { mockApi, renderApp, startTestSession } from '../../test-utils'

const PATH = '/administrativo_laboratorio/simuladores'
const AGENDA = 'GET /turnos/agenda'
const INASISTENCIA = 'POST /turnos/1/inasistencia'

const TURNO = {
  turno_id: 1,
  estudio_id: 1,
  paciente: 'Lucía Fernández',
  laboratorio: 'Laboratorio de extracción Córdoba 1',
  inicio: '2026-11-03T09:15:00-03:00',
  ya_paso: true,
  inasistencias: 0,
}

afterEach(() => vi.unstubAllGlobals())
beforeEach(() => {
  localStorage.clear()
  startTestSession('administrativo_laboratorio')
})

describe('Simulador del laboratorio de extracción: inasistencias', () => {
  it('registra la inasistencia de un turno que ya pasó', async () => {
    let agenda = [TURNO]
    const mock = mockApi({
      [AGENDA]: () => ({ body: agenda }),
      [INASISTENCIA]: () => {
        agenda = []
        return {
          body: {
            turno: { id: 1 },
            inasistencias: 1,
            limite: 5,
            limite_alcanzado: false,
            paciente_avisado: true,
          },
        }
      },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    expect(await screen.findByText(/Lucía Fernández · estudio 1/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Registrar inasistencia' }))

    expect(await screen.findByRole('status')).toHaveTextContent(
      'Inasistencia registrada: el paciente acumula 1 de 5. Se le avisó al paciente.',
    )
    expect(await screen.findByText('No hay turnos programados.')).toBeInTheDocument()
    expect(mock).toHaveBeenCalledWith(
      expect.stringContaining('/turnos/1/inasistencia'),
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('no deja registrar la inasistencia de un turno que todavía no pasó', async () => {
    mockApi({ [AGENDA]: { body: [{ ...TURNO, ya_paso: false }] } })
    renderApp(PATH)

    expect(await screen.findByRole('button', { name: 'Registrar inasistencia' })).toBeDisabled()
  })

  it('informa cuando el paciente llega al límite', async () => {
    mockApi({
      [AGENDA]: { body: [{ ...TURNO, inasistencias: 4 }] },
      [INASISTENCIA]: {
        body: {
          turno: { id: 1 },
          inasistencias: 5,
          limite: 5,
          limite_alcanzado: true,
          paciente_avisado: true,
        },
      },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Registrar inasistencia' }))
    expect(await screen.findByRole('status')).toHaveTextContent('Llegó al límite de inasistencias.')
  })

  it('muestra el error del servidor', async () => {
    mockApi({
      [AGENDA]: { body: [TURNO] },
      [INASISTENCIA]: {
        status: 409,
        body: { detalle: 'El turno está Cancelado: no se puede registrar una inasistencia.' },
      },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Registrar inasistencia' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('no se puede registrar')
  })
})
