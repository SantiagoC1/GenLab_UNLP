import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { Pathology } from '../../lib/pathologies'
import type { Symptom } from '../../lib/symptoms'
import { mockApi, renderWithQuery, sentTo, startTestSession } from '../../test-utils'
import PatologiasPantalla from './PatologiasPantalla'

const LIST = 'GET /config_medica/pathologies'
const CREATE = 'POST /config_medica/pathologies'
const SEARCH = 'GET /consulta_medica/symptoms'

const PAIN: Symptom = { code: 'SIM-001', term: 'Dolor' }
const FEVER: Symptom = { code: 'SIM-002', term: 'Fiebre' }
const TIREDNESS: Symptom = { code: 'SIM-003', term: 'Cansancio' }
const RASH: Symptom = { code: 'SIM-004', term: 'Erupción' }
const CATALOG = [PAIN, FEVER, TIREDNESS, RASH]

const POMPE: Pathology = { id: 1, name: 'Pompe', cardinal: PAIN, secondary: [FEVER, TIREDNESS] }

const search = (url: URL) => {
  const text = (url.searchParams.get('q') ?? '').toLowerCase()
  const items = CATALOG.filter((symptom) => symptom.term.toLowerCase().includes(text))
  return { body: { items, page: 1, has_more: false } }
}

async function find(
  user: ReturnType<typeof userEvent.setup>,
  label: string,
  text: string,
  term: string,
) {
  await user.type(screen.getByLabelText(label), text)
  await user.click(await screen.findByRole('button', { name: term }))
}

