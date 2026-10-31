
import { useCallback, useEffect, useState } from 'react'
import { api, ApiError, json } from '../../lib/api'

type AvailableStudy = {
  id: number
  batch_id: number
  state: string
  pompe_urgent: boolean
  arrived_at: string
  pathology: string
}

type StudyGenes = {
  study_id: number
  pathology: string
  genes: string[]
  simulated: boolean
}

type StudyAssignment = {
  study_id: number
  batch_id: number
  analyst_id: string
  analyst_name: string
  assigned_at: string
  state: string
}

const ANALYSTS = [
  { id: 'analyst-1', name: 'Bioinformático de prueba 1' },
  { id: 'analyst-2', name: 'Bioinformático de prueba 2' },
]

function formatDate(value: string): string {
  return new Date(value).toLocaleString('es-AR')
}

export default function EstudiosDisponiblesPantalla() {
  const [studies, setStudies] = useState<AvailableStudy[]>([])
  const [assignedStudies, setAssignedStudies] = useState<
    StudyAssignment[]
  >([])

  const [analystId, setAnalystId] = useState('analyst-1')
  const [selectedStudy, setSelectedStudy] =
    useState<AvailableStudy | null>(null)
  const [genes, setGenes] = useState<StudyGenes | null>(null)

  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingGenes, setIsLoadingGenes] = useState(false)
  const [isTaking, setIsTaking] = useState(false)

  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const loadStudies = useCallback(
    async (selectedAnalyst: string) => {
      try {
        const [available, assigned] = await Promise.all([
          api<AvailableStudy[]>(
            '/bioinformatics/studies/available',
          ),
          api<StudyAssignment[]>(
            `/bioinformatics/studies/assigned?analyst_id=${encodeURIComponent(
              selectedAnalyst,
            )}`,
          ),
        ])

        setStudies(available)
        setAssignedStudies(assigned)
        setError('')
      } catch {
        setError('No se pudieron consultar los estudios.')
      } finally {
        setIsLoading(false)
      }
    },
    [],
  )

  useEffect(() => {
    void loadStudies(analystId)
  }, [analystId, loadStudies])

  async function openStudy(study: AvailableStudy) {
    setSelectedStudy(study)
    setGenes(null)
    setError('')
    setSuccess('')
    setIsLoadingGenes(true)

    try {
      const result = await api<StudyGenes>(
        `/bioinformatics/studies/${study.id}/genes`,
      )

      setGenes(result)
    } catch (caughtError) {
      setSelectedStudy(null)

      if (caughtError instanceof ApiError) {
        setError(caughtError.message)
      } else {
        setError('No se pudo consultar la lista de genes.')
      }

      await loadStudies(analystId)
    } finally {
      setIsLoadingGenes(false)
    }
  }

  async function handleTakeStudy() {
    if (!selectedStudy || isTaking) return

    setIsTaking(true)
    setError('')
    setSuccess('')

    try {
      const result = await api<StudyAssignment>(
        `/bioinformatics/studies/${selectedStudy.id}/take`,
        {
          method: 'POST',
          ...json({ analyst_id: analystId }),
        },
      )

      setSelectedStudy(null)
      setGenes(null)

      await loadStudies(analystId)

      setSuccess(
        `El estudio #${result.study_id} fue asignado correctamente a ${result.analyst_name}.`,
      )
    } catch (caughtError) {
      setSelectedStudy(null)
      setGenes(null)

      if (caughtError instanceof ApiError) {
        setError(caughtError.message)
      } else {
        setError('No se pudo tomar el estudio.')
      }

      await loadStudies(analystId)
    } finally {
      setIsTaking(false)
    }
  }

  return (
    <section className="space-y-6 p-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">
            Estudios disponibles
          </h1>

          <p className="mt-2 text-sm text-gray-600">
            Consultá los estudios recibidos desde Corea y
            seleccioná uno para comenzar su análisis.
          </p>
        </div>

        <button
          type="button"
          disabled={isLoading || isTaking}
          onClick={() => {
            setIsLoading(true)
            void loadStudies(analystId)
          }}
          className="rounded-lg border px-4 py-2 text-sm disabled:opacity-50"
        >
          Actualizar
        </button>
      </header>

      <div className="max-w-sm rounded-xl border bg-white p-4">
        <label
          htmlFor="analyst-selector"
          className="block text-sm font-medium"
        >
          Bioinformático de prueba
        </label>

        <select
          id="analyst-selector"
          value={analystId}
          disabled={isTaking}
          onChange={(event) => {
            setAnalystId(event.target.value)
            setSelectedStudy(null)
            setGenes(null)
            setError('')
            setSuccess('')
            setIsLoading(true)
          }}
          className="mt-2 w-full rounded-lg border p-3"
        >
          {ANALYSTS.map((analyst) => (
            <option key={analyst.id} value={analyst.id}>
              {analyst.name}
            </option>
          ))}
        </select>

        <p className="mt-2 text-xs text-gray-500">
          Selector disponible únicamente para probar la
          asignación entre distintos usuarios.
        </p>
      </div>

      {error && (
        <p
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800"
        >
          {error}
        </p>
      )}

      {success && (
        <p
          role="status"
          className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800"
        >
          {success}
        </p>
      )}

      <div className="space-y-4">
        <h2 className="text-lg font-semibold">
          Pendientes de asignación
        </h2>

        {isLoading ? (
          <p>Cargando estudios...</p>
        ) : studies.length === 0 ? (
          <div className="rounded-xl border bg-white p-5">
            No hay estudios disponibles para tomar.
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border bg-white">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="p-4">Estudio</th>
                  <th className="p-4">Lote</th>
                  <th className="p-4">Prioridad</th>
                  <th className="p-4">Llegada</th>
                  <th className="p-4">Acción</th>
                </tr>
              </thead>

              <tbody>
                {studies.map((study) => (
                  <tr key={study.id} className="border-t">
                    <td className="p-4 font-medium">
                      #{study.id}
                    </td>
                    <td className="p-4">
                      #{study.batch_id}
                    </td>
                    <td className="p-4">
                      {study.pompe_urgent ? (
                        <span className="font-semibold text-red-700">
                          Pompe urgente
                        </span>
                      ) : (
                        'Normal'
                      )}
                    </td>
                    <td className="p-4">
                      {formatDate(study.arrived_at)}
                    </td>
                    <td className="p-4">
                      <button
                        type="button"
                        onClick={() => void openStudy(study)}
                        className="rounded-lg border px-3 py-2 font-medium"
                      >
                        Ver genes y tomar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="space-y-4">
        <h2 className="text-lg font-semibold">
          Mis estudios asignados
        </h2>

        {assignedStudies.length === 0 ? (
          <div className="rounded-xl border bg-white p-5 text-sm">
            Este bioinformático todavía no tiene estudios asignados.
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border bg-white">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="p-4">Estudio</th>
                  <th className="p-4">Lote</th>
                  <th className="p-4">Estado</th>
                  <th className="p-4">Asignado el</th>
                </tr>
              </thead>

              <tbody>
                {assignedStudies.map((assignment) => (
                  <tr
                    key={assignment.study_id}
                    className="border-t"
                  >
                    <td className="p-4 font-medium">
                      #{assignment.study_id}
                    </td>
                    <td className="p-4">
                      #{assignment.batch_id}
                    </td>
                    <td className="p-4">
                      En análisis
                    </td>
                    <td className="p-4">
                      {formatDate(assignment.assigned_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selectedStudy && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="study-dialog-title"
            className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl"
          >
            <h2
              id="study-dialog-title"
              className="text-xl font-semibold"
            >
              Estudio #{selectedStudy.id}
            </h2>

            <p className="mt-3 text-sm">
              <strong>Patología sospechada:</strong>{' '}
              {selectedStudy.pathology}
            </p>

            {selectedStudy.pompe_urgent && (
              <p className="mt-2 font-semibold text-red-700">
                Prioridad Pompe urgente
              </p>
            )}

            <h3 className="mt-5 font-semibold">
              Genes para el análisis
            </h3>

            {isLoadingGenes ? (
              <p className="mt-2 text-sm">
                Consultando genes...
              </p>
            ) : genes ? (
              <div className="mt-3 space-y-3">
                <ul className="list-inside list-disc text-sm">
                  {genes.genes.map((gene) => (
                    <li key={gene}>{gene}</li>
                  ))}
                </ul>

                <p className="rounded-lg bg-amber-50 p-3 text-xs text-amber-900">
                  Lista generada por un simulador.
                  No representa una recomendación clínica.
                </p>
              </div>
            ) : (
              <p className="mt-2 text-sm">
                No se pudo obtener la lista de genes.
              </p>
            )}

            <p className="mt-4 text-sm text-gray-600">
              Si confirmás, el estudio quedará asignado a{' '}
              <strong>
                {ANALYSTS.find(
                  (analyst) => analyst.id === analystId,
                )?.name}
              </strong>{' '}
              y dejará de estar disponible para otros
              bioinformáticos.
            </p>

            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                disabled={isTaking}
                onClick={() => {
                  setSelectedStudy(null)
                  setGenes(null)
                }}
                className="rounded-lg border px-4 py-2 text-sm disabled:opacity-50"
              >
                Cancelar
              </button>

              <button
                type="button"
                disabled={
                  isTaking ||
                  isLoadingGenes ||
                  !genes
                }
                onClick={() => void handleTakeStudy()}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                {isTaking
                  ? 'Asignando...'
                  : 'Confirmar asignación'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
