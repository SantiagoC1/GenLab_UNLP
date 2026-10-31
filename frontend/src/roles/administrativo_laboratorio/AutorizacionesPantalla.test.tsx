import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { mockApi, renderApp, sentTo, startTestSession } from '../../test-utils'

const PATH = '/administrativo_laboratorio/autorizaciones'
const BANDEJA = 'GET /presupuesto_pago/autorizaciones-pendientes'
const RESPONDER = 'POST /presupuesto_pago/estudios/1/autorizacion'

const PENDIENTE = {
  estudio_id: 1,
  paciente: 'Lucía Fernández',
  obra_social: 'OSDE',
  porcentaje: 80,
  importe_usd: 500,
  estado_estudio: 'Creado',
}

afterEach(() => vi.unstubAllGlobals())
beforeEach(() => {
  localStorage.clear()
  startTestSession('administrativo_laboratorio')
})

describe('Registrar la autorización de la obra social', () => {
  it('registra la autorización y la saca de la bandeja', async () => {
    let pendientes = [PENDIENTE]
    const mock = mockApi({
      [BANDEJA]: () => ({ body: pendientes }),
      [RESPONDER]: () => {
        pendientes = []
        return {
          body: {
            estudio_id: 1,
            estado: 'Autorizado',
            resultado: 'Autorizado',
            paciente_avisado: true,
          },
        }
      },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: /Lucía Fernández/ }))
    expect(screen.getByText('OSDE', { selector: 'strong' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Registrar la respuesta' }))

    expect(await screen.findByRole('status')).toHaveTextContent(
      'Respuesta registrada: estudio Autorizado. El paciente recibió un aviso.',
    )
    expect(await screen.findByText('No hay autorizaciones pendientes.')).toBeInTheDocument()
    expect(sentTo(mock, RESPONDER)).toEqual([{ resultado: 'Autorizado' }])
  })

  it('el rechazo exige el motivo y lo envía', async () => {
    const mock = mockApi({
      [BANDEJA]: { body: [PENDIENTE] },
      [RESPONDER]: {
        body: {
          estudio_id: 1,
          estado: 'Rechazado',
          resultado: 'Rechazado',
          paciente_avisado: true,
        },
      },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: /Lucía Fernández/ }))
    await user.click(screen.getByLabelText('Rechazado'))
    const registrar = screen.getByRole('button', { name: 'Registrar la respuesta' })
    expect(registrar).toBeDisabled()

    await user.type(screen.getByLabelText('Motivo del rechazo'), 'No está en el nomenclador')
    await user.click(registrar)

    expect(await screen.findByRole('status')).toHaveTextContent('estudio Rechazado')
    expect(sentTo(mock, RESPONDER)).toEqual([
      { resultado: 'Rechazado', motivo: 'No está en el nomenclador' },
    ])
  })

  it('muestra el error del servidor', async () => {
    mockApi({
      [BANDEJA]: { body: [PENDIENTE] },
      [RESPONDER]: {
        status: 409,
        body: { detalle: 'El estudio no tiene una autorización de la obra social pendiente.' },
      },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: /Lucía Fernández/ }))
    await user.click(screen.getByRole('button', { name: 'Registrar la respuesta' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('autorización de la obra social')
  })
})
