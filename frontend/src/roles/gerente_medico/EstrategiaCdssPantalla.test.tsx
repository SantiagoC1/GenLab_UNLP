import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { mockApi, renderWithQuery, sentTo, startTestSession } from '../../test-utils'
import EstrategiaCdssPantalla from './EstrategiaCdssPantalla'

const GET = 'GET /config_medica/cdss-strategy'
const PUT = 'PUT /config_medica/cdss-strategy'

const option = (name: RegExp | string) => screen.getByRole('radio', { name })

describe('EstrategiaCdssPantalla', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    startTestSession('gerente_medico')
  })
  afterEach(() => vi.unstubAllGlobals())

  it('shows the three strategies with the current one selected', async () => {
    mockApi({ [GET]: { body: { strategy: 'menor_diferencia' } } })
    renderWithQuery(<EstrategiaCdssPantalla />)

    expect(await screen.findAllByRole('radio')).toHaveLength(3)
    expect(option(/Menor diferencia/)).toBeChecked()
    expect(option(/Más síntomas coincidentes/)).not.toBeChecked()
  })

  it('only allows saving once the choice changed', async () => {
    mockApi({ [GET]: { body: { strategy: 'menor_diferencia' } } })
    const user = userEvent.setup()
    renderWithQuery(<EstrategiaCdssPantalla />)

    const save = await screen.findByRole('button', { name: 'Guardar estrategia' })
    expect(save).toBeDisabled()

    await user.click(option(/Más síntomas coincidentes/))
    expect(save).toBeEnabled()
  })

  it('saves the chosen strategy and confirms it', async () => {
    let current = 'menor_diferencia'
    let reads = 0
    const mock = mockApi({
      [GET]: () => {
        reads += 1
        return { body: { strategy: current } }
      },
      [PUT]: () => {
        current = 'sintomas_coincidentes'
        return { body: { strategy: current } }
      },
    })
    const user = userEvent.setup()
    renderWithQuery(<EstrategiaCdssPantalla />)

    await user.click(await screen.findByRole('radio', { name: /Más síntomas coincidentes/ }))
    await user.click(screen.getByRole('button', { name: 'Guardar estrategia' }))

    expect(await screen.findByText('Se guardó la estrategia del CDSS.')).toBeInTheDocument()
    expect(sentTo(mock, PUT)).toEqual([{ strategy: 'sintomas_coincidentes' }])
    expect(option(/Más síntomas coincidentes/)).toBeChecked()
    // La respuesta del guardado reemplaza a la caché: no hay lectura extra ni vuelta al valor viejo
    expect(reads).toBe(1)
  })

  it('shows the message of the server when it cannot save', async () => {
    mockApi({
      [GET]: { body: { strategy: 'menor_diferencia' } },
      [PUT]: { status: 422, body: { detalle: 'Elegí una de las estrategias del CDSS.' } },
    })
    const user = userEvent.setup()
    renderWithQuery(<EstrategiaCdssPantalla />)

    await user.click(await screen.findByRole('radio', { name: /Más síntomas coincidentes/ }))
    await user.click(screen.getByRole('button', { name: 'Guardar estrategia' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Elegí una de las estrategias')
  })

  it('shows the error and retries when the strategy cannot be loaded', async () => {
    let attempts = 0
    mockApi({
      [GET]: () => {
        attempts += 1
        return attempts === 1
          ? { status: 500, body: { detalle: 'Falló.' } }
          : { body: { strategy: 'menor_diferencia' } }
      },
    })
    const user = userEvent.setup()
    renderWithQuery(<EstrategiaCdssPantalla />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Falló.')
    await user.click(screen.getByRole('button', { name: 'Reintentar' }))

    expect(await screen.findAllByRole('radio')).toHaveLength(3)
  })
})
