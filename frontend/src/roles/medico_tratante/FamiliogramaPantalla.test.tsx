import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  emptyRelativeForm,
  relativeToForm,
  toPayload,
  validateRelative,
  type Relative,
} from '../../lib/familiograma'
import { mockApi, renderApp, sentTo, startTestSession } from '../../test-utils'

const FIND = 'GET /consulta_medica/patients'
const KINSHIPS = 'GET /familiograma/kinships'
const PATHOLOGIES = 'GET /config_medica/pathologies'
const RELATIVES = 'GET /familiograma/patients/p-1/relatives'
const SAVE = 'PUT /familiograma/patients/p-1/relatives'
const TREE = 'GET /familiograma/patients/p-1/family-tree'

const PATIENT = {
  id: 'p-1',
  dni: '30123456',
  first_name: 'Tomás',
  last_name: 'Ruiz',
  birth_date: '2017-05-20',
}
const FABRY = { id: 1, name: 'Fabry', code: 'FABRY', cardinal: null, secondary: [] }
const MOTHER: Relative = {
  kinship_id: 1,
  first_name: 'Carolina',
  last_name: 'Ruiz',
  dni: null,
  linked_patient_id: null,
  sex: 'mujer',
  age: 36,
  deceased: false,
  symptoms: [],
  pathologies: [{ id: 1, code: 'FABRY', name: 'Fabry' }],
}

function routes(overrides: Record<string, unknown> = {}) {
  return {
    [FIND]: { body: PATIENT },
    [KINSHIPS]: {
      body: [
        { id: 1, name: 'progenitor' },
        { id: 2, name: 'hermano/a' },
      ],
    },
    [PATHOLOGIES]: { body: [FABRY] },
    [RELATIVES]: { body: [] },
    [SAVE]: { body: [MOTHER] },
    [TREE]: { body: { warnings: [], svg_base64: 'PHN2Zz4=' } },
    ...overrides,
  } as Parameters<typeof mockApi>[0]
}

async function fillRelative(user: ReturnType<typeof userEvent.setup>) {
  const relative = await screen.findByRole('group', { name: 'Familiar 1' })
  await user.selectOptions(within(relative).getByLabelText('Parentesco'), 'progenitor')
  await user.type(within(relative).getByLabelText('Nombre'), 'Carolina')
  await user.type(within(relative).getByLabelText('Apellido'), 'Ruiz')
  await user.type(within(relative).getByLabelText('DNI (opcional)'), '20111222')
  await user.click(within(relative).getByRole('radio', { name: 'Mujer' }))
  await user.type(within(relative).getByLabelText(/^Edad/), '36')
  await user.click(within(relative).getByRole('checkbox', { name: 'Fabry' }))
}

