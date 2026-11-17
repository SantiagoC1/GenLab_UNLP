import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import type { Symptom } from '../lib/symptoms'
import { mockApi, queriesTo, renderWithQuery, startTestSession } from '../test-utils'
import { SymptomSearch } from './SymptomSearch'

const SEARCH = 'GET /consulta_medica/symptoms'
const HYPOTONIA: Symptom = { code: 'SIM-009', term: 'Hipotonía' }
const HEPATOMEGALY: Symptom = { code: 'SIM-007', term: 'Hepatomegalia' }
const DEBOUNCE_MS = 10

const found = (items: Symptom[], page = 1, hasMore = false) => ({
  body: { items, page, has_more: hasMore },
})

function renderSearch(props: Partial<React.ComponentProps<typeof SymptomSearch>> = {}) {
  const onSelect = vi.fn()
  renderWithQuery(
    <SymptomSearch selected={[]} onSelect={onSelect} debounceMs={DEBOUNCE_MS} {...props} />,
  )
  return { onSelect, user: userEvent.setup() }
}

const field = () => screen.getByLabelText('Buscar síntoma')
const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

describe('SymptomSearch', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    startTestSession('medico_tratante')
  })
  afterEach(() => vi.unstubAllGlobals())

  it('with fewer than 3 letters it asks for more and does not search', async () => {
    const mock = mockApi({ [SEARCH]: found([HYPOTONIA]) })
    const { user } = renderSearch()

    await user.type(field(), 'hi')
    await wait(DEBOUNCE_MS * 5)

    expect(screen.getByText(/al menos 3 letras/)).toBeInTheDocument()
    expect(queriesTo(mock, SEARCH)).toHaveLength(0)
  })

  it('with 3 letters or more it searches only the final text, trimmed', async () => {
    const mock = mockApi({ [SEARCH]: found([HYPOTONIA]) })
    const { user } = renderSearch()

    await user.type(field(), '  hipotonia  ')

    expect(await screen.findByRole('button', { name: 'Hipotonía' })).toBeInTheDocument()
    const queries = queriesTo(mock, SEARCH)
    expect(queries.every((query) => query.get('q')!.length >= 3)).toBe(true)
    expect(queries.at(-1)?.get('q')).toBe('hipotonia')
    expect(queries.at(-1)?.get('page')).toBe('1')
  })

  it('choosing a result reports it, empties the field and focuses it to search again', async () => {
    mockApi({ [SEARCH]: found([HYPOTONIA]) })
    const { user, onSelect } = renderSearch()

    await user.type(field(), 'hip')
    await user.click(await screen.findByRole('button', { name: 'Hipotonía' }))

    expect(onSelect).toHaveBeenCalledExactlyOnceWith(HYPOTONIA)
    expect(field()).toHaveValue('')
    expect(field()).toHaveFocus()
    expect(screen.queryByRole('button', { name: 'Hipotonía' })).not.toBeInTheDocument()
  })

  it('does not offer a symptom that was already chosen', async () => {
    mockApi({ [SEARCH]: found([HYPOTONIA, HEPATOMEGALY]) })
    const { user } = renderSearch({ selected: [HYPOTONIA] })

    await user.type(field(), 'hip')

    expect(await screen.findByRole('button', { name: 'Hepatomegalia' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Hipotonía' })).not.toBeInTheDocument()
  })

  it('without matches it says so and gives no way to add free text', async () => {
    mockApi({ [SEARCH]: found([]) })
    const { user, onSelect } = renderSearch()

    await user.type(field(), 'zzzz')

    expect(await screen.findByText(/No hay resultados para «zzzz»/)).toBeInTheDocument()
    await user.type(field(), '{Enter}')
    expect(onSelect).not.toHaveBeenCalled()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('pressing Enter never adds the typed text nor submits the surrounding form', async () => {
    mockApi({ [SEARCH]: found([HYPOTONIA]) })
    const onSubmit = vi.fn((event: React.FormEvent) => event.preventDefault())
    const onSelect = vi.fn()
    renderWithQuery(
      <form onSubmit={onSubmit}>
        <SymptomSearch selected={[]} onSelect={onSelect} debounceMs={DEBOUNCE_MS} />
      </form>,
    )
    const user = userEvent.setup()

    await user.type(field(), 'hip')
    await screen.findByRole('button', { name: 'Hipotonía' })
    await user.type(field(), '{Enter}')

    expect(onSelect).not.toHaveBeenCalled()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('shows the text searched as plain text, never as HTML', async () => {
    mockApi({ [SEARCH]: found([]) })
    const { user } = renderSearch()

    await user.type(field(), '<img src=x onerror=alert(1)>')

    expect(await screen.findByText(/No hay resultados para/)).toBeInTheDocument()
    expect(document.querySelector('img')).toBeNull()
  })

  it('when SNOMED fails it shows the message and retries on demand', async () => {
    let calls = 0
    mockApi({
      [SEARCH]: () =>
        ++calls === 1
          ? { status: 503, body: { detalle: "El módulo externo 'SNOMED' no está disponible." } }
          : found([HYPOTONIA]),
    })
    const { user } = renderSearch()

    await user.type(field(), 'hip')
    expect(await screen.findByRole('alert')).toHaveTextContent('no está disponible')

    await user.click(screen.getByRole('button', { name: 'Reintentar' }))

    expect(await screen.findByRole('button', { name: 'Hipotonía' })).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('when the connection fails it explains it without breaking', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    const { user } = renderSearch()

    await user.type(field(), 'hip')

    expect(await screen.findByRole('alert')).toHaveTextContent('Revisá tu conexión')
  })

  it('paginates with Previous and Next, and goes back to page 1 when the text changes', async () => {
    const mock = mockApi({
      [SEARCH]: (url) =>
        url.searchParams.get('page') === '2'
          ? found([HEPATOMEGALY], 2, false)
          : found([HYPOTONIA], 1, true),
    })
    const { user } = renderSearch()

    await user.type(field(), 'hip')
    await screen.findByRole('button', { name: 'Hipotonía' })
    expect(screen.getByRole('button', { name: 'Anterior' })).toBeDisabled()

    await user.click(screen.getByRole('button', { name: 'Siguiente' }))
    expect(await screen.findByRole('button', { name: 'Hepatomegalia' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Siguiente' })).toBeDisabled()

    await user.click(screen.getByRole('button', { name: 'Anterior' }))
    expect(await screen.findByRole('button', { name: 'Hipotonía' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Siguiente' }))
    await screen.findByRole('button', { name: 'Hepatomegalia' })
    await user.type(field(), 'n')
    await waitFor(() => expect(queriesTo(mock, SEARCH).at(-1)?.get('q')).toBe('hipn'))
    expect(queriesTo(mock, SEARCH).at(-1)?.get('page')).toBe('1')
  })

  it('an empty page after the first one says there are no more results', async () => {
    mockApi({
      [SEARCH]: (url) =>
        url.searchParams.get('page') === '2' ? found([], 2, false) : found([HYPOTONIA], 1, true),
    })
    const { user } = renderSearch()

    await user.type(field(), 'hip')
    await user.click(await screen.findByRole('button', { name: 'Siguiente' }))

    expect(await screen.findByText('No hay más resultados.')).toBeInTheDocument()
    expect(screen.queryByText(/No hay resultados para/)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Anterior' })).toBeEnabled()
  })

  it('deleting letters below the minimum hides the results and stops searching', async () => {
    const mock = mockApi({ [SEARCH]: found([HYPOTONIA]) })
    const { user } = renderSearch()

    await user.type(field(), 'hip')
    await screen.findByRole('button', { name: 'Hipotonía' })
    const before = queriesTo(mock, SEARCH).length

    await user.type(field(), '{Backspace}')
    await wait(DEBOUNCE_MS * 5)

    expect(screen.queryByRole('button', { name: 'Hipotonía' })).not.toBeInTheDocument()
    expect(queriesTo(mock, SEARCH)).toHaveLength(before)
  })

  it('in single mode it is disabled once a symptom was chosen', async () => {
    function Cardinal() {
      const [chosen, setChosen] = useState<Symptom[]>([])
      return (
        <SymptomSearch
          single
          selected={chosen}
          onSelect={(s) => setChosen([s])}
          debounceMs={DEBOUNCE_MS}
        />
      )
    }
    mockApi({ [SEARCH]: found([HYPOTONIA]) })
    renderWithQuery(<Cardinal />)
    const user = userEvent.setup()

    await user.type(field(), 'hip')
    await user.click(await screen.findByRole('button', { name: 'Hipotonía' }))

    expect(field()).toBeDisabled()
    expect(screen.getByText(/Quitá el síntoma elegido/)).toBeInTheDocument()
  })
})