describe('PatologiasPantalla', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    startTestSession('gerente_medico')
  })
  afterEach(() => vi.unstubAllGlobals())

  it('lists each pathology with its cardinal and secondary symptoms', async () => {
    mockApi({ [LIST]: { body: [POMPE] } })
    renderWithQuery(<PatologiasPantalla />)

    expect(await screen.findByRole('heading', { name: 'Pompe' })).toBeInTheDocument()
    expect(screen.getByText('Dolor')).toBeInTheDocument()
    expect(screen.getByText('Fiebre, Cansancio')).toBeInTheDocument()
  })

  it('says so when there are no pathologies', async () => {
    mockApi({ [LIST]: { body: [] } })
    renderWithQuery(<PatologiasPantalla />)

    expect(await screen.findByText('Todavía no hay patologías cargadas.')).toBeInTheDocument()
  })

  it('shows the error and retries when the list cannot be loaded', async () => {
    let attempts = 0
    mockApi({
      [LIST]: () => {
        attempts += 1
        return attempts === 1 ? { status: 500, body: { detalle: 'Falló.' } } : { body: [POMPE] }
      },
    })
    const user = userEvent.setup()
    renderWithQuery(<PatologiasPantalla />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Falló.')
    await user.click(screen.getByRole('button', { name: 'Reintentar' }))

    expect(await screen.findByRole('heading', { name: 'Pompe' })).toBeInTheDocument()
  })

  it('creates a pathology with its cardinal and two secondary symptoms', async () => {
    let list: Pathology[] = []
    const mock = mockApi({
      [LIST]: () => ({ body: list }),
      [SEARCH]: search,
      [CREATE]: () => {
        list = [{ id: 2, name: 'Fabry', cardinal: PAIN, secondary: [FEVER, TIREDNESS] }]
        return { status: 201, body: list[0] }
      },
    })
    const user = userEvent.setup()
    renderWithQuery(<PatologiasPantalla />)

    await user.click(await screen.findByRole('button', { name: 'Nueva patología' }))
    await user.type(screen.getByLabelText('Nombre de la patología'), '  Fabry ')
    await find(user, 'Buscar síntoma cardinal', 'dol', 'Dolor')
    await find(user, 'Buscar síntomas secundarios', 'fie', 'Fiebre')

    const save = screen.getByRole('button', { name: 'Guardar patología' })
    expect(save).toBeDisabled()

    await find(user, 'Buscar síntomas secundarios', 'can', 'Cansancio')
    expect(save).toBeEnabled()
    await user.click(save)

    expect(await screen.findByText('Se guardó la patología Fabry.')).toBeInTheDocument()
    expect(sentTo(mock, CREATE)).toEqual([
      { name: 'Fabry', cardinal: PAIN, secondary: [FEVER, TIREDNESS] },
    ])
    expect(await screen.findByRole('heading', { name: 'Fabry' })).toBeInTheDocument()
  })

  it('does not offer the cardinal symptom again as a secondary one', async () => {
    mockApi({ [LIST]: { body: [] }, [SEARCH]: search })
    const user = userEvent.setup()
    renderWithQuery(<PatologiasPantalla />)

    await user.click(await screen.findByRole('button', { name: 'Nueva patología' }))
    await find(user, 'Buscar síntoma cardinal', 'dol', 'Dolor')
    await user.type(screen.getByLabelText('Buscar síntomas secundarios'), 'dol')

    await waitFor(() =>
      expect(screen.getByText(/No hay resultados|Ya elegiste/)).toBeInTheDocument(),
    )
    expect(screen.queryByRole('button', { name: 'Dolor' })).not.toBeInTheDocument()
  })

  it('shows the message of the server when the pathology already exists', async () => {
    mockApi({
      [LIST]: { body: [POMPE] },
      [SEARCH]: search,
      [CREATE]: { status: 422, body: { detalle: 'Ya existe una patología con ese nombre.' } },
    })
    const user = userEvent.setup()
    renderWithQuery(<PatologiasPantalla />)

    await user.click(await screen.findByRole('button', { name: 'Nueva patología' }))
    await user.type(screen.getByLabelText('Nombre de la patología'), 'pompe')
    await find(user, 'Buscar síntoma cardinal', 'dol', 'Dolor')
    await find(user, 'Buscar síntomas secundarios', 'fie', 'Fiebre')
    await find(user, 'Buscar síntomas secundarios', 'can', 'Cansancio')
    await user.click(screen.getByRole('button', { name: 'Guardar patología' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Ya existe una patología')
    expect(screen.getByLabelText('Nombre de la patología')).toHaveValue('pompe')
  })

  it('edits the symptoms of a pathology without asking for the name again', async () => {
    let list = [POMPE]
    const mock = mockApi({
      [LIST]: () => ({ body: list }),
      [SEARCH]: search,
      'PUT /config_medica/pathologies/1/symptoms': () => {
        list = [{ ...POMPE, secondary: [FEVER, RASH] }]
        return { body: list[0] }
      },
    })
    const user = userEvent.setup()
    renderWithQuery(<PatologiasPantalla />)

    await user.click(await screen.findByRole('button', { name: 'Editar síntomas de Pompe' }))
    expect(screen.queryByLabelText('Nombre de la patología')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Quitar Cansancio' }))
    const save = screen.getByRole('button', { name: 'Guardar cambios' })
    expect(save).toBeDisabled()

    await find(user, 'Buscar síntomas secundarios', 'erup', 'Erupción')
    await user.click(save)

    expect(await screen.findByText('Se guardó la patología Pompe.')).toBeInTheDocument()
    expect(sentTo(mock, 'PUT /config_medica/pathologies/1/symptoms')).toEqual([
      { cardinal: PAIN, secondary: [FEVER, RASH] },
    ])
    expect(await screen.findByText('Fiebre, Erupción')).toBeInTheDocument()
  })

  it('moves a symptom out of the secondary list when it becomes the cardinal one', async () => {
    mockApi({ [LIST]: { body: [POMPE] }, [SEARCH]: search })
    const user = userEvent.setup()
    renderWithQuery(<PatologiasPantalla />)

    await user.click(await screen.findByRole('button', { name: 'Editar síntomas de Pompe' }))
    await user.click(screen.getByRole('button', { name: 'Quitar Dolor' }))
    await find(user, 'Buscar síntoma cardinal', 'fie', 'Fiebre')

    const secondary = screen.getByRole('list', { name: 'Síntomas secundarios elegidos' })
    expect(within(secondary).queryByText('Fiebre')).not.toBeInTheDocument()
    expect(within(secondary).getByText('Cansancio')).toBeInTheDocument()
  })

  it('cancels the edition and goes back to the list', async () => {
    mockApi({ [LIST]: { body: [POMPE] } })
    const user = userEvent.setup()
    renderWithQuery(<PatologiasPantalla />)

    await user.click(await screen.findByRole('button', { name: 'Editar síntomas de Pompe' }))
    await user.click(screen.getByRole('button', { name: 'Cancelar' }))

    expect(screen.getByRole('button', { name: 'Editar síntomas de Pompe' })).toBeInTheDocument()
  })
})
