import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mockApi, renderApp, sentTo, startTestSession } from '../../test-utils'

const PATH = '/administrativo_laboratorio/remuestreo'
const LISTA = 'GET /turnos/estudios/remuestreables'
const PEDIR = 'POST /turnos/estudios/4/remuestreo-administrativo'

const EN_COREA = {
  estudio_id: 4,
  paciente: 'Paula Ramos',
  dni: '22321414',
  estado: 'EnViajeACorea',
  remuestreo_pendiente: null,
}
const EN_BIOINFORMATICA = {
  estudio_id: 5,
  paciente: 'Martín Gómez',
  dni: '30999888',
  estado: 'EnElAreaDeBioinformatica',
  remuestreo_pendiente: null,
}
const PEDIDO = {
  remuestreo_id: 1,
  estudio_id: 4,
  estado: 'TurnoSacado',
  motivo: 'mala_calidad_de_muestra',
  detalle: 'La muestra llegó hemolizada.',
  medico_avisado: true,
  paciente_avisado: true,
}

afterEach(() => vi.unstubAllGlobals())
beforeEach(() => {
  localStorage.clear()
  startTestSession('administrativo_laboratorio')
})

async function elegirYCompletar(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole('button', { name: /Paula Ramos/ }))
  await user.selectOptions(
    screen.getByLabelText('Motivo del remuestreo'),
    'mala_calidad_de_muestra',
  )
  await user.type(screen.getByLabelText('Detalle'), 'La muestra llegó hemolizada.')
}

describe('RemuestreoPantalla: la lista', () => {
  it('lista los estudios con el paciente, el DNI y el estado', async () => {
    mockApi({ [LISTA]: { body: [EN_COREA, EN_BIOINFORMATICA] } })
    renderApp(PATH)

    const primero = await screen.findByRole('button', { name: /Paula Ramos/ })
    expect(primero).toHaveTextContent('Estudio 4 · Paula Ramos')
    expect(primero).toHaveTextContent('DNI 22321414 · En viaje a Corea')
    expect(screen.getByRole('button', { name: /Martín Gómez/ })).toHaveTextContent(
      'DNI 30999888 · En el área de bioinformática',
    )
  })

  it('muestra que está cargando mientras llegan los estudios', async () => {
    mockApi({ [LISTA]: { body: [EN_COREA] } })
    renderApp(PATH)

    expect(screen.getByText('Cargando los estudios…')).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: /Paula Ramos/ })).toBeInTheDocument()
    expect(screen.queryByText('Cargando los estudios…')).not.toBeInTheDocument()
  })

  it('avisa cuando no hay estudios para remuestrear', async () => {
    mockApi({ [LISTA]: { body: [] } })
    renderApp(PATH)

    expect(
      await screen.findByText('No hay estudios en viaje a Corea ni en el área de bioinformática.'),
    ).toBeInTheDocument()
  })

  it('muestra el error y deja reintentar', async () => {
    let intentos = 0
    mockApi({
      [LISTA]: () => {
        intentos += 1
        return intentos === 1
          ? { status: 503, body: { detalle: 'El servicio no responde.' } }
          : { body: [EN_COREA] }
      },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No se pudieron cargar los estudios: El servicio no responde.',
    )
    await user.click(screen.getByRole('button', { name: 'Reintentar' }))

    expect(await screen.findByRole('button', { name: /Paula Ramos/ })).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('marca el estudio que ya tiene un remuestreo pendiente y no deja pedir otro', async () => {
    const pendiente = {
      ...EN_COREA,
      remuestreo_pendiente: {
        remuestreo_id: 1,
        motivo: 'adn_desnaturalizado',
        detalle: 'Pedido anterior',
        pedido_en: '2026-11-02T10:07:00-03:00',
      },
    }
    const mock = mockApi({ [LISTA]: { body: [pendiente] } })
    renderApp(PATH)
    const user = userEvent.setup()

    expect(await screen.findByText('Remuestreo pendiente')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Paula Ramos/ }))

    expect(await screen.findByRole('status')).toHaveTextContent(
      'ya tiene un remuestreo pendiente: el paciente todavía no sacó el nuevo turno',
    )
    expect(screen.queryByRole('button', { name: 'Pedir remuestreo' })).not.toBeInTheDocument()
    expect(sentTo(mock, PEDIR)).toEqual([])
  })
})

