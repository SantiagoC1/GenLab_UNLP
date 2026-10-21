import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { PANTALLAS, initialScreen } from './roles/pantallas'
import { useRol } from './roles/rol-context'
import AvisosPantalla from './roles/comun/AvisosPantalla'

function ProtectedRoute() {
  const { session } = useRol()
  if (!session && !import.meta.env.DEV) return <Navigate to="/ingresar" replace />
  if (session?.mustChangePassword) return <Navigate to="/cambiar-contrasena" replace />
  return <Layout />
}

export default function App() {
  const { rol } = useRol()
  const inicio = initialScreen(rol)

  return (
    <Routes>
      {PANTALLAS.filter((p) => p.rol === 'publico').map(({ ruta, componente: Pantalla }) => (
        <Route
          key={ruta}
          path={`/${ruta}`}
          element={
            <main className="mx-auto max-w-md p-4 sm:p-8">
              <Pantalla />
            </main>
          }
        />
      ))}
      <Route element={<ProtectedRoute />}>
        {PANTALLAS.filter((p) => p.rol !== 'publico').map(
          ({ rol: r, ruta, componente: Pantalla }) => (
            <Route key={`${r}/${ruta}`} path={`/${r}/${ruta}`} element={<Pantalla />} />
          ),
        )}
        <Route path="/avisos" element={<AvisosPantalla />} />
        <Route
          path="*"
          element={<Navigate to={inicio ? `/${rol}/${inicio}` : '/ingresar'} replace />}
        />
      </Route>
    </Routes>
  )
}
