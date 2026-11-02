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

  describe('DEV auth bypass', () => {
    afterEach(() => {
      localStorage.clear()
      vi.unstubAllEnvs()
    })

    it('sends the role chosen in the DEV selector when there is no session', async () => {
      localStorage.setItem('genlab.rol-dev', 'gerente_medico')
      const mock = mockApi({ 'GET /something': { body: {} } })
      await api('/something')
      expect(mock.mock.calls[0][1]?.headers).toMatchObject({ 'X-Dev-Role': 'gerente_medico' })
      expect(mock.mock.calls[0][1]?.headers).not.toHaveProperty('X-Dev-User')
    })

    it('uses the same default role as the selector and ignores an unknown one', async () => {
      localStorage.setItem('genlab.rol-dev', 'superusuario')
      const mock = mockApi({ 'GET /something': { body: {} } })
      await api('/something')
      expect(mock.mock.calls[0][1]?.headers).toMatchObject({ 'X-Dev-Role': 'paciente' })
    })

    it('also sends X-Dev-User when one was chosen', async () => {
      localStorage.setItem('genlab.rol-dev', 'paciente')
      localStorage.setItem('genlab.user-dev', 'martin.gomez@example.com')
      const mock = mockApi({ 'GET /something': { body: {} } })
      await api('/something')
      expect(mock.mock.calls[0][1]?.headers).toMatchObject({
        'X-Dev-Role': 'paciente',
        'X-Dev-User': 'martin.gomez@example.com',
      })
    })

    it('sends nothing when there is a real session', async () => {
      localStorage.setItem('genlab.rol-dev', 'gerente_medico')
      saveSession({ token: 'abc', rol: 'paciente', mustChangePassword: false })
      const mock = mockApi({ 'GET /something': { body: {} } })
      await api('/something')
      expect(mock.mock.calls[0][1]?.headers).not.toHaveProperty('X-Dev-Role')
    })

    it('sends nothing in a production build', async () => {
      vi.stubEnv('DEV', false)
      localStorage.setItem('genlab.rol-dev', 'gerente_medico')
      const mock = mockApi({ 'GET /something': { body: {} } })
      await api('/something')
      expect(mock.mock.calls[0][1]?.headers).not.toHaveProperty('X-Dev-Role')
    })
  })
})
