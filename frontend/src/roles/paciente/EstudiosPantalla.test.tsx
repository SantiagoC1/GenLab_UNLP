import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { mockApi, renderWithQuery } from '../../test-utils'
import EstudiosPantalla from './EstudiosPantalla'

describe('Mis estudios del paciente', () => {
  it('muestra los estudios de la cuenta', async () => {
    mockApi({
      'GET /consulta_medica/my-studies': {
        body: [
          {
            id: 4,
            state: 'Creado',
            pompe_urgent: false,
            created_at: '2026-11-20T10:00:00+00:00',
            state_changed_at: '2026-11-20T10:00:00+00:00',
            patient_name: 'Lucía Fernández',
            patient_dni: '30123456',
            pathologies: ['Fabry'],
            gene_count: 1,
          },
        ],
      },
    })
    renderWithQuery(<EstudiosPantalla />)

    expect(await screen.findByText(/Estudio 4/)).toBeInTheDocument()
    expect(screen.queryByText('Pompe urgente')).not.toBeInTheDocument()
  })

  it('avisa cuando no tiene estudios', async () => {
    mockApi({ 'GET /consulta_medica/my-studies': { body: [] } })
    renderWithQuery(<EstudiosPantalla />)

    expect(await screen.findByText('Todavía no tenés estudios.')).toBeInTheDocument()
  })
})
