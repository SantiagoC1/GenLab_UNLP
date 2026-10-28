import { api, SESSION_EXPIRED_EVENT } from './api'
import { clearSession, readSession, saveSession } from './session'
import { mockApi } from '../test-utils'

describe('api', () => {
  beforeEach(() => clearSession())
  afterEach(() => vi.unstubAllGlobals())

  it('sends the session token', async () => {
    saveSession({ token: 'abc', rol: 'paciente', mustChangePassword: false })
    const mock = mockApi({ 'GET /something': { body: {} } })
    await api('/something')
    expect(mock.mock.calls[0][1]?.headers).toMatchObject({ Authorization: 'Bearer abc' })
  })

  it('does not send Authorization without a session', async () => {
    const mock = mockApi({ 'GET /something': { body: {} } })
    await api('/something')
    expect(mock.mock.calls[0][1]?.headers).not.toHaveProperty('Authorization')
  })

  it('ends the session and notifies when the backend says it expired', async () => {
    saveSession({ token: 'abc', rol: 'paciente', mustChangePassword: false })
    mockApi({
      'GET /something': {
        status: 401,
        body: { detalle: 'Sesión inválida o vencida.', code: 'invalid_session' },
      },
    })
    const listener = vi.fn()
    window.addEventListener(SESSION_EXPIRED_EVENT, listener)
    await expect(api('/something')).rejects.toThrow('Sesión inválida o vencida.')
    window.removeEventListener(SESSION_EXPIRED_EVENT, listener)
    expect(readSession()).toBeNull()
    expect(listener).toHaveBeenCalledOnce()
  })

  it('a plain 401 (wrong credentials) does not end the session', async () => {
    saveSession({ token: 'abc', rol: 'paciente', mustChangePassword: false })
    mockApi({ 'GET /something': { status: 401, body: { detalle: 'Credenciales inválidas.' } } })
    await expect(api('/something')).rejects.toThrow('Credenciales inválidas.')
    expect(readSession()).not.toBeNull()
  })
})
