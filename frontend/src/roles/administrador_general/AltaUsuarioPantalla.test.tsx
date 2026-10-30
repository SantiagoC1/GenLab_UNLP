import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { mockApi, renderApp, sentTo, startTestSession } from '../../test-utils'

const PATH = '/administrador_general/alta-usuario'
const CREATE = 'POST /acceso/users'
const CATALOGS = {
  body: {
    specialties: [{ id: 1, name: 'Genética médica' }],
    provinces: ['Córdoba', 'Santa Fe'],
  },
}
const ADMIN = {
  id: '1',
  first_name: 'Ana',
  last_name: 'Gómez',
  email: 'admin@example.com',
  phone: '221',
  role: 'administrador_general',
  province: null,
  license_number: null,
  blocked: false,
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
})
beforeEach(() => {
  localStorage.clear()
  sessionStorage.clear()
  startTestSession('administrador_general')
})

async function openForm() {
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: 'Nuevo usuario' }))
  return user
}

async function fillCarrier(user: ReturnType<typeof userEvent.setup>) {
  await user.selectOptions(screen.getByLabelText('Rol'), 'transportista')
  await user.type(screen.getByLabelText('Nombre'), 'Pedro')
  await user.type(screen.getByLabelText('Apellido'), 'Díaz')
  await user.type(screen.getByLabelText('Teléfono de contacto'), '3425550000')
  await user.type(screen.getByLabelText('Mail'), 'pedro@example.com')
  await user.selectOptions(screen.getByLabelText('Provincia que cubre'), 'Santa Fe')
}

describe('Dar de alta a un usuario', () => {
  it('shows the list of users', async () => {
    mockApi({ 'GET /acceso/users': { body: [ADMIN] }, 'GET /acceso/catalogs': CATALOGS })
    renderApp(PATH)

    const row = (await screen.findByText('Gómez, Ana')).closest('tr')!
    expect(within(row).getByText('admin@example.com')).toBeInTheDocument()
    expect(within(row).getByText('Administrador general')).toBeInTheDocument()
    expect(within(row).getByText('Activo')).toBeInTheDocument()
  })

  it('offers every role except the patient and the general administrator', async () => {
    mockApi({ 'GET /acceso/users': { body: [] }, 'GET /acceso/catalogs': CATALOGS })
    renderApp(PATH)
    await openForm()

    const roles = screen.getAllByRole('option').map((o) => o.textContent)
    expect(roles).toEqual([
      'Elegí un rol',
      'Médico tratante',
      'Administrativo del laboratorio',
      'Bioinformático',
      'Transportista',
      'Gerente médico',
    ])
  })

  it('the carrier must give the province they cover', async () => {
    const mock = mockApi({ 'GET /acceso/users': { body: [] }, 'GET /acceso/catalogs': CATALOGS })
    renderApp(PATH)
    const user = await openForm()
    expect(screen.queryByLabelText('Provincia que cubre')).toBeNull()

    await user.selectOptions(screen.getByLabelText('Rol'), 'transportista')
    await user.click(screen.getByRole('button', { name: 'Guardar el alta' }))

    expect(screen.getByText('Elegí la provincia que cubre.')).toBeInTheDocument()
    expect(sentTo(mock, CREATE)).toHaveLength(0)
  })

  it('saves the creation, says credentials were sent and refreshes the list', async () => {
    let users: Record<string, unknown>[] = [ADMIN]
    const mock = mockApi({
      'GET /acceso/users': () => ({ body: users }),
      'GET /acceso/catalogs': CATALOGS,
      [CREATE]: () => {
        const created = {
          ...ADMIN,
          id: '2',
          first_name: 'Pedro',
          last_name: 'Díaz',
          email: 'pedro@example.com',
          role: 'transportista',
          province: 'Santa Fe',
        }
        users = [...users, created]
        return { status: 201, body: created }
      },
    })
    renderApp(PATH)
    const user = await openForm()
    await fillCarrier(user)
    await user.click(screen.getByRole('button', { name: 'Guardar el alta' }))

    expect(
      await screen.findByText(/Enviamos las credenciales de acceso a pedro@example.com/),
    ).toBeInTheDocument()
    expect(await screen.findByText('Díaz, Pedro')).toBeInTheDocument()
    expect(sentTo(mock, CREATE)[0]).toEqual({
      role: 'transportista',
      first_name: 'Pedro',
      last_name: 'Díaz',
      phone: '3425550000',
      email: 'pedro@example.com',
      province: 'Santa Fe',
    })
  })

  it('says when there is already a carrier in that province', async () => {
    mockApi({
      'GET /acceso/users': { body: [] },
      'GET /acceso/catalogs': CATALOGS,
      [CREATE]: { status: 409, body: { detalle: 'Ya hay un transportista para Santa Fe.' } },
    })
    renderApp(PATH)
    const user = await openForm()
    await fillCarrier(user)
    await user.click(screen.getByRole('button', { name: 'Guardar el alta' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Ya hay un transportista para Santa Fe.',
    )
    // the form stays open with what was filled in: no work is lost
    expect(screen.getByLabelText('Nombre')).toHaveValue('Pedro')
  })

  it('lets the admin unblock a blocked account and refreshes the list', async () => {
    const PEDRO = {
      ...ADMIN,
      id: '2',
      first_name: 'Pedro',
      last_name: 'Díaz',
      email: 'pedro@example.com',
      role: 'transportista',
      province: 'Santa Fe',
    }
    let blocked = true
    const UNBLOCK = 'POST /acceso/users/2/unblock'
    const mock = mockApi({
      'GET /acceso/users': () => ({ body: [ADMIN, { ...PEDRO, blocked }] }),
      'GET /acceso/catalogs': CATALOGS,
      [UNBLOCK]: () => {
        blocked = false
        return { body: PEDRO }
      },
    })
    renderApp(PATH)

    const row = (await screen.findByText('Díaz, Pedro')).closest('tr')!
    expect(within(row).getByText('Bloqueado')).toBeInTheDocument()
    // solo las cuentas bloqueadas ofrecen la acción
    expect(screen.getAllByRole('button', { name: 'Desbloquear' })).toHaveLength(1)

    await userEvent.click(within(row).getByRole('button', { name: 'Desbloquear' }))

    expect(
      await screen.findByText(/Desbloqueamos la cuenta de pedro@example.com/),
    ).toBeInTheDocument()
    await vi.waitFor(() => expect(screen.queryByRole('button', { name: 'Desbloquear' })).toBeNull())
    expect(sentTo(mock, UNBLOCK)).toHaveLength(1)
  })
})
