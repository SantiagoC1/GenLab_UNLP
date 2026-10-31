import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import PresupuestosPantalla from './PresupuestosPantalla'

function respuesta(cuerpo: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(cuerpo), { status }))
}

function renderizar() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <PresupuestosPantalla />
    </QueryClientProvider>,
  )
}

describe('PresupuestosPantalla', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('lista la bandeja, muestra los genes y el importe, y emite el presupuesto', async () => {
    let pendientes = [{ id: 2, paciente: 'Martín Gómez', cantidad_genes: 8 }]
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (init?.method === 'POST') {
        pendientes = []
        return respuesta({ estudio_id: 2, importe_usd: 590 }, 201)
      }
      if (url.endsWith('/estudios-pendientes')) return respuesta(pendientes)
      return respuesta({
        id: 2,
        paciente: 'Martín Gómez',
        genes: ['GBA', 'GLA'],
        cantidad_genes: 8,
        importe_usd: 590,
        presupuesto_emitido: false,
      })
    })
    vi.stubGlobal('fetch', fetchMock)
    renderizar()

    await userEvent.click(await screen.findByRole('button', { name: /Martín Gómez/ }))
    expect(await screen.findByText('USD 590', { exact: false })).toBeInTheDocument()
    expect(screen.getByText('GBA')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Emitir presupuesto' }))
    expect(await screen.findByRole('status')).toHaveTextContent('Presupuesto emitido')
    expect(await screen.findByText('No hay estudios sin presupuesto.')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/presupuesto_pago/estudios/2/presupuesto'),
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('muestra el error cuando no se puede emitir', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) => {
        if (init?.method === 'POST')
          return respuesta({ detalle: 'El estudio ya tiene el presupuesto emitido.' }, 409)
        if (url.endsWith('/estudios-pendientes')) {
          return respuesta([{ id: 1, paciente: 'Lucía Fernández', cantidad_genes: 3 }])
        }
        return respuesta({
          id: 1,
          paciente: 'Lucía Fernández',
          genes: ['GBA'],
          cantidad_genes: 3,
          importe_usd: 500,
          presupuesto_emitido: false,
        })
      }),
    )
    renderizar()

    await userEvent.click(await screen.findByRole('button', { name: /Lucía Fernández/ }))
    await userEvent.click(await screen.findByRole('button', { name: 'Emitir presupuesto' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('ya tiene el presupuesto emitido')
  })
})
