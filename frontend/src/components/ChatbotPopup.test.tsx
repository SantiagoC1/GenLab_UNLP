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
  mockApi({})
})

async function openChat(user: User) {
  await user.click(await screen.findByRole('button', { name: 'Abrir chat' }))
}

async function typeAndSend(user: User, text: string) {
  await user.type(screen.getByLabelText('Tu consulta'), text)
  await user.click(screen.getByRole('button', { name: 'Enviar' }))
}

describe('Chatbot del paciente', () => {
  it('muestra el botón en las pantallas del paciente', async () => {
    startTestSession('paciente')
    renderLayout()
    expect(await screen.findByRole('button', { name: 'Abrir chat' })).toBeInTheDocument()
  })

  it('no lo muestra en las pantallas de otros roles', async () => {
    startTestSession('administrador_general')
    renderLayout()
    await screen.findByRole('navigation', { name: 'Principal' })
    expect(screen.queryByRole('button', { name: 'Abrir chat' })).not.toBeInTheDocument()
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
    expect(screen.getByRole('region', { name: 'Chatbot' })).toBeInTheDocument()
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('region', { name: 'Chatbot' })).not.toBeInTheDocument()
  })
})
