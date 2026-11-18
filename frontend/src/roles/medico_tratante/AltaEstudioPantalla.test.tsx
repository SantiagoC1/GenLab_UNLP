import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { normalizeGene } from '../../lib/studies'
import { mockApi, queriesTo, renderApp, sentTo, startTestSession } from '../../test-utils'

const FIND = 'GET /consulta_medica/patients'
const PATHOLOGIES = 'GET /config_medica/pathologies'
const GENES = 'GET /consulta_medica/studies/genes'
const GENE_SEARCH = 'GET /consulta_medica/studies/gene-search'
const CREATE = 'POST /consulta_medica/studies'

const PATIENT = {
  id: 'p-1',
  dni: '30123456',
  first_name: 'Ana',
  last_name: 'Pérez',
  birth_date: '1990-05-20',
}
const FABRY = { id: 1, name: 'Fabry', code: 'FABRY', cardinal: null, secondary: [] }
const POMPE = { id: 2, name: 'Pompe', code: 'POMPE', cardinal: null, secondary: [] }
const CREATED = {
  id: 12,
  state: 'Creado',
  pompe_urgent: false,
  secondary_findings: false,
  genes: [{ gene: 'GLA', origin: 'patologia' }],
}

function genesFor(url: URL) {
  const secondary = url.searchParams.get('secondary_findings') === 'true'
  const genes = [{ gene: 'GLA', origin: 'patologia' }]
  if (secondary) genes.push({ gene: 'ACMG-1', origin: 'hallazgo_secundario' })
  return { body: { genes } }
}

function routes(overrides: Record<string, unknown> = {}) {
  return {
    [FIND]: { body: PATIENT },
    [PATHOLOGIES]: { body: [FABRY, POMPE] },
    [GENES]: genesFor,
    [GENE_SEARCH]: { body: { genes: ['GAA', 'GAB1'] } },
    [CREATE]: { status: 201, body: CREATED },
    ...overrides,
  } as Parameters<typeof mockApi>[0]
}

