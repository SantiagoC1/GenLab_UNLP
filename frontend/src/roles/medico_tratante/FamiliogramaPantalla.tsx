import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Alert } from '../../components/Alert'
import { Button } from '../../components/Button'
import { RelativeFields } from '../../components/RelativeFields'
import { TextField } from '../../components/TextField'
import { ApiError, errorMessage } from '../../lib/api'
import {
  emptyRelativeForm,
  MAX_RELATIVES,
  relativeToForm,
  useFamilyTree,
  useKinships,
  useRelatives,
  useSaveRelatives,
  validateRelatives,
  type Relative,
  type RelativeForm,
} from '../../lib/familiograma'
import { isValidDni, usePatientByDni, type Patient } from '../../lib/patients'
import { usePathologies } from '../../lib/pathologies'
import type { Errors } from '../../lib/validation'

/**
 * Carga de familiares y familiograma del paciente. El médico busca al paciente por DNI (o llega
 * con `?dni=`), completa sus familiares y genera el familiograma, que se muestra como imagen con
 * texto alternativo. La imagen no se guarda: se pide al módulo cada vez.
 */
export default function FamiliogramaPantalla() {
  const [searchParams] = useSearchParams()
  const initialDni = searchParams.get('dni') ?? ''
  const [dni, setDni] = useState(initialDni)
  const [searchedDni, setSearchedDni] = useState(initialDni)
  const [dniError, setDniError] = useState('')

  const patientQuery = usePatientByDni(searchedDni)
  const patient = patientQuery.data
  const relatives = useRelatives(patient?.id)
  const patientNotFound =
    patientQuery.error instanceof ApiError && patientQuery.error.status === 404

  /** Busca al paciente por el DNI escrito. */
  const search = (event: FormEvent) => {
    event.preventDefault()
    if (!isValidDni(dni)) {
      setDniError('El DNI tiene que tener 7 u 8 dígitos.')
      return
    }
    setDniError('')
    setSearchedDni(dni.trim())
  }

  return (
    <section className="space-y-6">
      <h1 className="text-xl font-semibold text-ink sm:text-2xl">Familiograma del paciente</h1>

      <form onSubmit={search} className="flex flex-wrap items-end gap-3" noValidate>
        <div className="w-full sm:w-64">
          <TextField
            label="DNI del paciente"
            value={dni}
            inputMode="numeric"
            maxLength={8}
            error={dniError || undefined}
            onChange={(event) => setDni(event.target.value)}
          />
        </div>
        <Button type="submit" loading={patientQuery.isFetching}>
          Buscar paciente
        </Button>
      </form>

      {patientNotFound && <Alert kind="warning">No hay un paciente registrado con ese DNI.</Alert>}
      {patientQuery.isError && !patientNotFound && (
        <Alert kind="error">{errorMessage(patientQuery.error)}</Alert>
      )}
      {relatives.isError && <Alert kind="error">{errorMessage(relatives.error)}</Alert>}

      {patient && relatives.data && (
        <RelativesEditor key={patient.id} patient={patient} initial={relatives.data} />
      )}
    </section>
  )
}

interface EditorProps {
  patient: Patient
  initial: Relative[]
}

/**
 * El formulario de familiares de un paciente ya elegido. Parte de lo guardado y se vuelve a montar
 * si cambia el paciente, así no hace falta copiar datos con un efecto. Al enviar con errores el
 * foco pasa a un resumen de cuántos hay.
 */
