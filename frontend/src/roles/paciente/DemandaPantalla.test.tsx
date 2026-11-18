import { fireEvent, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { mockApi, renderApp, startTestSession } from '../../test-utils'

const PATH = '/paciente/demanda'
const ESTUDIOS = 'GET /presupuesto_pago/mis-estudios'
const DEMANDA = 'POST /presupuesto_pago/mis-estudios/1/demanda'

const RECHAZADO = {
  id: 1,
  estado: 'Rechazado',
  cantidad_genes: 3,
  importe_usd: 500,
  cobertura: {
    obra_social: 'OSDE',
    porcentaje: 80,
    estado: 'Rechazado',
    motivo_rechazo: 'No cubre estudios genéticos.',
    demanda_enviada: false,
    demanda_nombre: null,
  },
}

afterEach(() => vi.unstubAllGlobals())
beforeEach(() => {
  localStorage.clear()
  startTestSession('paciente')
})

describe('Solicitar la reautorización con una demanda', () => {
  it('muestra el motivo del rechazo y envía el PDF de la demanda', async () => {
    const mock = mockApi({
      [ESTUDIOS]: { body: [RECHAZADO] },
      [DEMANDA]: {
        status: 201,
        body: { estudio_id: 1, demanda_nombre: 'fallo.pdf', administrativo_avisado: true },
      },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    expect(await screen.findByText('No cubre estudios genéticos.')).toBeInTheDocument()
    const archivo = new File(['%PDF-1.4'], 'fallo.pdf', { type: 'application/pdf' })
    await user.upload(screen.getByLabelText('PDF de la demanda'), archivo)
    await user.click(screen.getByRole('button', { name: 'Pedir la reautorización' }))

    expect(await screen.findByRole('status')).toHaveTextContent('Recibimos tu demanda (fallo.pdf)')
    const [, init] = mock.mock.calls.find(([url]) => String(url).endsWith('/demanda'))!
    expect(init?.method).toBe('POST')
    expect(init?.headers).toMatchObject({
      'Content-Type': 'application/pdf',
      'X-Nombre-Archivo': 'fallo.pdf',
    })
  })

  it('rechaza un archivo que no es PDF sin enviarlo', async () => {
    const mock = mockApi({ [ESTUDIOS]: { body: [RECHAZADO] } })
    renderApp(PATH)

    const entrada = await screen.findByLabelText('PDF de la demanda')
    const imagen = new File(['x'], 'foto.png', { type: 'image/png' })
    // `fireEvent` skips the `accept` filter that `userEvent.upload` applies
    fireEvent.change(entrada, { target: { files: [imagen] } })

    expect(await screen.findByRole('alert')).toHaveTextContent('Solo se aceptan archivos PDF.')
    expect(screen.getByRole('button', { name: 'Pedir la reautorización' })).toBeDisabled()
    expect(mock.mock.calls.some(([, init]) => init?.method === 'POST')).toBe(false)
  })

  it('muestra el error del servidor, por ejemplo si el archivo no es un PDF real', async () => {
    mockApi({
      [ESTUDIOS]: { body: [RECHAZADO] },
      [DEMANDA]: { status: 422, body: { detalle: 'El archivo no es un PDF.' } },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    const archivo = new File(['no soy pdf'], 'falso.pdf', { type: 'application/pdf' })
    await user.upload(await screen.findByLabelText('PDF de la demanda'), archivo)
    await user.click(screen.getByRole('button', { name: 'Pedir la reautorización' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('El archivo no es un PDF.')
  })

  it('si ya envió la demanda lo informa y no ofrece enviarla de nuevo', async () => {
    mockApi({
      [ESTUDIOS]: {
        body: [
          {
            ...RECHAZADO,
            cobertura: {
              ...RECHAZADO.cobertura,
              demanda_enviada: true,
              demanda_nombre: 'fallo.pdf',
            },
          },
        ],
      },
    })
    renderApp(PATH)

    expect(await screen.findByText(/Ya enviaste la demanda \(fallo.pdf\)/)).toBeInTheDocument()
    expect(screen.queryByLabelText('PDF de la demanda')).not.toBeInTheDocument()
  })

  it('avisa cuando no hay estudios Rechazados', async () => {
    mockApi({ [ESTUDIOS]: { body: [] } })
    renderApp(PATH)
    expect(await screen.findByText('No tenés estudios Rechazados.')).toBeInTheDocument()
  })
})