describe('AltaEstudioPantalla', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    startTestSession('medico_tratante')
  })
  afterEach(() => vi.unstubAllGlobals())

  it('loads the patient from the DNI in the address', async () => {
    mockApi(routes())
    renderApp('/medico_tratante/alta-estudio?dni=30123456')

    expect(await screen.findByText(/Paciente: Ana Pérez/)).toBeInTheDocument()
    expect(screen.getByLabelText('DNI del paciente')).toHaveValue('30123456')
  })

  it('searches for the patient by DNI when it does not come in the address', async () => {
    const mock = mockApi(routes())
    const user = userEvent.setup()
    renderApp('/medico_tratante/alta-estudio')

    await user.type(await screen.findByLabelText('DNI del paciente'), '30123456')
    await user.click(screen.getByRole('button', { name: 'Buscar paciente' }))

    expect(await screen.findByText(/Paciente: Ana Pérez/)).toBeInTheDocument()
    expect(queriesTo(mock, FIND)[0].get('dni')).toBe('30123456')
  })

  it('does not search with an invalid DNI', async () => {
    const mock = mockApi(routes())
    const user = userEvent.setup()
    renderApp('/medico_tratante/alta-estudio')

    await user.type(await screen.findByLabelText('DNI del paciente'), '123')
    await user.click(screen.getByRole('button', { name: 'Buscar paciente' }))

    expect(await screen.findByText('El DNI tiene que tener 7 u 8 dígitos.')).toBeInTheDocument()
    expect(queriesTo(mock, FIND)).toEqual([])
  })

  it('offers to register the patient when the DNI does not exist', async () => {
    mockApi(routes({ [FIND]: { status: 404, body: { detalle: 'No hay un paciente.' } } }))
    renderApp('/medico_tratante/alta-estudio?dni=30123456')

    const link = await screen.findByRole('link', { name: 'Dar de alta al paciente' })
    expect(link).toHaveAttribute('href', '/medico_tratante/alta-paciente')
    expect(screen.queryByRole('button', { name: 'Solicitar estudio' })).not.toBeInTheDocument()
  })

  it('shows the genes of the chosen pathology with their origin', async () => {
    const mock = mockApi(routes())
    const user = userEvent.setup()
    renderApp('/medico_tratante/alta-estudio?dni=30123456')

    expect(await screen.findByText('Elegí al menos una patología.')).toBeInTheDocument()
    await user.click(await screen.findByRole('checkbox', { name: 'Fabry' }))

    expect(await screen.findByText('GLA · De la patología')).toBeInTheDocument()
    expect(queriesTo(mock, GENES)[0].get('pathology_ids')).toBe('1')
  })

  it('asks again with the secondary findings when the box is checked', async () => {
    const mock = mockApi(routes())
    const user = userEvent.setup()
    renderApp('/medico_tratante/alta-estudio?dni=30123456')

    await user.click(await screen.findByRole('checkbox', { name: 'Fabry' }))
    await screen.findByText('GLA · De la patología')
    await user.click(screen.getByRole('checkbox', { name: 'Evaluar hallazgos secundarios' }))

    expect(await screen.findByText('ACMG-1 · Hallazgo secundario')).toBeInTheDocument()
    const last = queriesTo(mock, GENES).at(-1)
    expect(last?.get('secondary_findings')).toBe('true')
  })

  it('adds a manual gene in uppercase, once, and lets the doctor remove it', async () => {
    mockApi(routes())
    const user = userEvent.setup()
    renderApp('/medico_tratante/alta-estudio?dni=30123456')

    await user.click(await screen.findByRole('checkbox', { name: 'Fabry' }))
    await screen.findByText('GLA · De la patología')
    await user.type(screen.getByLabelText('Agregar un gen'), 'gaa')
    await user.click(screen.getByRole('button', { name: 'Agregar gen' }))
    await user.type(screen.getByLabelText('Agregar un gen'), 'GAA{Enter}')
    await user.type(screen.getByLabelText('Agregar un gen'), 'gla{Enter}')

    expect(screen.getAllByText('GAA · Agregado por el médico')).toHaveLength(1)
    expect(screen.queryByText('GLA · Agregado por el médico')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Quitar GAA' }))
    expect(screen.queryByText('GAA · Agregado por el médico')).not.toBeInTheDocument()
  })

  it('suggests genes from Apigen while the doctor types', async () => {
    const mock = mockApi(routes())
    const user = userEvent.setup()
    renderApp('/medico_tratante/alta-estudio?dni=30123456')

    await user.type(await screen.findByLabelText('Agregar un gen'), 'ga')

    expect(await screen.findByDisplayValue('ga')).toBeInTheDocument()
    await vi.waitFor(() => expect(queriesTo(mock, GENE_SEARCH)[0]?.get('q')).toBe('GA'))
    expect(document.querySelectorAll('#gene-suggestions option')).toHaveLength(2)
  })

  it('requests the study with the patient, the pathologies and the manual genes', async () => {
    const mock = mockApi(routes())
    const user = userEvent.setup()
    renderApp('/medico_tratante/alta-estudio?dni=30123456')

    await user.click(await screen.findByRole('checkbox', { name: 'Fabry' }))
    await screen.findByText('GLA · De la patología')
    await user.type(screen.getByLabelText('Agregar un gen'), 'gaa{Enter}')
    await user.click(screen.getByRole('button', { name: 'Solicitar estudio' }))

    expect(await screen.findByText(/Se solicitó el estudio 12 de Ana Pérez/)).toBeInTheDocument()
    expect(sentTo(mock, CREATE)).toEqual([
      {
        patient_id: 'p-1',
        pathology_ids: [1],
        secondary_findings: false,
        manual_genes: ['GAA'],
      },
    ])
  })

  it('says when the study is Pompe urgent', async () => {
    mockApi(routes({ [CREATE]: { status: 201, body: { ...CREATED, pompe_urgent: true } } }))
    const user = userEvent.setup()
    renderApp('/medico_tratante/alta-estudio?dni=30123456')

    await user.click(await screen.findByRole('checkbox', { name: 'Pompe' }))
    await screen.findByText('GLA · De la patología')
    await user.click(screen.getByRole('button', { name: 'Solicitar estudio' }))

    expect(await screen.findByText(/Pompe urgente/)).toBeInTheDocument()
  })

  it('does not let the doctor request the study without a pathology', async () => {
    mockApi(routes())
    renderApp('/medico_tratante/alta-estudio?dni=30123456')

    expect(await screen.findByRole('button', { name: 'Solicitar estudio' })).toBeDisabled()
  })

  it('warns and blocks the request when Apigen does not answer', async () => {
    mockApi(
      routes({
        [GENES]: {
          status: 503,
          body: { detalle: "El módulo externo 'Apigen' no está disponible." },
        },
      }),
    )
    const user = userEvent.setup()
    renderApp('/medico_tratante/alta-estudio?dni=30123456')

    await user.click(await screen.findByRole('checkbox', { name: 'Fabry' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Apigen')
    expect(screen.getByRole('button', { name: 'Solicitar estudio' })).toBeDisabled()
  })

  it('shows the error of the server when the study cannot be created', async () => {
    mockApi(routes({ [CREATE]: { status: 503, body: { detalle: 'Apigen no está disponible.' } } }))
    const user = userEvent.setup()
    renderApp('/medico_tratante/alta-estudio?dni=30123456')

    await user.click(await screen.findByRole('checkbox', { name: 'Fabry' }))
    await screen.findByText('GLA · De la patología')
    await user.click(screen.getByRole('button', { name: 'Solicitar estudio' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Apigen no está disponible.')
  })

  it('normalizes a gene to uppercase without spaces', () => {
    expect(normalizeGene('  gaa ')).toBe('GAA')
  })
})
