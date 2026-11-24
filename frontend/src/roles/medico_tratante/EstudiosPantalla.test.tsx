import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { mockApi, renderWithQuery } from '../../test-utils'
import EstudiosPantalla from './EstudiosPantalla'

const STUDY = {
  id: 7,
  state: 'TurnoSacado',
  pompe_urgent: true,
  created_at: '2026-11-20T10:00:00+00:00',
  state_changed_at: '2026-11-20T10:00:00+00:00',
  patient_name: 'Lucía Fernández',
  patient_dni: '30123456',
  pathologies: ['Pompe', 'Fabry'],
  gene_count: 3,
}

describe('Mis estudios del médico', () => {
  it('muestra cada estudio con su paciente, estado y marca de Pompe urgente', async () => {
    mockApi({ 'GET /consulta_medica/studies': { body: [STUDY] } })
    renderWithQuery(<EstudiosPantalla />)

    expect(await screen.findByText(/Lucía Fernández/)).toBeInTheDocument()
    expect(screen.getByText('Turno sacado')).toBeInTheDocument()
    expect(screen.getByText('Pompe urgente')).toBeInTheDocument()
    expect(screen.getByText('Pompe, Fabry')).toBeInTheDocument()
  })

  it('avisa cuando todavía no hay estudios', async () => {
    mockApi({ 'GET /consulta_medica/studies': { body: [] } })
    renderWithQuery(<EstudiosPantalla />)

    expect(await screen.findByText('Todavía no pediste ningún estudio.')).toBeInTheDocument()
  })
})
