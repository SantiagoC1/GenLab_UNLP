import { Navigate } from 'react-router-dom'
import { ChangePasswordForm } from '../../components/ChangePasswordForm'
import { useRol } from '../rol-context'

export default function ChangePasswordScreen() {
  const { session } = useRol()
  if (!session && !import.meta.env.DEV) return <Navigate to="/ingresar" replace />

  return (
    <section>
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">Cambiar la contraseña</h1>
      <p className="mt-1 text-sm text-slate-500">
        Escenario 3 · M1-RF7. Para seguir tenés que reemplazar la contraseña inicial. Si el paciente
        es menor de edad, lo hace su padre o madre.
      </p>
      <ChangePasswordForm />
    </section>
  )
}
