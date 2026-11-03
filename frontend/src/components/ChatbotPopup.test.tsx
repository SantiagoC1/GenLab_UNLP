import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { RolProvider } from '../roles/RolProvider'
import { mockApi, sentTo, startTestSession } from '../test-utils'
import { Layout } from './Layout'

const MESSAGES = 'POST /chatbot/messages'

const ANSWER = 'Un exoma lee las partes que codifican proteínas.'
const BODY = { answer: ANSWER, conversation_id: 'c-1', kind: 'respuesta' }

type User = ReturnType<typeof userEvent.setup>

/**
 * Draws the real Layout (which decides whether the chatbot shows) around a stub screen, so these
 * tests do not depend on any real screen: those change and make their own requests.
 */
function renderLayout() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/test']}>
        <RolProvider>
          <Routes>
            <Route element={<Layout />}>
              <Route path="*" element={<h1>Pantalla de prueba</h1>} />
            </Route>
          </Routes>
        </RolProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())
beforeEach(() => {
  localStorage.clear()
  sessionStorage.clear()
  mockApi({})
})

async function openChat(user: User) {
  await user.click(await screen.findByRole('button', { name: 'Consultar al chatbot' }))
}

async function typeAndSend(user: User, text: string) {
  await user.type(screen.getByLabelText('Tu consulta'), text)
  await user.click(screen.getByRole('button', { name: 'Enviar' }))
}

