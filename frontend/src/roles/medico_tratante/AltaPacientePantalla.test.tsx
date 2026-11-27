import { fireEvent, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { isMinor, validatePatient, EMPTY_PATIENT_FORM } from '../../lib/patients'
import { mockApi, renderApp, sentTo, startTestSession } from '../../test-utils'

const FIND = 'GET /consulta_medica/patients'
const CREATE = 'POST /consulta_medica/patients'
const PATHOLOGIES = 'GET /config_medica/pathologies'
const SEARCH = 'GET /consulta_medica/symptoms'

const PAIN = { code: 'SIM-001', term: 'Dolor' }
const FABRY = { id: 1, name: 'Fabry', cardinal: PAIN, secondary: [] }
const CREATED = {
  id: 'p-1',
  dni: '30123456',
  first_name: 'Ana',
  last_name: 'Pérez',
  birth_date: '1990-05-20',
  account_created: true,
}

function routes(overrides: Record<string, never> = {}) {
  return {
    [PATHOLOGIES]: { body: [FABRY] },
    [FIND]: { status: 404, body: { detalle: 'No hay un paciente registrado con ese DNI.' } },
    [SEARCH]: { body: { items: [PAIN], page: 1, has_more: false } },
    [CREATE]: { status: 201, body: CREATED },
    ...overrides,
  }
}

async function searchUnknownDni(user: ReturnType<typeof userEvent.setup>) {
  await user.type(await screen.findByLabelText('DNI del paciente'), '30123456')
  await user.click(screen.getByRole('button', { name: 'Buscar paciente' }))
  await screen.findByText(/No hay un paciente con ese DNI/)
}

async function fillPersonalData(
  user: ReturnType<typeof userEvent.setup>,
  birthDate = '1990-05-20',
) {
  await user.type(screen.getByLabelText('Nombre'), 'Ana')
  await user.type(screen.getByLabelText('Apellido'), 'Pérez')
  fireEvent.change(screen.getByLabelText('Fecha de nacimiento'), { target: { value: birthDate } })
  await user.click(screen.getByRole('radio', { name: 'Mujer' }))
  await user.type(screen.getByLabelText('Teléfono'), '2215550000')
  await user.type(screen.getByLabelText(/^Mail/), 'ana@ejemplo.com')
  await user.type(screen.getByLabelText('Resumen de historia clínica'), 'Dolor en manos.')
  await user.click(await screen.findByRole('checkbox', { name: 'Fabry' }))
}

describe('AltaPacientePantalla', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    startTestSession('medico_tratante')
  })
  afterEach(() => vi.unstubAllGlobals())

  it('asks for the DNI first and shows the form when the patient does not exist', async () => {
    mockApi(routes())
    const user = userEvent.setup()
    renderApp('/medico_tratante/alta-paciente')

    expect(screen.queryByLabelText('Apellido')).not.toBeInTheDocument()
    await searchUnknownDni(user)

    expect(screen.getByLabelText('Apellido')).toBeInTheDocument()
  })

  it('shows the patient and a link to the study when the DNI already exists', async () => {
    mockApi(
      routes({
        [FIND]: { body: { ...CREATED } } as never,
      }),
    )
    const user = userEvent.setup()
    renderApp('/medico_tratante/alta-paciente')

    await user.type(await screen.findByLabelText('DNI del paciente'), '30123456')
    await user.click(screen.getByRole('button', { name: 'Buscar paciente' }))

    expect(
      await screen.findByText(/Este paciente ya está registrado: Ana Pérez/),
    ).toBeInTheDocument()
    const links = screen.getAllByRole('link', { name: 'Dar de alta el estudio' })
    expect(links.map((link) => link.getAttribute('href'))).toContain(
      '/medico_tratante/alta-estudio?dni=30123456',
    )
    const familyLinks = screen.getAllByRole('link', { name: 'Cargar familiares' })
    expect(familyLinks.map((link) => link.getAttribute('href'))).toContain(
      '/medico_tratante/familiograma?dni=30123456',
    )
    expect(screen.queryByLabelText('Apellido')).not.toBeInTheDocument()
  })

  it('does not search with an invalid DNI', async () => {
    const mock = mockApi(routes())
    const user = userEvent.setup()
    renderApp('/medico_tratante/alta-paciente')

    await user.type(await screen.findByLabelText('DNI del paciente'), '123')
    await user.click(screen.getByRole('button', { name: 'Buscar paciente' }))

    expect(await screen.findByText('El DNI tiene que tener 7 u 8 dígitos.')).toBeInTheDocument()
    expect(mock.mock.calls.some(([url]) => String(url).includes('/consulta_medica/patients'))).toBe(
      false,
    )
  })

  it('creates the patient with a clinical suspicion and says the credentials were sent', async () => {
    const mock = mockApi(routes())
    const user = userEvent.setup()
    renderApp('/medico_tratante/alta-paciente')

    await searchUnknownDni(user)
    await fillPersonalData(user)
    await user.click(screen.getByRole('radio', { name: 'Clínica' }))
    await user.type(screen.getByLabelText('Buscar síntomas del paciente'), 'dol')
    await user.click(await screen.findByRole('button', { name: 'Dolor' }))
    await user.click(screen.getByRole('button', { name: 'Dar de alta al paciente' }))

    expect(await screen.findByText(/Se dio de alta a Ana Pérez/)).toBeInTheDocument()
    expect(screen.getByText(/Se enviaron las credenciales a ana@ejemplo.com/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Cargar familiares' })).toHaveAttribute(
      'href',
      '/medico_tratante/familiograma?dni=30123456',
    )
    expect(sentTo(mock, CREATE)).toEqual([
      {
        dni: '30123456',
        first_name: 'Ana',
        last_name: 'Pérez',
        birth_date: '1990-05-20',
        sex: 'mujer',
        phone: '2215550000',
        email: 'ana@ejemplo.com',
        suspicion_type: 'clinica',
        pathology_ids: [1],
        clinical_summary: 'Dolor en manos.',
        symptoms: [PAIN],
      },
    ])
    // It types a lot with userEvent: on a slow machine (CI) the default 5 s is not always enough.
  }, 20_000)

  it('lets a familial suspicion go without symptoms', async () => {
    const mock = mockApi(routes())
    const user = userEvent.setup()
    renderApp('/medico_tratante/alta-paciente')

    await searchUnknownDni(user)
    await fillPersonalData(user)
    await user.click(screen.getByRole('radio', { name: 'Familiar' }))
    await user.click(screen.getByRole('button', { name: 'Dar de alta al paciente' }))

    expect(await screen.findByText(/Se dio de alta a Ana Pérez/)).toBeInTheDocument()
    expect(sentTo(mock, CREATE)[0].symptoms).toEqual([])
  })

  it('does not send a clinical suspicion without symptoms', async () => {
    const mock = mockApi(routes())
    const user = userEvent.setup()
    renderApp('/medico_tratante/alta-paciente')

    await searchUnknownDni(user)
    await fillPersonalData(user)
    await user.click(screen.getByRole('radio', { name: 'Clínica' }))
    await user.click(screen.getByRole('button', { name: 'Dar de alta al paciente' }))

    expect(
      await screen.findByText('En una sospecha clínica cargá al menos un síntoma.'),
    ).toBeInTheDocument()
    expect(sentTo(mock, CREATE)).toEqual([])
  })

  it('moves the focus to a summary of the errors and links each error to its field', async () => {
    mockApi(routes())
    const user = userEvent.setup()
    renderApp('/medico_tratante/alta-paciente')

    await searchUnknownDni(user)
    await user.click(screen.getByRole('button', { name: 'Dar de alta al paciente' }))

    const summary = await screen.findByText(/campos para corregir/)
    expect(summary).toHaveFocus()
    const errorOfSummary = await screen.findByText('Completá el resumen de historia clínica.')
    expect(screen.getByLabelText('Resumen de historia clínica')).toHaveAccessibleDescription(
      errorOfSummary.textContent ?? '',
    )
    expect(screen.getByRole('group', { name: 'Tipo de sospecha' })).toHaveAccessibleDescription(
      'Elegí el tipo de sospecha.',
    )
  })

  it('limits the length of the texts the doctor can type', async () => {
    mockApi(routes())
    const user = userEvent.setup()
    renderApp('/medico_tratante/alta-paciente')

    await searchUnknownDni(user)

    expect(screen.getByLabelText('Nombre')).toHaveAttribute('maxlength', '100')
    expect(screen.getByLabelText('Teléfono')).toHaveAttribute('maxlength', '30')
    expect(screen.getByLabelText('Resumen de historia clínica')).toHaveAttribute(
      'maxlength',
      '5000',
    )
  })

  it('asks for the mail of the parents when the patient is a minor', async () => {
    mockApi(routes())
    const user = userEvent.setup()
    renderApp('/medico_tratante/alta-paciente')

    await searchUnknownDni(user)
    expect(screen.getByLabelText('Mail')).toBeInTheDocument()

    const year = new Date().getFullYear() - 5
    fireEvent.change(screen.getByLabelText('Fecha de nacimiento'), {
      target: { value: `${year}-01-01` },
    })

    expect(screen.getByLabelText('Mail del padre o madre')).toBeInTheDocument()
  })

  it('keeps what was typed and shows the message when the server blocks the alta', async () => {
    mockApi(
      routes({
        [CREATE]: {
          status: 422,
          body: { detalle: 'Los síntomas cargados no corresponden a la patología sospechada.' },
        } as never,
      }),
    )
    const user = userEvent.setup()
    renderApp('/medico_tratante/alta-paciente')

    await searchUnknownDni(user)
    await fillPersonalData(user)
    await user.click(screen.getByRole('radio', { name: 'Familiar' }))
    await user.click(screen.getByRole('button', { name: 'Dar de alta al paciente' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('no corresponden a la patología')
    expect(screen.getByLabelText('Nombre')).toHaveValue('Ana')
  })

  it('says no credentials were sent when the account already existed', async () => {
    mockApi(
      routes({ [CREATE]: { status: 201, body: { ...CREATED, account_created: false } } as never }),
    )
    const user = userEvent.setup()
    renderApp('/medico_tratante/alta-paciente')

    await searchUnknownDni(user)
    await fillPersonalData(user)
    await user.click(screen.getByRole('radio', { name: 'Familiar' }))
    await user.click(screen.getByRole('button', { name: 'Dar de alta al paciente' }))

    expect(await screen.findByText(/no se enviaron credenciales nuevas/)).toBeInTheDocument()
  })
})

describe('isMinor', () => {
  const today = new Date('2026-11-14T12:00:00')

  it('is a minor the day before the 18th birthday', () => {
    expect(isMinor('2008-11-15', today)).toBe(true)
  })

  it('is an adult on the 18th birthday', () => {
    expect(isMinor('2008-11-14', today)).toBe(false)
  })

  it('does not break with an empty date', () => {
    expect(isMinor('', today)).toBe(false)
  })
})

describe('validatePatient', () => {
  it('rejects a future birth date', () => {
    const form = { ...EMPTY_PATIENT_FORM, birthDate: '2030-01-01' }

    expect(validatePatient(form, new Date('2026-11-14T12:00:00')).birthDate).toMatch(/futura/)
  })
})
