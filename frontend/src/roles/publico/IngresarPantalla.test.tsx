import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { mockApi, renderApp, sentTo, sessionResponse } from '../../test-utils'
import { readSession } from '../../lib/session'

const LOGIN = 'POST /acceso/login'
const VERIFY = 'POST /acceso/verify-code'
const CODE_SENT = { body: { state: 'code_sent', session: null, challenge: 'challenge-token' } }

async function submitCredentials(password = 'clave-segura') {
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('Mail'), 'medica@example.com')
  await user.type(screen.getByLabelText('Contraseña'), password)
  await user.click(screen.getByRole('button', { name: 'Ingresar' }))
  return user
}

describe('Ingresar al sistema', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
  })
  afterEach(() => vi.unstubAllGlobals())

  it('asks for the code on a new device and lets in with the right code', async () => {
    const mock = mockApi({
      [LOGIN]: CODE_SENT,
      [VERIFY]: { body: sessionResponse('medico_tratante') },
    })
    renderApp('/ingresar')
    const user = await submitCredentials()

    expect(await screen.findByText(/Te enviamos un código de verificación/)).toBeInTheDocument()
    await user.type(screen.getByLabelText('Código de verificación'), '123456')
    await user.click(screen.getByRole('button', { name: 'Verificar el código' }))

    expect(await screen.findByRole('heading', { name: 'Mis estudios' })).toBeInTheDocument()
    expect(readSession()).toMatchObject({ token: 'test-token', rol: 'medico_tratante' })

    const [credentials] = sentTo(mock, LOGIN)
    expect(credentials).toMatchObject({ email: 'medica@example.com', password: 'clave-segura' })
    expect(credentials.device_id).toEqual(expect.any(String))
    expect(sentTo(mock, VERIFY)[0]).toMatchObject({
      email: 'medica@example.com',
      code: '123456',
      challenge: 'challenge-token',
      device_id: credentials.device_id,
    })
  })

  it('goes straight in when the device and network are already known', async () => {
    mockApi({
      [LOGIN]: {
        body: {
          state: 'authenticated',
          session: sessionResponse('transportista'),
          challenge: null,
        },
      },
    })
    renderApp('/ingresar')
    await submitCredentials()

    expect(await screen.findByRole('heading', { name: 'Orden del día' })).toBeInTheDocument()
    expect(screen.queryByLabelText('Código de verificación')).toBeNull()
  })

  it('with wrong credentials it warns and does not ask for the code', async () => {
    mockApi({ [LOGIN]: { status: 401, body: { detalle: 'Credenciales inválidas.' } } })
    renderApp('/ingresar')
    await submitCredentials('bad')

    expect(await screen.findByRole('alert')).toHaveTextContent('Credenciales inválidas.')
    expect(screen.queryByLabelText('Código de verificación')).toBeNull()
    expect(readSession()).toBeNull()
  })

  it('says the account is blocked', async () => {
    mockApi({
      [LOGIN]: {
        status: 423,
        body: { detalle: 'Cuenta bloqueada por demasiados intentos fallidos.' },
      },
    })
    renderApp('/ingresar')
    await submitCredentials()

    expect(await screen.findByRole('alert')).toHaveTextContent('Cuenta bloqueada')
  })

  it('with a wrong code it warns and allows asking for a new one', async () => {
    const mock = mockApi({
      [LOGIN]: CODE_SENT,
      [VERIFY]: { status: 401, body: { detalle: 'Código inválido o vencido.' } },
    })
    renderApp('/ingresar')
    const user = await submitCredentials()

    await user.type(await screen.findByLabelText('Código de verificación'), '000000')
    await user.click(screen.getByRole('button', { name: 'Verificar el código' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Código inválido o vencido.')

    await user.click(screen.getByRole('button', { name: 'Pedir un código nuevo' }))
    await vi.waitFor(() => expect(sentTo(mock, LOGIN)).toHaveLength(2))
    expect(screen.getByLabelText('Código de verificación')).toBeInTheDocument()
  })

  it('"Volver" goes back to the credentials step', async () => {
    mockApi({ [LOGIN]: CODE_SENT })
    renderApp('/ingresar')
    const user = await submitCredentials()

    await user.click(await screen.findByRole('button', { name: 'Volver' }))
    expect(screen.getByLabelText('Contraseña')).toBeInTheDocument()
  })

  it('a patient with the initial password is sent to the password change', async () => {
    mockApi({
      [LOGIN]: {
        body: {
          state: 'authenticated',
          session: sessionResponse('paciente', true),
          challenge: null,
        },
      },
    })
    renderApp('/ingresar')
    await submitCredentials()

    expect(
      await screen.findByRole('heading', { name: 'Cambiar la contraseña' }),
    ).toBeInTheDocument()
    expect(readSession()?.mustChangePassword).toBe(true)
  })

  it('says a new code was sent when asking for another one', async () => {
    mockApi({ [LOGIN]: CODE_SENT })
    renderApp('/ingresar')
    const user = await submitCredentials()

    expect(await screen.findByText(/Te enviamos un código de verificación/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Pedir un código nuevo' }))

    expect(await screen.findByText(/Te enviamos un código nuevo/)).toBeInTheDocument()
  })

  it('shows the wait message when the new code is asked for too soon', async () => {
    let calls = 0
    mockApi({
      [LOGIN]: () =>
        ++calls === 1
          ? CODE_SENT
          : { status: 429, body: { detalle: 'Esperá un momento antes de pedir otro código.' } },
    })
    renderApp('/ingresar')
    const user = await submitCredentials()

    await user.click(await screen.findByRole('button', { name: 'Pedir un código nuevo' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Esperá un momento')
    expect(screen.getByLabelText('Código de verificación')).toBeInTheDocument()
  })
})
