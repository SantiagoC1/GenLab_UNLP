import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { mockApi, renderApp, startTestSession } from '../../test-utils'

const PATH = '/paciente/documentos'
const MIS_TURNOS = 'GET /turnos/mis-turnos'

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
  URL.createObjectURL = vi.fn(() => 'blob:documento')
  URL.revokeObjectURL = vi.fn()
})

describe('Orden de extracción y consentimiento informado', () => {
  it('muestra el turno, avisa que el consentimiento se entrega en papel y descarga los PDF', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const ruta = new URL(String(input)).pathname
      if (ruta === '/turnos/mis-turnos') {
        return new Response(JSON.stringify([TURNO]), { status: 200 })
      }
      return new Response('%PDF-1.4', {
        status: 200,
        headers: { 'Content-Type': 'application/pdf' },
      })
    })
    vi.stubGlobal('fetch', fetchMock)
    renderApp(PATH)
    const user = userEvent.setup()

    expect(await screen.findByText(/Laboratorio de extracción Córdoba 1/)).toBeInTheDocument()
    expect(screen.getByText(/09:15/)).toBeInTheDocument()
    expect(
      screen.getByText(/Se entrega en papel en el laboratorio de extracción/),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Descargar la orden de extracción' }))
    await user.click(screen.getByRole('button', { name: 'Descargar el consentimiento informado' }))

    await vi.waitFor(() => {
      const rutas = fetchMock.mock.calls.map(([url]) => new URL(String(url)).pathname)
      expect(rutas).toContain('/turnos/7/orden-extraccion')
      expect(rutas).toContain('/turnos/7/consentimiento-informado')
    })
  })

  it('no ofrece documentos si no hay un turno vigente', async () => {
    mockApi({
      [MIS_TURNOS]: { body: [{ ...TURNO, estado: 'Cancelado', orden_extraccion_url: null }] },
    })
    renderApp(PATH)

    expect(await screen.findByText(/No tenés un turno de extracción vigente/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Descargar/ })).not.toBeInTheDocument()
  })

  it('muestra el error cuando no se puede descargar', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const ruta = new URL(String(input)).pathname
        if (ruta === '/turnos/mis-turnos') {
          return new Response(JSON.stringify([TURNO]), { status: 200 })
        }
        return new Response(JSON.stringify({ detalle: 'El turno ya no está vigente.' }), {
          status: 409,
        })
      }),
    )
    renderApp(PATH)
    const user = userEvent.setup()

    await user.click(
      await screen.findByRole('button', { name: 'Descargar la orden de extracción' }),
    )
    expect(await screen.findByRole('alert')).toHaveTextContent('El turno ya no está vigente.')
  })
})
