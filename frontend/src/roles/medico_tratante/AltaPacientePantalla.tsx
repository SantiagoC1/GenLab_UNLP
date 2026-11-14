import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { Alert } from '../../components/Alert'
import { Button } from '../../components/Button'
import { SymptomSearch } from '../../components/SymptomSearch'
import { FIELD_CLASS, TextField } from '../../components/TextField'
import { ApiError } from '../../lib/api'
import {
  EMPTY_PATIENT_FORM,
  isMinor,
  isValidDni,
  MAX_EMAIL_LENGTH,
  MAX_NAME_LENGTH,
  MAX_PHONE_LENGTH,
  MAX_SUMMARY_LENGTH,
  todayAsIso,
  useCreatePatient,
  useFindPatient,
  validatePatient,
  type CreatedPatient,
  type PatientForm,
  type SuspicionType,
} from '../../lib/patients'
import { usePathologies } from '../../lib/pathologies'
import type { Errors } from '../../lib/validation'

/** Mensaje para el médico: el del backend si lo hay, y si no, que no hay conexión. */
function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : 'No pudimos conectarnos. Revisá tu conexión.'
}

/**
 * Busca al paciente por DNI y, si no existe, lo da de alta (escenario 9).
 *
 * Accesibilidad: cada error se asocia a su campo con `aria-describedby` y se anuncia con
 * `role="alert"`. Al enviar con errores, el foco pasa a un resumen que dice cuántos campos hay que
 * corregir, así quien usa teclado o lector de pantalla no tiene que buscarlos.
 */