describe('FamiliogramaPantalla', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    startTestSession('medico_tratante')
  })
  afterEach(() => vi.unstubAllGlobals())

  it('loads the patient from the DNI in the address and shows the saved relatives', async () => {
    mockApi(routes({ [RELATIVES]: { body: [MOTHER] } }))
    renderApp('/medico_tratante/familiograma?dni=30123456')

    expect(await screen.findByText(/Paciente: Tomás Ruiz/)).toBeInTheDocument()
    const relative = screen.getByRole('group', { name: 'Familiar 1' })
    expect(within(relative).getByLabelText('Nombre')).toHaveValue('Carolina')
    expect(await within(relative).findByRole('checkbox', { name: 'Fabry' })).toBeChecked()
  })

  it('does not offer the patient as a kinship', async () => {
    mockApi(routes())
    const user = userEvent.setup()
    renderApp('/medico_tratante/familiograma?dni=30123456')

    await user.click(await screen.findByRole('button', { name: 'Agregar familiar' }))

    const options = screen.getAllByRole('option').map((option) => option.textContent)
    expect(options).toEqual(['Elegí un parentesco', 'progenitor', 'hermano/a'])
  })

  it('says so when there is no patient with that DNI', async () => {
    mockApi(routes({ [FIND]: { status: 404, body: { detalle: 'No existe' } } }))
    renderApp('/medico_tratante/familiograma?dni=30123456')

    expect(
      await screen.findByText('No hay un paciente registrado con ese DNI.'),
    ).toBeInTheDocument()
  })

  it('rejects a DNI with a wrong format without asking the server', async () => {
    const mock = mockApi(routes())
    const user = userEvent.setup()
    renderApp('/medico_tratante/familiograma')

    await user.type(await screen.findByLabelText('DNI del paciente'), '123')
    await user.click(screen.getByRole('button', { name: 'Buscar paciente' }))

    expect(await screen.findByText('El DNI tiene que tener 7 u 8 dígitos.')).toBeInTheDocument()
    expect(sentTo(mock, FIND)).toEqual([])
  })

  it('shows what is missing when a relative is incomplete', async () => {
    const mock = mockApi(routes())
    const user = userEvent.setup()
    renderApp('/medico_tratante/familiograma?dni=30123456')

    await user.click(await screen.findByRole('button', { name: 'Agregar familiar' }))
    await user.click(screen.getByRole('button', { name: 'Guardar familiares' }))

    expect(await screen.findByText(/Hay 1 familiar para corregir/)).toBeInTheDocument()
    expect(screen.getByText('Elegí el parentesco.')).toBeInTheDocument()
    expect(screen.getByText('Completá el nombre.')).toBeInTheDocument()
    expect(screen.getByText('Elegí el sexo.')).toBeInTheDocument()
    expect(sentTo(mock, SAVE)).toEqual([])
  })

  it('saves the relatives with the names of the API', async () => {
    const mock = mockApi(routes())
    const user = userEvent.setup()
    renderApp('/medico_tratante/familiograma?dni=30123456')

    await user.click(await screen.findByRole('button', { name: 'Agregar familiar' }))
    await fillRelative(user)
    await user.click(screen.getByRole('button', { name: 'Guardar familiares' }))

    expect(await screen.findByText('Se guardaron los familiares.')).toBeInTheDocument()
    expect(sentTo(mock, SAVE)).toEqual([
      {
        relatives: [
          {
            kinship_id: 1,
            first_name: 'Carolina',
            last_name: 'Ruiz',
            dni: '20111222',
            sex: 'mujer',
            age: 36,
            deceased: false,
            symptoms: [],
            pathology_ids: [1],
          },
        ],
      },
    ])
    expect(sentTo(mock, TREE)).toEqual([])
  })

  it('says when the DNI of a saved relative is already a patient', async () => {
    mockApi(
      routes({
        [RELATIVES]: { body: [{ ...MOTHER, dni: '20111222', linked_patient_id: 'p-9' }] },
      }),
    )
    renderApp('/medico_tratante/familiograma?dni=30123456')

    expect(await screen.findByText('Ya es paciente de GenLab.')).toBeInTheDocument()
  })

  it('does not say it when the relative is not a patient', async () => {
    mockApi(routes({ [RELATIVES]: { body: [{ ...MOTHER, dni: '20111222' }] } }))
    renderApp('/medico_tratante/familiograma?dni=30123456')

    expect(await screen.findByLabelText('DNI (opcional)')).toHaveValue('20111222')
    expect(screen.queryByText('Ya es paciente de GenLab.')).not.toBeInTheDocument()
  })

  it('shows the link after saving a DNI that belongs to a patient', async () => {
    mockApi(
      routes({
        [SAVE]: { body: [{ ...MOTHER, dni: '20111222', linked_patient_id: 'p-9' }] },
      }),
    )
    const user = userEvent.setup()
    renderApp('/medico_tratante/familiograma?dni=30123456')

    await user.click(await screen.findByRole('button', { name: 'Agregar familiar' }))
    await fillRelative(user)
    await user.click(screen.getByRole('button', { name: 'Guardar familiares' }))

    expect(await screen.findByText('Ya es paciente de GenLab.')).toBeInTheDocument()
  })

  it('rejects a DNI with a wrong format without sending', async () => {
    const mock = mockApi(routes())
    const user = userEvent.setup()
    renderApp('/medico_tratante/familiograma?dni=30123456')

    await user.click(await screen.findByRole('button', { name: 'Agregar familiar' }))
    await fillRelative(user)
    const dni = screen.getByLabelText('DNI (opcional)')
    await user.clear(dni)
    await user.type(dni, '123')
    await user.click(screen.getByRole('button', { name: 'Guardar familiares' }))

    expect(await screen.findByText('El DNI tiene que tener 7 u 8 dígitos.')).toBeInTheDocument()
    expect(sentTo(mock, SAVE)).toEqual([])
  })

  it('removes a relative from the list', async () => {
    mockApi(routes({ [RELATIVES]: { body: [MOTHER] } }))
    const user = userEvent.setup()
    renderApp('/medico_tratante/familiograma?dni=30123456')

    await user.click(await screen.findByRole('button', { name: 'Quitar al familiar 1' }))

    expect(screen.queryByRole('group', { name: 'Familiar 1' })).not.toBeInTheDocument()
    expect(screen.getByText('Todavía no cargaste familiares.')).toBeInTheDocument()
  })

  it('saves and shows the family tree as an image with a text alternative', async () => {
    mockApi(
      routes({
        [RELATIVES]: { body: [MOTHER] },
        [TREE]: { body: { warnings: ['Falta la edad de un familiar'], svg_base64: 'PHN2Zz4=' } },
      }),
    )
    const user = userEvent.setup()
    renderApp('/medico_tratante/familiograma?dni=30123456')

    await user.click(await screen.findByRole('button', { name: 'Guardar y generar familiograma' }))

    const image = await screen.findByRole('img', { name: 'Familiograma de Tomás Ruiz' })
    expect(image).toHaveAttribute('src', 'data:image/svg+xml;base64,PHN2Zz4=')
    expect(screen.getByText('Falta la edad de un familiar')).toBeInTheDocument()
  })

  it('keeps the relatives and lets the doctor retry when the module fails', async () => {
    const mock = mockApi(
      routes({
        [RELATIVES]: { body: [MOTHER] },
        [TREE]: {
          status: 503,
          body: { detalle: "El módulo externo 'familiograma' no está disponible." },
        },
      }),
    )
    const user = userEvent.setup()
    renderApp('/medico_tratante/familiograma?dni=30123456')

    await user.click(await screen.findByRole('button', { name: 'Guardar y generar familiograma' }))

    expect(await screen.findByText(/no está disponible/)).toBeInTheDocument()
    expect(screen.getByText(/podés reintentar/)).toBeInTheDocument()
    expect(screen.getByLabelText('Nombre')).toHaveValue('Carolina')
    expect(sentTo(mock, SAVE)).toHaveLength(1)
  })

  it('shows the message of the module when it rejects the data', async () => {
    mockApi(
      routes({
        [RELATIVES]: { body: [MOTHER] },
        [TREE]: {
          status: 422,
          body: { detalle: 'El módulo de familiograma rechazó los datos: Vínculos ambiguos' },
        },
      }),
    )
    const user = userEvent.setup()
    renderApp('/medico_tratante/familiograma?dni=30123456')

    await user.click(await screen.findByRole('button', { name: 'Guardar y generar familiograma' }))

    expect(await screen.findByText(/Vínculos ambiguos/)).toBeInTheDocument()
  })
})

