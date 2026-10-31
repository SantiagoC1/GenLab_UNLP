import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { mockApi, renderApp, sentTo, startTestSession } from '../../test-utils'

const PATH = '/administrativo_laboratorio/simuladores'
const AGENDA = 'GET /turnos/agenda'
const INASISTENCIA = 'POST /turnos/1/inasistencia'
const MUESTRA = 'POST /turnos/notificaciones-muestra'

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

  it('manda el mensaje de Telegram con el volumen y el estudio pasa a Listo para retirar', async () => {
    let agenda = [TURNO]
    const mock = mockApi({
      [AGENDA]: () => ({ body: agenda }),
      [MUESTRA]: () => {
        agenda = []
        return {
          body: {
            estudio_id: 1,
            estado: 'ListoParaRetirar',
            volumen_ml: 3.5,
            volumen_suficiente: true,
            listo_para_retirar: true,
          },
        }
      },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    const enviar = await screen.findByRole('button', { name: 'Enviar mensaje de Telegram' })
    expect(enviar).toBeDisabled()
    await user.type(screen.getByLabelText('Volumen de la muestra (ml)'), '3.5')
    expect(
      screen.getByText(/Mensaje del bot: «Muestra tomada · estudio 1 · 3.5 ml»/),
    ).toBeInTheDocument()
    await user.click(enviar)

    expect(await screen.findByRole('status')).toHaveTextContent(
      'Notificación recibida: estudio 1, 3.5 ml. El estudio pasó a Listo para retirar.',
    )
    expect(sentTo(mock, MUESTRA)).toEqual([{ estudio_id: 1, volumen_ml: 3.5 }])
  })

  it('avisa que con menos de 2 ml no se habilita el retiro', async () => {
    mockApi({
      [AGENDA]: { body: [TURNO] },
      [MUESTRA]: {
        body: {
          estudio_id: 1,
          estado: 'TurnoSacado',
          volumen_ml: 1.5,
          volumen_suficiente: false,
          listo_para_retirar: false,
          remuestreo: { medico_avisado: true, paciente_avisado: true },
        },
      },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText('Volumen de la muestra (ml)'), '1.5')
    await user.click(screen.getByRole('button', { name: 'Enviar mensaje de Telegram' }))

    expect(await screen.findByRole('status')).toHaveTextContent(
      'El volumen es menor a 2 ml: no se habilita el retiro y se habilitó un remuestreo sin costo. Se avisó al médico y al paciente.',
    )
  })

  it('muestra el error cuando la notificación se rechaza', async () => {
    mockApi({
      [AGENDA]: { body: [TURNO] },
      [MUESTRA]: {
        status: 409,
        body: {
          detalle: 'El estudio no tiene un turno de extracción vigente: no se espera una muestra.',
        },
      },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText('Volumen de la muestra (ml)'), '3')
    await user.click(screen.getByRole('button', { name: 'Enviar mensaje de Telegram' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('no se espera una muestra')
  })
})
