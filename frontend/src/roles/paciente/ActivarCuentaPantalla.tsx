import { ChangePasswordForm } from '../../components/ChangePasswordForm'

export default function ActivarCuentaPantalla() {
  return (
    <section className="max-w-md">
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">Activar la cuenta</h1>
      <p className="mt-1 text-sm text-slate-500">Escenario 3 · M1-RF7</p>
      <ChangePasswordForm />
    </section>
  )
}
