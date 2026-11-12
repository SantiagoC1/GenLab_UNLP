import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactElement } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import App from './App'
import type { SessionResponse } from './lib/access'
import { saveSession } from './lib/session'
import { RolProvider } from './roles/RolProvider'
import type { Rol } from './roles/roles'

// REUTILIZABLE: ayudas para los tests de las pantallas de todos los módulos.

interface SimulatedResponse {
  status?: number
  body: unknown
}

/**
 * Reemplaza `fetch` por respuestas simuladas. La clave es "MÉTODO /ruta" (sin el host), por
 * ejemplo 'POST /acceso/login'. La respuesta puede ser fija o una función, que se evalúa en cada
 * llamada y recibe la URL completa (sirve para que una lista cambie después de un alta o para
 * responder según la query string). Una ruta que no se simuló
 * responde 500, para que el test falle a la vista. Devuelve el mock, para revisar lo que se envió
 * con `sentTo`. Limpiar con `vi.unstubAllGlobals()`.
 */
export function mockApi(
  routes: Record<string, SimulatedResponse | ((url: URL) => SimulatedResponse)>,
) {
  const mock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), 'http://localhost')
    const key = `${init?.method ?? 'GET'} ${url.pathname}`
    const simulated = routes[key]
    if (!simulated) {
      return new Response(JSON.stringify({ detalle: `Sin respuesta simulada para ${key}` }), {
        status: 500,
      })
    }
    const route = typeof simulated === 'function' ? simulated(url) : simulated
    return new Response(JSON.stringify(route.body), {
      status: route.status ?? 200,
      headers: { 'Content-Type': 'application/json' },
    })
  })
  vi.stubGlobal('fetch', mock)
  return mock
}

/** Los cuerpos JSON que la aplicación envió a esa ruta ("MÉTODO /ruta"), en orden. */
export function sentTo(mock: ReturnType<typeof mockApi>, key: string): Record<string, unknown>[] {
  return mock.mock.calls
    .filter(([input, init]) => {
      const path = new URL(String(input), 'http://localhost').pathname
      return `${init?.method ?? 'GET'} ${path}` === key
    })
    .map(([, init]) => JSON.parse(String(init?.body ?? '{}')))
}

/** La query string de cada pedido a esa ruta ("MÉTODO /ruta"), en orden. */
export function queriesTo(mock: ReturnType<typeof mockApi>, key: string): URLSearchParams[] {
  return mock.mock.calls
    .map(([input, init]) => ({ url: new URL(String(input), 'http://localhost'), init }))
    .filter(({ url, init }) => `${init?.method ?? 'GET'} ${url.pathname}` === key)
    .map(({ url }) => url.searchParams)
}

/** La respuesta del backend cuando se abre una sesión (ingreso o registro). */
export function sessionResponse(rol: Rol, mustChangePassword = false): SessionResponse {
  return { access_token: 'test-token', role: rol, must_change_password: mustChangePassword }
}

/** Deja abierta una sesión con ese rol, como si la persona ya hubiera ingresado. */
export function startTestSession(rol: Rol): void {
  saveSession({ token: 'test-token', rol, mustChangePassword: false })
}

/** Dibuja un componente suelto, con el proveedor de consultas. */
export function renderWithQuery(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

/** Dibuja toda la aplicación, con sus proveedores, en esa ruta. */
export function renderApp(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <RolProvider>
          <App />
        </RolProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}