describe('Chatbot del paciente', () => {
  it('muestra el botón en las pantallas del paciente', async () => {
    startTestSession('paciente')
    renderLayout()
    expect(await screen.findByRole('button', { name: 'Consultar al chatbot' })).toBeInTheDocument()
  })

  it('no lo muestra en las pantallas de otros roles', async () => {
    startTestSession('administrador_general')
    renderLayout()
    await screen.findByRole('navigation', { name: 'Principal' })
    expect(screen.queryByRole('button', { name: 'Consultar al chatbot' })).not.toBeInTheDocument()
  })

  it('envía la consulta y muestra la respuesta, con el aviso de que no da diagnósticos', async () => {
    startTestSession('paciente')
    const mock = mockApi({ [MESSAGES]: { body: BODY } })
    renderLayout()
    const user = userEvent.setup()

    await openChat(user)
    expect(screen.getByText(/No reemplaza a tu médico/)).toBeInTheDocument()
    await typeAndSend(user, '¿Qué es un exoma?')

    expect(await screen.findByText(ANSWER)).toBeInTheDocument()
    expect(screen.getByText('¿Qué es un exoma?')).toBeInTheDocument()
    expect(sentTo(mock, MESSAGES)).toEqual([
      { message: '¿Qué es un exoma?', conversation_id: null },
    ])
  })

  it('reenvía el identificador de la conversación en el segundo mensaje', async () => {
    startTestSession('paciente')
    const mock = mockApi({ [MESSAGES]: { body: BODY } })
    renderLayout()
    const user = userEvent.setup()

    await openChat(user)
    await typeAndSend(user, 'Hola')
    await screen.findByText(ANSWER)
    await typeAndSend(user, '¿y cómo se hereda?')

    await screen.findAllByText(ANSWER)
    expect(sentTo(mock, MESSAGES)[1]).toEqual({
      message: '¿y cómo se hereda?',
      conversation_id: 'c-1',
    })
  })

  it('avisa si el chatbot no está disponible', async () => {
    startTestSession('paciente')
    mockApi({
      [MESSAGES]: {
        status: 503,
        body: { detalle: "El módulo externo 'chatbot' no está disponible." },
      },
    })
    renderLayout()
    const user = userEvent.setup()

    await openChat(user)
    await typeAndSend(user, 'Hola')

    expect(await screen.findByRole('alert')).toHaveTextContent('no está disponible')
  })

  it('avisa si hay demasiadas consultas', async () => {
    startTestSession('paciente')
    mockApi({
      [MESSAGES]: { status: 429, body: { detalle: 'Hay muchas consultas en este momento.' } },
    })
    renderLayout()
    const user = userEvent.setup()

    await openChat(user)
    await typeAndSend(user, 'Hola')

    expect(await screen.findByRole('alert')).toHaveTextContent('muchas consultas')
  })

  it('se cierra con Escape', async () => {
    startTestSession('paciente')
    renderLayout()
    const user = userEvent.setup()

    await openChat(user)
    expect(screen.getByRole('dialog', { name: 'Chatbot' })).toBeInTheDocument()
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog', { name: 'Chatbot' })).not.toBeInTheDocument()
  })

  it('401: explica que es un problema de conexión sin detalles técnicos', async () => {
    startTestSession('paciente')
    mockApi({ [MESSAGES]: { status: 401, body: { detalle: 'apikey inválida' } } })
    renderLayout()
    const user = userEvent.setup()

    await openChat(user)
    await typeAndSend(user, 'Hola')

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('No pudimos conectarnos con el asistente')
    expect(alert).not.toHaveTextContent('apikey')
  })

  it('422: pide una pregunta de hasta 1000 caracteres', async () => {
    startTestSession('paciente')
    mockApi({ [MESSAGES]: { status: 422, body: { detalle: 'mensaje inválido' } } })
    renderLayout()
    const user = userEvent.setup()

    await openChat(user)
    await typeAndSend(user, 'Hola')

    expect(await screen.findByRole('alert')).toHaveTextContent('hasta 1000 caracteres')
  })

  it('429: indica cuántos segundos esperar y bloquea el envío', async () => {
    startTestSession('paciente')
    mockApi({
      [MESSAGES]: { status: 429, body: { detalle: 'Límite' }, headers: { 'Retry-After': '30' } },
    })
    renderLayout()
    const user = userEvent.setup()

    await openChat(user)
    await typeAndSend(user, 'Hola')

    expect(await screen.findByRole('alert')).toHaveTextContent('en 30 segundos')
    await user.type(screen.getByLabelText('Tu consulta'), 'otra')
    expect(screen.getByRole('button', { name: 'Enviar' })).toBeDisabled()
  })

  it('sin red: ofrece reintentar y reenvía el último mensaje', async () => {
    startTestSession('paciente')
    // Only the first chatbot request fails: the layout makes other requests of its own first.
    let failed = false
    const mock = vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).includes('/chatbot/messages') && !failed) {
        failed = true
        throw new TypeError('Failed to fetch')
      }
      return new Response(JSON.stringify(BODY), { status: 200 })
    })
    vi.stubGlobal('fetch', mock)
    renderLayout()
    const user = userEvent.setup()

    await openChat(user)
    await typeAndSend(user, 'Hola')
    expect(await screen.findByRole('alert')).toHaveTextContent('Algo salió mal')
    await user.click(screen.getByRole('button', { name: 'Reintentar' }))

    expect(await screen.findByText(ANSWER)).toBeInTheDocument()
    expect(screen.getAllByText('Hola')).toHaveLength(1)
  })

  it('no deja enviar un mensaje de más de 1000 caracteres ni uno vacío', async () => {
    startTestSession('paciente')
    mockApi({})
    renderLayout()
    const user = userEvent.setup()

    await openChat(user)
    expect(screen.getByRole('button', { name: 'Enviar' })).toBeDisabled()
    await user.type(screen.getByLabelText('Tu consulta'), '   ')
    expect(screen.getByRole('button', { name: 'Enviar' })).toBeDisabled()
    await user.clear(screen.getByLabelText('Tu consulta'))
    await user.click(screen.getByLabelText('Tu consulta'))
    await user.paste('a'.repeat(1001))
    expect(screen.getByRole('button', { name: 'Enviar' })).toBeDisabled()
    expect(screen.getByText(/demasiado largo/)).toBeInTheDocument()
  })
})
