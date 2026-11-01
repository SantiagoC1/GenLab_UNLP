import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { mockApi, renderApp, sentTo, startTestSession } from '../test-utils'

const PATH = '/paciente/turnos'
const MESSAGES = 'POST /chatbot/messages'

const ANSWER = 'Un exoma lee las partes que codifican proteínas.'
const BODY = { answer: ANSWER, conversation_id: 'c-1', kind: 'respuesta' }

type User = ReturnType<typeof userEvent.setup>

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
    renderApp(PATH)
    expect(await screen.findByRole('button', { name: 'Abrir chat' })).toBeInTheDocument()
  })

  it('no lo muestra en las pantallas de otros roles', async () => {
    startTestSession('administrador_general')
    renderApp('/administrador_general/alta-usuario')
    await screen.findByRole('navigation', { name: 'Principal' })
    expect(screen.queryByRole('button', { name: 'Abrir chat' })).not.toBeInTheDocument()
  })

  it('envía la consulta y muestra la respuesta, con el aviso de que no da diagnósticos', async () => {
    startTestSession('paciente')
    const mock = mockApi({ [MESSAGES]: { body: BODY } })
    renderApp(PATH)
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
    renderApp(PATH)
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
    renderApp(PATH)
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
    renderApp(PATH)
    const user = userEvent.setup()

    await openChat(user)
    await typeAndSend(user, 'Hola')

    expect(await screen.findByRole('alert')).toHaveTextContent('muchas consultas')
  })

  it('se cierra con Escape', async () => {
    startTestSession('paciente')
    renderApp(PATH)
    const user = userEvent.setup()

    await openChat(user)
    expect(screen.getByRole('region', { name: 'Chatbot' })).toBeInTheDocument()
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('region', { name: 'Chatbot' })).not.toBeInTheDocument()
  })
})
