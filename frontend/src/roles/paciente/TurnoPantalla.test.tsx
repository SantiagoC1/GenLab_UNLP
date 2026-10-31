import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { mockApi, renderApp, sentTo, startTestSession } from '../../test-utils'

const PATH = '/paciente/turno'
const HABILITADOS = 'GET /turnos/habilitados'
const LABORATORIOS = 'GET /turnos/laboratorios'
const LIBRES = 'GET /turnos/laboratorios/1/turnos-libres'
const RESERVAR = 'POST /turnos/reservas'

const LAB = {
  id: 1,
  nombre: 'Laboratorio de extracción Córdoba 1',
  direccion: 'Av. San Martín 100, Córdoba',
  provincia: 'Córdoba',
  latitud: -31.42,
  longitud: -64.18,
  proximo_turno: '2026-11-03T09:00:00-03:00',
}
const OTRO = {
  ...LAB,
  id: 2,
  nombre: 'Laboratorio de extracción Salta 1',
  provincia: 'Salta',
  latitud: -24.78,
  longitud: -65.41,
}
const HABILITADO = { estudio_id: 1, estado: 'Pagado', motivo: 'pagado' }
const DIA_CON_TURNOS = {
  laboratorio_id: 1,
  fecha: '2026-11-03',
  turnos: ['2026-11-03T09:00:00-03:00', '2026-11-03T09:15:00-03:00'],
  motivo: null,
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})
beforeEach(() => {
  localStorage.clear()
  startTestSession('paciente')
})

async function elegirLaboratorio(user: ReturnType<typeof userEvent.setup>) {
  await user.click(
    await screen.findByRole('button', { name: /^Laboratorio de extracción Córdoba 1/ }),
  )
}

describe('Sacar turno de extracción', () => {
  it('elige un laboratorio y un turno libre, y reserva', async () => {
    const mock = mockApi({
      [HABILITADOS]: { body: [HABILITADO] },
      [LABORATORIOS]: { body: [LAB, OTRO] },
      [LIBRES]: { body: DIA_CON_TURNOS },
      [RESERVAR]: {
        status: 201,
        body: { id: 1, estudio_id: 1, laboratorio: LAB, inicio: '2026-11-03T09:15:00-03:00' },
      },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await elegirLaboratorio(user)
    await user.click(await screen.findByRole('button', { name: '09:15' }))
    await user.click(screen.getByRole('button', { name: 'Reservar el turno' }))

    expect(await screen.findByRole('status')).toHaveTextContent(
      'Turno reservado en Laboratorio de extracción Córdoba 1',
    )
    expect(screen.getByRole('link', { name: 'Documentos' })).toBeInTheDocument()
    expect(sentTo(mock, RESERVAR)).toEqual([
      { estudio_id: 1, laboratorio_id: 1, inicio: '2026-11-03T09:15:00-03:00' },
    ])
  })

  it('se puede elegir el laboratorio también desde el mapa', async () => {
    mockApi({
      [HABILITADOS]: { body: [HABILITADO] },
      [LABORATORIOS]: { body: [LAB, OTRO] },
      [LIBRES]: { body: DIA_CON_TURNOS },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await user.click(
      await screen.findByRole('button', { name: 'Mapa: Laboratorio de extracción Córdoba 1' }),
    )
    expect(
      await screen.findByText('Turnos de Laboratorio de extracción Córdoba 1'),
    ).toBeInTheDocument()
  })

  it('filtra los laboratorios por provincia', async () => {
    mockApi({
      [HABILITADOS]: { body: [HABILITADO] },
      [LABORATORIOS]: { body: [LAB, OTRO] },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await user.selectOptions(await screen.findByLabelText('Provincia'), 'Salta')
    expect(
      screen.queryByRole('button', { name: /^Laboratorio de extracción Córdoba 1/ }),
    ).toBeNull()
    expect(
      screen.getByRole('button', { name: /^Laboratorio de extracción Salta 1/ }),
    ).toBeInTheDocument()
  })

  it('si el turno se ocupó antes de reservarlo informa y muestra los libres actualizados', async () => {
    let libres = DIA_CON_TURNOS
    mockApi({
      [HABILITADOS]: { body: [HABILITADO] },
      [LABORATORIOS]: { body: [LAB] },
      [LIBRES]: () => ({ body: libres }),
      [RESERVAR]: () => {
        libres = { ...DIA_CON_TURNOS, turnos: ['2026-11-03T09:15:00-03:00'] }
        return {
          status: 409,
          body: { detalle: 'Ese turno se ocupó antes de que lo reserves.', code: 'turno_ocupado' },
        }
      },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await elegirLaboratorio(user)
    await user.click(await screen.findByRole('button', { name: '09:00' }))
    await user.click(screen.getByRole('button', { name: 'Reservar el turno' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('se ocupó antes de que lo reserves')
    await vi.waitFor(() => expect(screen.queryByRole('button', { name: '09:00' })).toBeNull())
    expect(screen.getByRole('button', { name: '09:15' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reservar el turno' })).toBeDisabled()
  })

  it('informa cuando no hay turnos ese día', async () => {
    mockApi({
      [HABILITADOS]: { body: [HABILITADO] },
      [LABORATORIOS]: { body: [LAB] },
      [LIBRES]: {
        body: {
          laboratorio_id: 1,
          fecha: '2026-11-07',
          turnos: [],
          motivo: 'Los laboratorios atienden de lunes a viernes.',
        },
      },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await elegirLaboratorio(user)
    expect(
      await screen.findByText('Los laboratorios atienden de lunes a viernes.'),
    ).toBeInTheDocument()
  })

  it('no ofrece turnos si ningún estudio está habilitado', async () => {
    mockApi({ [HABILITADOS]: { body: [] }, [LABORATORIOS]: { body: [LAB] } })
    renderApp(PATH)

    expect(
      await screen.findByText(/No tenés estudios habilitados para sacar turno/),
    ).toBeInTheDocument()
    expect(screen.queryByLabelText('Provincia')).not.toBeInTheDocument()
  })

  it('avisa que hace falta una nueva muestra, sin costo, cuando hay un remuestreo', async () => {
    mockApi({
      [HABILITADOS]: {
        body: [
          {
            estudio_id: 1,
            estado: 'TurnoSacado',
            motivo: 'nueva_reserva',
            inasistencias: 0,
            remuestreo_motivo: 'volumen_menor_2ml',
          },
        ],
      },
      [LABORATORIOS]: { body: [LAB] },
    })
    renderApp(PATH)

    expect(
      await screen.findByText(/Hace falta una nueva muestra: la muestra tuvo menos de 2 ml/),
    ).toBeInTheDocument()
    expect(screen.getByText(/no tiene costo/)).toBeInTheDocument()
    expect(await screen.findByLabelText('Provincia')).toBeInTheDocument()
  })
})
