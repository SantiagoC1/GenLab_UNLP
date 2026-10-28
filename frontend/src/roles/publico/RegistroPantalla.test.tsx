import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { mockApi, renderApp, sentTo, sessionResponse } from '../../test-utils'

const CATALOGS = {
  body: {
    specialties: [
      { id: 1, name: 'Genética médica' },
      { id: 2, name: 'Pediatría' },
    ],
    provinces: ['Buenos Aires', 'Santa Fe'],
  },
}
const REGISTER = 'POST /acceso/register'

async function fillCommonData(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText('Nombre'), '  Lucía ')
  await user.type(screen.getByLabelText('Apellido'), 'Pérez')
  await user.type(screen.getByLabelText('Teléfono de contacto'), '2215550000')
  await user.type(screen.getByLabelText('Mail'), 'Lucia@Example.com')
  await user.type(screen.getByLabelText('Contraseña'), 'una-clave-larga')
}

describe('Registrarse', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
  })
  afterEach(() => vi.unstubAllGlobals())

  it('does not allow sending with missing required data', async () => {
    const mock = mockApi({ 'GET /acceso/catalogs': CATALOGS })
    renderApp('/registro')
    await userEvent.click(screen.getByRole('button', { name: 'Registrarme' }))

    expect(screen.getByText('Elegí un rol.')).toBeInTheDocument()
    expect(screen.getByText('Completá el nombre.')).toBeInTheDocument()
    expect(screen.getByText('Completá el mail.')).toBeInTheDocument()
    expect(screen.getByText('Definí una contraseña.')).toBeInTheDocument()
    expect(sentTo(mock, REGISTER)).toHaveLength(0)
  })

  it('only offers the roles that sign up on their own', () => {
    mockApi({ 'GET /acceso/catalogs': CATALOGS })
    renderApp('/registro')
    const roles = screen.getAllByRole('option').map((o) => o.textContent)
    expect(roles).toEqual([
      'Elegí un rol',
      'Médico tratante',
      'Administrativo del laboratorio',
      'Bioinformático',
    ])
  })

  it('the treating doctor also fills in license number and specialties', async () => {
    const mock = mockApi({ 'GET /acceso/catalogs': CATALOGS })
    renderApp('/registro')
    const user = userEvent.setup()
    expect(screen.queryByLabelText('Matrícula')).toBeNull()

    await user.selectOptions(screen.getByLabelText('Rol'), 'medico_tratante')
    await fillCommonData(user)
    await user.click(screen.getByRole('button', { name: 'Registrarme' }))

    expect(screen.getByText('Completá la matrícula.')).toBeInTheDocument()
    expect(screen.getByText('Elegí al menos una especialidad.')).toBeInTheDocument()
    expect(sentTo(mock, REGISTER)).toHaveLength(0)
  })

  it('rejects a short password', async () => {
    mockApi({ 'GET /acceso/catalogs': CATALOGS })
    renderApp('/registro')
    await userEvent.type(screen.getByLabelText('Contraseña'), 'corta')
    await userEvent.click(screen.getByRole('button', { name: 'Registrarme' }))
    expect(screen.getByText('La contraseña debe tener al menos 8 caracteres.')).toBeInTheDocument()
  })

  it('registers the doctor and takes them to the view of their role', async () => {
    const mock = mockApi({
      'GET /acceso/catalogs': CATALOGS,
      [REGISTER]: { status: 201, body: sessionResponse('medico_tratante') },
    })
    renderApp('/registro')
    const user = userEvent.setup()

    await user.selectOptions(screen.getByLabelText('Rol'), 'medico_tratante')
    await fillCommonData(user)
    await user.type(screen.getByLabelText('Matrícula'), 'MP 12345')
    await user.click(await screen.findByLabelText('Genética médica'))
    await user.click(screen.getByRole('button', { name: 'Registrarme' }))

    expect(await screen.findByRole('heading', { name: 'Mis estudios' })).toBeInTheDocument()
    expect(sentTo(mock, REGISTER)[0]).toMatchObject({
      role: 'medico_tratante',
      first_name: 'Lucía',
      last_name: 'Pérez',
      phone: '2215550000',
      email: 'lucia@example.com',
      password: 'una-clave-larga',
      license_number: 'MP 12345',
      specialties: [1],
    })
  })

  it('the bioinformatician signs up without license number or specialties', async () => {
    const mock = mockApi({
      'GET /acceso/catalogs': CATALOGS,
      [REGISTER]: { status: 201, body: sessionResponse('bioinformatico') },
    })
    renderApp('/registro')
    const user = userEvent.setup()

    await user.selectOptions(screen.getByLabelText('Rol'), 'bioinformatico')
    await fillCommonData(user)
    await user.click(screen.getByRole('button', { name: 'Registrarme' }))

    expect(await screen.findByRole('heading', { name: 'Estudios disponibles' })).toBeInTheDocument()
    const [sent] = sentTo(mock, REGISTER)
    expect(sent).not.toHaveProperty('license_number')
    expect(sent).not.toHaveProperty('specialties')
  })

  it('says the mail is already registered', async () => {
    mockApi({
      'GET /acceso/catalogs': CATALOGS,
      [REGISTER]: { status: 409, body: { detalle: 'Ya existe un usuario con ese mail.' } },
    })
    renderApp('/registro')
    const user = userEvent.setup()

    await user.selectOptions(screen.getByLabelText('Rol'), 'bioinformatico')
    await fillCommonData(user)
    await user.click(screen.getByRole('button', { name: 'Registrarme' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Ya existe un usuario con ese mail.')
  })
})