describe('RemuestreoPantalla: pedir el remuestreo', () => {
  it('manda el motivo y el detalle, avisa el resultado y saca el estudio de la lista', async () => {
    let lista = [EN_COREA, EN_BIOINFORMATICA]
    const mock = mockApi({
      [LISTA]: () => ({ body: lista }),
      [PEDIR]: () => {
        lista = [EN_BIOINFORMATICA]
        return { body: PEDIDO }
      },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await elegirYCompletar(user)
    await user.click(screen.getByRole('button', { name: 'Pedir remuestreo' }))

    expect(await screen.findByRole('status')).toHaveTextContent(
      'Remuestreo pedido para el estudio 4. El estudio volvió a Turno sacado, sin costo. Se avisó al médico tratante y al paciente.',
    )
    expect(sentTo(mock, PEDIR)).toEqual([
      { motivo: 'mala_calidad_de_muestra', detalle: 'La muestra llegó hemolizada.' },
    ])
    await vi.waitFor(() =>
      expect(screen.queryByRole('button', { name: /Paula Ramos/ })).not.toBeInTheDocument(),
    )
    expect(screen.getByRole('button', { name: /Martín Gómez/ })).toBeInTheDocument()
    expect(screen.queryByLabelText('Detalle')).not.toBeInTheDocument()
  })

  it('manda el motivo del ADN cuando se elige ese', async () => {
    const mock = mockApi({
      [LISTA]: { body: [EN_COREA] },
      [PEDIR]: { body: { ...PEDIDO, motivo: 'adn_desnaturalizado' } },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: /Paula Ramos/ }))
    await user.selectOptions(
      screen.getByLabelText('Motivo del remuestreo'),
      'ADN insuficiente o desnaturalizado',
    )
    await user.type(screen.getByLabelText('Detalle'), '  Corea informó ADN degradado.  ')
    await user.click(screen.getByRole('button', { name: 'Pedir remuestreo' }))

    await screen.findByRole('status')
    expect(sentTo(mock, PEDIR)).toEqual([
      { motivo: 'adn_desnaturalizado', detalle: 'Corea informó ADN degradado.' },
    ])
  })

  it('dice a quién no se pudo avisar', async () => {
    mockApi({
      [LISTA]: { body: [EN_COREA] },
      [PEDIR]: { body: { ...PEDIDO, medico_avisado: false } },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await elegirYCompletar(user)
    await user.click(screen.getByRole('button', { name: 'Pedir remuestreo' }))

    expect(await screen.findByRole('status')).toHaveTextContent(
      'Se avisó al paciente, pero no se pudo avisar al médico tratante.',
    )
  })

  it('deshabilita el envío mientras se manda y no lo manda dos veces', async () => {
    let terminar: (respuesta: Response) => void = () => {}
    let envios = 0
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const { pathname } = new URL(String(input), 'http://localhost')
        if (init?.method === 'POST' && pathname.endsWith('/remuestreo-administrativo')) {
          envios += 1
          return new Promise<Response>((resolver) => {
            terminar = resolver
          })
        }
        return Promise.resolve(new Response(JSON.stringify([EN_COREA])))
      }),
    )
    renderApp(PATH)
    const user = userEvent.setup()

    await elegirYCompletar(user)
    await user.click(screen.getByRole('button', { name: 'Pedir remuestreo' }))

    const boton = screen.getByRole('button', { name: 'Pedir remuestreo' })
    expect(boton).toBeDisabled()
    expect(boton).toHaveAttribute('aria-busy', 'true')
    expect(screen.getByLabelText('Motivo del remuestreo')).toBeDisabled()
    expect(screen.getByLabelText('Detalle')).toBeDisabled()
    await user.click(boton)
    expect(envios).toBe(1)

    terminar(new Response(JSON.stringify(PEDIDO), { status: 200 }))
    expect(await screen.findByRole('status')).toHaveTextContent('Remuestreo pedido')
  })

  it('pide el motivo y el detalle antes de mandar', async () => {
    const mock = mockApi({ [LISTA]: { body: [EN_COREA] }, [PEDIR]: { body: PEDIDO } })
    renderApp(PATH)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: /Paula Ramos/ }))
    await user.click(screen.getByRole('button', { name: 'Pedir remuestreo' }))

    expect(screen.getByText('Elegí el motivo del remuestreo.')).toBeInTheDocument()
    expect(
      screen.getByText(/Escribí el detalle del remuestreo \(al menos 3 caracteres\)/),
    ).toBeInTheDocument()

    await user.selectOptions(
      screen.getByLabelText('Motivo del remuestreo'),
      'mala_calidad_de_muestra',
    )
    await user.type(screen.getByLabelText('Detalle'), '  a ')
    await user.click(screen.getByRole('button', { name: 'Pedir remuestreo' }))

    expect(screen.queryByText('Elegí el motivo del remuestreo.')).not.toBeInTheDocument()
    expect(screen.getByLabelText('Detalle')).toHaveAttribute('aria-invalid', 'true')
    expect(sentTo(mock, PEDIR)).toEqual([])
  })

  it('muestra el error del servidor y vuelve a pedir la lista', async () => {
    let pedidosDeLista = 0
    mockApi({
      [LISTA]: () => {
        pedidosDeLista += 1
        return { body: pedidosDeLista === 1 ? [EN_COREA] : [] }
      },
      [PEDIR]: {
        status: 409,
        body: {
          detalle:
            'El estudio está TurnoSacado: el remuestreo solo se pide cuando la muestra está en viaje a Corea o en el área de bioinformática.',
          code: 'estudio_sin_remuestreo_posible',
        },
      },
    })
    renderApp(PATH)
    const user = userEvent.setup()

    await elegirYCompletar(user)
    await user.click(screen.getByRole('button', { name: 'Pedir remuestreo' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'El estudio está TurnoSacado: el remuestreo solo se pide cuando la muestra está en viaje a Corea',
    )
    expect(
      await screen.findByText('No hay estudios en viaje a Corea ni en el área de bioinformática.'),
    ).toBeInTheDocument()
    expect(pedidosDeLista).toBe(2)
  })
})

describe('RemuestreoPantalla: en la aplicación', () => {
  it('tiene su entrada en el menú del administrativo', async () => {
    mockApi({ [LISTA]: { body: [] } })
    renderApp(PATH)

    const enlaces = await screen.findAllByRole('link', {
      name: 'Pedir el remuestreo de un estudio',
    })
    expect(enlaces[0]).toHaveAttribute('href', '/administrativo_laboratorio/remuestreo')
  })

  it('no habla de lotes en la pantalla', async () => {
    mockApi({ [LISTA]: { body: [EN_COREA] } })
    renderApp(PATH)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: /Paula Ramos/ }))

    expect(within(screen.getByRole('main')).queryByText(/lote/i)).not.toBeInTheDocument()
  })
})
