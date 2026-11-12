import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import App from './App'
import { RolProvider } from './roles/RolProvider'

function renderizar(ruta: string) {
  const queryClient = new QueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[ruta]}>
        <RolProvider>
          <App />
        </RolProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('App', () => {
  beforeEach(() => localStorage.clear())

  it('muestra el menú del rol paciente por defecto', () => {
    renderizar('/')
    expect(
      screen.getAllByRole('link', { name: 'Sacar turno de extracción' }).length,
    ).toBeGreaterThan(0)
  })

  it('el selector de desarrollo cambia el menú al rol elegido', async () => {
    renderizar('/')
    await userEvent.selectOptions(screen.getAllByLabelText('Rol de desarrollo')[0], 'transportista')
    expect(screen.getAllByRole('link', { name: 'Orden del día' }).length).toBeGreaterThan(0)
    expect(screen.queryByRole('link', { name: 'Sacar turno de extracción' })).toBeNull()
  })
})