function RelativesEditor({ patient, initial }: EditorProps) {
  const [forms, setForms] = useState<RelativeForm[]>(() =>
    initial.map((relative, index) => relativeToForm(relative, index)),
  )
  const [errors, setErrors] = useState<Record<number, Errors>>({})
  const nextKey = useRef(initial.length)
  const errorSummary = useRef<HTMLDivElement>(null)
  const errorCount = Object.keys(errors).length

  const kinships = useKinships()
  const pathologies = usePathologies()
  const save = useSaveRelatives(patient.id)
  const tree = useFamilyTree(patient.id)
  const patientDnis = new Set(
    (save.data ?? initial)
      .filter((relative) => relative.linked_patient_id !== null)
      .map((relative) => relative.dni),
  )

  useEffect(() => {
    if (errorCount > 0) errorSummary.current?.focus()
  }, [errors, errorCount])

  /** Suma un familiar vacío al final de la lista. */
  const addRelative = () => {
    setForms((current) => [...current, emptyRelativeForm(nextKey.current)])
    nextKey.current += 1
  }

  /** Cambia solo algunos campos de un familiar. */
  const changeRelative = (key: number, patch: Partial<RelativeForm>) =>
    setForms((current) => current.map((form) => (form.key === key ? { ...form, ...patch } : form)))

  /** Saca a un familiar de la lista. */
  const removeRelative = (key: number) =>
    setForms((current) => current.filter((form) => form.key !== key))

  /** Valida y guarda la lista; con `generate`, después pide el familiograma. */
  const submit = (generate: boolean) => {
    const found = validateRelatives(forms)
    setErrors(found)
    if (Object.keys(found).length > 0) return
    save.mutate(forms, { onSuccess: () => generate && tree.mutate() })
  }

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    submit(false)
  }

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-4">
      <p className="text-sm text-ink-soft">
        Paciente: {patient.first_name} {patient.last_name}. Cargá a sus familiares y generá el
        familiograma.
      </p>

      {kinships.isError && <Alert kind="error">{errorMessage(kinships.error)}</Alert>}

      {errorCount > 0 && (
        <div
          ref={errorSummary}
          tabIndex={-1}
          role="alert"
          className="rounded-control border border-danger-line bg-danger-soft px-3 py-2 text-sm text-danger"
        >
          {errorCount === 1
            ? 'Hay 1 familiar para corregir.'
            : `Hay ${errorCount} familiares para corregir.`}{' '}
          El motivo está debajo de cada campo.
        </div>
      )}

      {forms.length === 0 && <p className="text-sm text-muted">Todavía no cargaste familiares.</p>}
      {forms.map((form, index) => (
        <RelativeFields
          key={form.key}
          number={index + 1}
          form={form}
          kinships={kinships.data ?? []}
          pathologies={pathologies.data ?? []}
          errors={errors[form.key] ?? {}}
          isPatient={form.dni.trim() !== '' && patientDnis.has(form.dni.trim())}
          onChange={(patch) => changeRelative(form.key, patch)}
          onRemove={() => removeRelative(form.key)}
        />
      ))}

      <div className="flex flex-wrap gap-3">
        <Button variant="secondary" onClick={addRelative} disabled={forms.length >= MAX_RELATIVES}>
          Agregar familiar
        </Button>
        <Button type="submit" loading={save.isPending && !tree.isPending}>
          Guardar familiares
        </Button>
        <Button onClick={() => submit(true)} loading={save.isPending || tree.isPending}>
          Guardar y generar familiograma
        </Button>
      </div>

      {save.isError && <Alert kind="error">{errorMessage(save.error)}</Alert>}
      {save.isSuccess && !tree.isPending && !tree.isSuccess && !tree.isError && (
        <Alert kind="success">Se guardaron los familiares.</Alert>
      )}
      {tree.isError && (
        <Alert kind="error">
          {errorMessage(tree.error)} Los familiares quedaron guardados: podés reintentar.
        </Alert>
      )}
      {tree.data && (
        <div className="space-y-3">
          {tree.data.warnings.length > 0 && (
            <Alert kind="warning">
              <ul className="list-disc pl-4">
                {tree.data.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </Alert>
          )}
          <div className="overflow-auto rounded-control border border-line bg-white p-2">
            <img
              src={`data:image/svg+xml;base64,${tree.data.svg_base64}`}
              alt={`Familiograma de ${patient.first_name} ${patient.last_name}`}
            />
          </div>
        </div>
      )}
    </form>
  )
}