export default function AltaPacientePantalla() {
  const [form, setForm] = useState<PatientForm>(EMPTY_PATIENT_FORM)
  const [errors, setErrors] = useState<Errors>({})
  const [created, setCreated] = useState<CreatedPatient | null>(null)
  const [searchError, setSearchError] = useState('')
  const [showForm, setShowForm] = useState(false)

  const find = useFindPatient()
  const create = useCreatePatient()
  const pathologies = usePathologies()
  const summaryId = useId()
  const errorSummary = useRef<HTMLDivElement>(null)
  const suspicionErrorId = useId()
  const pathologiesErrorId = useId()
  const summaryErrorId = useId()
  const symptomsErrorId = useId()
  const errorCount = Object.keys(errors).length

  useEffect(() => {
    if (errorCount > 0) errorSummary.current?.focus()
  }, [errors, errorCount])

  /** Cambia un solo campo del formulario sin tocar el resto. */
  const set = <K extends keyof PatientForm>(key: K, value: PatientForm[K]) =>
    setForm((current) => ({ ...current, [key]: value }))

  /** Busca por DNI: si el backend responde 404 muestra el formulario de alta. */
  const search = (event: FormEvent) => {
    event.preventDefault()
    setSearchError('')
    setShowForm(false)
    if (!isValidDni(form.dni)) {
      setSearchError('El DNI tiene que tener 7 u 8 dígitos.')
      return
    }
    find.mutate(form.dni, {
      onError: (error) => {
        if (error instanceof ApiError && error.status === 404) setShowForm(true)
        else setSearchError(errorMessage(error))
      },
    })
  }

  /** Agrega o quita un diagnóstico presuntivo de la lista elegida. */
  const togglePathology = (id: number) =>
    set(
      'pathologyIds',
      form.pathologyIds.includes(id)
        ? form.pathologyIds.filter((item) => item !== id)
        : [...form.pathologyIds, id],
    )

  /** Valida el formulario y, si está completo, envía el alta. */
  const submit = (event: FormEvent) => {
    event.preventDefault()
    const found = validatePatient(form)
    setErrors(found)
    if (Object.keys(found).length > 0) return
    create.mutate(form, { onSuccess: setCreated })
  }

  const minor = isMinor(form.birthDate)
  const existing = find.data

  return (
    <section className="space-y-6">
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">Dar de alta al paciente</h1>

      <form onSubmit={search} className="flex flex-wrap items-end gap-3" noValidate>
        <div className="w-full sm:w-64">
          <TextField
            label="DNI del paciente"
            value={form.dni}
            inputMode="numeric"
            maxLength={8}
            error={searchError || undefined}
            onChange={(event) => {
              set('dni', event.target.value)
              find.reset()
              setShowForm(false)
            }}
          />
        </div>
        <Button type="submit" loading={find.isPending}>
          Buscar paciente
        </Button>
      </form>

      {existing && (
        <Alert>
          Este paciente ya está registrado: {existing.first_name} {existing.last_name}.{' '}
          <Link
            className="font-medium underline"
            to={`/medico_tratante/alta-estudio?dni=${encodeURIComponent(existing.dni)}`}
          >
            Dar de alta el estudio
          </Link>
        </Alert>
      )}

      {created && (
        <Alert kind="success">
          Se dio de alta a {created.first_name} {created.last_name}.{' '}
          {created.account_created
            ? `Se enviaron las credenciales a ${form.email.trim().toLowerCase()}.`
            : 'Ya existía la cuenta de ese mail: no se enviaron credenciales nuevas.'}{' '}
          <Link
            className="font-medium underline"
            to={`/medico_tratante/alta-estudio?dni=${encodeURIComponent(created.dni)}`}
          >
            Dar de alta el estudio
          </Link>
        </Alert>
      )}

      {showForm && !created && (
        <form onSubmit={submit} noValidate className="space-y-4">
          <Alert>No hay un paciente con ese DNI. Completá sus datos para darlo de alta.</Alert>

          {errorCount > 0 && (
            <div
              ref={errorSummary}
              tabIndex={-1}
              role="alert"
              className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-900"
            >
              {errorCount === 1
                ? 'Hay 1 campo para corregir.'
                : `Hay ${errorCount} campos para corregir.`}{' '}
              El motivo está debajo de cada campo.
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <TextField
              label="Nombre"
              maxLength={MAX_NAME_LENGTH}
              value={form.firstName}
              error={errors.firstName}
              onChange={(event) => set('firstName', event.target.value)}
            />
            <TextField
              label="Apellido"
              maxLength={MAX_NAME_LENGTH}
              value={form.lastName}
              error={errors.lastName}
              onChange={(event) => set('lastName', event.target.value)}
            />
            <TextField
              label="Fecha de nacimiento"
              type="date"
              max={todayAsIso()}
              value={form.birthDate}
              error={errors.birthDate}
              onChange={(event) => set('birthDate', event.target.value)}
            />
            <TextField
              label="Teléfono"
              type="tel"
              maxLength={MAX_PHONE_LENGTH}
              value={form.phone}
              error={errors.phone}
              onChange={(event) => set('phone', event.target.value)}
            />
            <TextField
              label={minor ? 'Mail del padre o madre' : 'Mail'}
              type="email"
              maxLength={MAX_EMAIL_LENGTH}
              value={form.email}
              error={errors.email}
              hint={
                minor
                  ? 'El paciente es menor de 18 años: la cuenta de acceso es la de su padre o madre.'
                  : undefined
              }
              onChange={(event) => set('email', event.target.value)}
            />
          </div>

          <fieldset aria-describedby={errors.suspicionType ? suspicionErrorId : undefined}>
            <legend className="text-sm font-medium text-slate-800">Tipo de sospecha</legend>
            <div className="mt-1 flex gap-4">
              {(['clinica', 'familiar'] as SuspicionType[]).map((type) => (
                <label key={type} className="flex items-center gap-2 text-sm">
                  <input
                    type="radio"
                    name="suspicion-type"
                    value={type}
                    checked={form.suspicionType === type}
                    onChange={() => set('suspicionType', type)}
                  />
                  {type === 'clinica' ? 'Clínica' : 'Familiar'}
                </label>
              ))}
            </div>
            {errors.suspicionType && (
              <p id={suspicionErrorId} role="alert" className="mt-1 text-xs text-red-700">
                {errors.suspicionType}
              </p>
            )}
          </fieldset>

          <fieldset aria-describedby={errors.pathologyIds ? pathologiesErrorId : undefined}>
            <legend className="text-sm font-medium text-slate-800">
              Diagnóstico presuntivo (patologías lisosomales)
            </legend>
            {pathologies.isPending && <p className="text-sm text-slate-600">Cargando…</p>}
            {pathologies.isError && (
              <p className="text-sm text-red-700">{errorMessage(pathologies.error)}</p>
            )}
            <div className="mt-1 flex flex-wrap gap-4">
              {pathologies.data?.map((pathology) => (
                <label key={pathology.id} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={form.pathologyIds.includes(pathology.id)}
                    onChange={() => togglePathology(pathology.id)}
                  />
                  {pathology.name}
                </label>
              ))}
            </div>
            {errors.pathologyIds && (
              <p id={pathologiesErrorId} role="alert" className="mt-1 text-xs text-red-700">
                {errors.pathologyIds}
              </p>
            )}
          </fieldset>

          <div>
            <label htmlFor={summaryId} className="block text-sm font-medium text-slate-800">
              Resumen de historia clínica
            </label>
            <textarea
              id={summaryId}
              rows={4}
              maxLength={MAX_SUMMARY_LENGTH}
              className={FIELD_CLASS}
              value={form.clinicalSummary}
              aria-invalid={errors.clinicalSummary ? true : undefined}
              aria-describedby={errors.clinicalSummary ? summaryErrorId : undefined}
              onChange={(event) => set('clinicalSummary', event.target.value)}
            />
            {errors.clinicalSummary && (
              <p id={summaryErrorId} role="alert" className="mt-1 text-xs text-red-700">
                {errors.clinicalSummary}
              </p>
            )}
          </div>

          <div>
            <SymptomSearch
              label="Buscar síntomas del paciente"
              selected={form.symptoms}
              onSelect={(symptom) => set('symptoms', [...form.symptoms, symptom])}
            />
            {form.symptoms.length > 0 && (
              <ul aria-label="Síntomas elegidos" className="mt-2 flex flex-wrap gap-2">
                {form.symptoms.map((symptom) => (
                  <li
                    key={symptom.code}
                    className="flex items-center gap-2 rounded-md border border-slate-300 bg-white px-2 py-1 text-sm"
                  >
                    {symptom.term}
                    <button
                      type="button"
                      aria-label={`Quitar ${symptom.term}`}
                      onClick={() =>
                        set(
                          'symptoms',
                          form.symptoms.filter((item) => item.code !== symptom.code),
                        )
                      }
                      className="rounded px-1 text-slate-600 hover:bg-slate-100"
                    >
                      ×
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {errors.symptoms && (
              <p id={symptomsErrorId} role="alert" className="mt-1 text-xs text-red-700">
                {errors.symptoms}
              </p>
            )}
          </div>

          {create.isError && <Alert kind="error">{errorMessage(create.error)}</Alert>}

          <Button type="submit" loading={create.isPending}>
            Dar de alta al paciente
          </Button>
        </form>
      )}
    </section>
  )
}
