import { useMutation, useQuery } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Alert } from '../../components/Alert'
import { Button } from '../../components/Button'
import { PersonFields } from '../../components/PersonFields'
import { TextField } from '../../components/TextField'
import { getCatalogs, register, toSession } from '../../lib/access'
import {
  EMPTY_PERSON,
  toPayload,
  validateNewPassword,
  validatePerson,
  type Errors,
  type PersonData,
} from '../../lib/validation'
import { initialScreen } from '../pantallas'
import { useRol } from '../rol-context'
import type { Rol } from '../roles'

// M1-RF1. The carrier and the medical manager are created by the general administrator.
const SELF_SIGNUP_ROLES: readonly Rol[] = [
  'medico_tratante',
  'administrativo_laboratorio',
  'bioinformatico',
]

/** Scenario 1 · M1-RF1 to RF3. */
export default function RegistroPantalla() {
  const { startSession } = useRol()
  const navigate = useNavigate()
  const [person, setPerson] = useState<PersonData>(EMPTY_PERSON)
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<Errors>({})

  const catalogs = useQuery({ queryKey: ['catalogs'], queryFn: getCatalogs })
  const signUp = useMutation({
    mutationFn: () => register({ ...toPayload(person), password }),
    onSuccess: (response) => {
      const session = toSession(response)
      startSession(session)
      navigate(`/${session.rol}/${initialScreen(session.rol)}`, { replace: true })
    },
  })

  const change = <K extends keyof PersonData>(field: K, value: PersonData[K]) =>
    setPerson((current) => ({ ...current, [field]: value }))

  const submit = (event: FormEvent) => {
    event.preventDefault()
    const found = validatePerson(person)
    const passwordError = validateNewPassword(password)
    if (passwordError) found.password = passwordError
    setErrors(found)
    if (Object.keys(found).length === 0) signUp.mutate()
  }

  return (
    <section>
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">Registrarse</h1>
      <p className="mt-1 text-sm text-slate-500">Escenario 1 · M1-RF1 a RF3</p>

      <form onSubmit={submit} noValidate className="mt-6 space-y-4">
        {signUp.error && <Alert kind="error">{signUp.error.message}</Alert>}
        {catalogs.isError && (
          <Alert kind="error">No pudimos cargar el catálogo de especialidades.</Alert>
        )}
        <PersonFields
          values={person}
          errors={errors}
          roles={SELF_SIGNUP_ROLES}
          catalogs={catalogs.data}
          onChange={change}
        />
        <TextField
          label="Contraseña"
          type="password"
          autoComplete="new-password"
          value={password}
          error={errors.password}
          hint="Al menos 8 caracteres."
          onChange={(e) => setPassword(e.target.value)}
        />
        <Button type="submit" loading={signUp.isPending}>
          Registrarme
        </Button>
        <p className="text-sm text-slate-600">
          ¿Ya tenés cuenta?{' '}
          <Link to="/ingresar" className="text-teal-700 underline">
            Ingresá
          </Link>
        </p>
      </form>
    </section>
  )
}