describe('validateRelative', () => {
  const complete = {
    ...emptyRelativeForm(0),
    kinshipId: '1',
    firstName: 'Carolina',
    lastName: 'Ruiz',
    sex: 'mujer' as const,
  }

  it('accepts a relative without age', () => {
    expect(validateRelative(complete)).toEqual({})
  })

  it('accepts a fractional age', () => {
    expect(validateRelative({ ...complete, age: '0.5' })).toEqual({})
  })

  it('rejects an age out of range', () => {
    expect(validateRelative({ ...complete, age: '-1' }).age).toMatch(/entre 0 y 120/)
    expect(validateRelative({ ...complete, age: '121' }).age).toMatch(/entre 0 y 120/)
  })

  it('asks for every required field', () => {
    expect(Object.keys(validateRelative(emptyRelativeForm(0))).sort()).toEqual([
      'firstName',
      'kinshipId',
      'lastName',
      'sex',
    ])
  })
})

describe('relatives payload', () => {
  it('keeps what was saved when it is edited and sent again', () => {
    const payload = toPayload([relativeToForm({ ...MOTHER, dni: '20111222' }, 0)])

    expect(payload.relatives[0]).toMatchObject({
      kinship_id: 1,
      dni: '20111222',
      age: 36,
      pathology_ids: [1],
    })
  })

  it('sends a null DNI when it is empty', () => {
    const payload = toPayload([relativeToForm(MOTHER, 0)])

    expect(payload.relatives[0].dni).toBeNull()
  })

  it('sends a null age when it is unknown', () => {
    const payload = toPayload([relativeToForm({ ...MOTHER, age: null }, 0)])

    expect(payload.relatives[0].age).toBeNull()
  })
})
