import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { PANTALLAS } from './roles/pantallas'
import { useRol } from './roles/rol-context'
import AvisosPantalla from './roles/comun/AvisosPantalla'

export default function App() {
  const { rol } = useRol()
  const inicio = PANTALLAS.find((p) => p.rol === rol)

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
      <Route element={<Layout />}>
        {PANTALLAS.filter((p) => p.rol !== 'publico').map(
          ({ rol: r, ruta, componente: Pantalla }) => (
            <Route key={`${r}/${ruta}`} path={`/${r}/${ruta}`} element={<Pantalla />} />
          ),
        )}
        <Route path="/avisos" element={<AvisosPantalla />} />
        <Route
          path="*"
          element={<Navigate to={inicio ? `/${rol}/${inicio.ruta}` : '/ingresar'} replace />}
        />
      </Route>
    </Routes>
  )
}
