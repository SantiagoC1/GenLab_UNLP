import { useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Alert } from '../../components/Alert'
import { Button } from '../../components/Button'
import { TextField } from '../../components/TextField'
import { ApiError, errorMessage } from '../../lib/api'
import { isValidDni, usePatientByDni } from '../../lib/patients'
import { usePathologies } from '../../lib/pathologies'
import {
  normalizeGene,
  ORIGIN_LABELS,
  useCreateStudy,
  useStudyGenes,
  type CreatedStudy,
  type StudyGene,
} from '../../lib/studies'

/**
 * Alta del estudio: el médico busca al paciente, elige las patologías, revisa los genes que
 * devuelve Apigen, agrega los que quiera y solicita el estudio. Puede llegar con `?dni=` desde el
 * alta de paciente. La lista de genes está en una región `aria-live` y el origen de cada gen se
 * escribe con texto, no solo con color.
 */
export default function AltaEstudioPantalla() {
  const [searchParams] = useSearchParams()
  const initialDni = searchParams.get('dni') ?? ''
  const [dni, setDni] = useState(initialDni)
  const [searchedDni, setSearchedDni] = useState(initialDni)
  const [dniError, setDniError] = useState('')
  const [pathologyIds, setPathologyIds] = useState<number[]>([])
  const [secondaryFindings, setSecondaryFindings] = useState(false)
  const [manualGenes, setManualGenes] = useState<string[]>([])
  const [manualText, setManualText] = useState('')
  const [created, setCreated] = useState<CreatedStudy | null>(null)

  const patientQuery = usePatientByDni(searchedDni)
  const pathologies = usePathologies()
  const genesQuery = useStudyGenes(pathologyIds, secondaryFindings)
  const create = useCreateStudy()

  const patient = patientQuery.data
  const patientNotFound =
    patientQuery.error instanceof ApiError && patientQuery.error.status === 404
  const apiGenes = genesQuery.data?.genes ?? []
  const addedGenes: StudyGene[] = manualGenes
    .filter((gene) => !apiGenes.some((item) => item.gene === gene))
    .map((gene) => ({ gene, origin: 'manual' }))
  const shownGenes = [...apiGenes, ...addedGenes]
  const canRequest = Boolean(patient) && pathologyIds.length > 0 && genesQuery.isSuccess

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

  /** Agrega o quita una patología de la lista sospechada. */
  const togglePathology = (id: number) =>
    setPathologyIds((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    )

  /** Suma el gen escrito a la lista, salvo que esté vacío o ya figure. */
  const addManualGene = () => {
    const gene = normalizeGene(manualText)
    if (gene && !shownGenes.some((item) => item.gene === gene)) {
      setManualGenes([...manualGenes, gene])
    }
    setManualText('')
  }

  /** Solicita el estudio con lo que eligió el médico. */
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (!patient || !canRequest) return
    create.mutate(
      {
        patient_id: patient.id,
        pathology_ids: pathologyIds,
        secondary_findings: secondaryFindings,
        manual_genes: manualGenes,
      },
      { onSuccess: setCreated },
    )
  }

  return (
    <section className="space-y-6">
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">Dar de alta el estudio</h1>

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

      {patientNotFound && (
        <Alert>
          No hay un paciente con ese DNI.{' '}
          <Link className="font-medium underline" to="/medico_tratante/alta-paciente">
            Dar de alta al paciente
          </Link>
        </Alert>
      )}
      {patientQuery.isError && !patientNotFound && (
        <Alert kind="error">{errorMessage(patientQuery.error)}</Alert>
      )}

      {created && (
        <Alert kind="success">
          Se solicitó el estudio {created.id} de {patient?.first_name} {patient?.last_name}. Estado:{' '}
          {created.state}.{created.pompe_urgent ? ' Pompe urgente.' : ''}
        </Alert>
      )}

      {patient && !created && (
        <form onSubmit={submit} noValidate className="space-y-4">
          <p className="text-sm text-slate-800">
            Paciente: {patient.first_name} {patient.last_name} (DNI {patient.dni})
          </p>

          <fieldset>
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
                    checked={pathologyIds.includes(pathology.id)}
                    onChange={() => togglePathology(pathology.id)}
                  />
                  {pathology.name}
                </label>
              ))}
            </div>
          </fieldset>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={secondaryFindings}
              onChange={(event) => setSecondaryFindings(event.target.checked)}
            />
            Evaluar hallazgos secundarios
          </label>

          <div aria-live="polite" className="space-y-2">
            <h2 className="text-sm font-medium text-slate-800">Genes a analizar</h2>
            {pathologyIds.length === 0 && (
              <p className="text-sm text-slate-600">Elegí al menos una patología.</p>
            )}
            {genesQuery.isFetching && <p className="text-sm text-slate-600">Buscando los genes…</p>}
            {genesQuery.isError && <Alert kind="error">{errorMessage(genesQuery.error)}</Alert>}
            {shownGenes.length > 0 && (
              <ul aria-label="Genes a analizar" className="flex flex-wrap gap-2">
                {shownGenes.map((item) => (
                  <li
                    key={item.gene}
                    className="flex items-center gap-2 rounded-md border border-slate-300 bg-white px-2 py-1 text-sm"
                  >
                    {item.gene} · {ORIGIN_LABELS[item.origin]}
                    {item.origin === 'manual' && (
                      <button
                        type="button"
                        aria-label={`Quitar ${item.gene}`}
                        onClick={() =>
                          setManualGenes(manualGenes.filter((gene) => gene !== item.gene))
                        }
                        className="rounded px-1 text-slate-600 hover:bg-slate-100"
                      >
                        ×
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="flex flex-wrap items-end gap-3">
            <div className="w-full sm:w-64">
              <TextField
                label="Agregar un gen"
                value={manualText}
                onChange={(event) => setManualText(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    event.preventDefault()
                    addManualGene()
                  }
                }}
              />
            </div>
            <Button type="button" variant="secondary" onClick={addManualGene}>
              Agregar gen
            </Button>
          </div>

          {create.isError && <Alert kind="error">{errorMessage(create.error)}</Alert>}

          <Button type="submit" loading={create.isPending} disabled={!canRequest}>
            Solicitar estudio
          </Button>
        </form>
      )}
    </section>
  )
}
