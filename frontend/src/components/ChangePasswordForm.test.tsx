import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { readSession } from '../lib/session'
import { mockApi, renderApp, sentTo, startTestSession } from '../test-utils'

const CHANGE = 'POST /acceso/change-password'

async function fillIn(newPassword: string, confirmation: string) {
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('Contraseña actual'), 'inicial-123')
  await user.type(screen.getByLabelText('Contraseña nueva'), newPassword)
  await user.type(screen.getByLabelText('Repetí la contraseña nueva'), confirmation)
  await user.click(screen.getByRole('button', { name: 'Guardar la contraseña' }))
}

describe('Cambiar la contraseña', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    startTestSession('paciente')
  })
  afterEach(() => vi.unstubAllGlobals())

  it('when the passwords do not match it warns, empties the new ones and sends nothing', async () => {
    const mock = mockApi({})
    renderApp('/cambiar-contrasena')
    await fillIn('nueva-clave-1', 'otra-clave-2')

    expect(screen.getByText('Las contraseñas no coinciden.')).toBeInTheDocument()
    expect(screen.getByLabelText('Contraseña nueva')).toHaveValue('')
    expect(screen.getByLabelText('Repetí la contraseña nueva')).toHaveValue('')
    expect(screen.getByLabelText('Contraseña actual')).toHaveValue('inicial-123')
    expect(sentTo(mock, CHANGE)).toHaveLength(0)
  })

  it('with matching passwords it saves and lifts the initial password block', async () => {
    const mock = mockApi({ [CHANGE]: { body: { state: 'password_changed' } } })
    renderApp('/cambiar-contrasena')
    await fillIn('nueva-clave-1', 'nueva-clave-1')

    await vi.waitFor(() => expect(sentTo(mock, CHANGE)).toHaveLength(1))
    expect(sentTo(mock, CHANGE)[0]).toEqual({
      current_password: 'inicial-123',
      new_password: 'nueva-clave-1',
      confirmation: 'nueva-clave-1',
    })
    await vi.waitFor(() => expect(readSession()?.mustChangePassword).toBe(false))
  })
})
