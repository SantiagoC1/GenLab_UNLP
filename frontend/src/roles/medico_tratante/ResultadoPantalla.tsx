
import { useEffect, useState } from 'react'
import { api, ApiError, json } from '../../lib/api'
import { useSearchParams } from 'react-router-dom'
import { useMockActor } from '../../lib/mockIdentity'

type ResultSummary = {
  study_id: number
  state: string
  variant_count: number
  negative: boolean
  completed_at: string
}

type Variant = {
  gene: string
  variant: string
  classification: string
}

type ResultDetail = ResultSummary & {
  pdf_available: boolean
  variants: Variant[] | null
}

type Pathology = {
  name: string
  simulated: boolean
}

type ReanalysisPreview = {
  study_id: number
  pathology: string
  candidate_genes: string[]
  analyzed_genes: string[]
  pending_genes: string[]
  excluded_genes: string[]
  can_request: boolean
  has_pending_request: boolean
  simulated: boolean
}

type ReanalysisRequest = {
  id: number
  study_id: number
  doctor_id: string
  pathology: string
  candidate_genes: string[]
  excluded_genes: string[]
  pending_genes: string[]
  requested_at: string
  status: string
  original_completed_at: string
  uses_existing_raw_data: boolean
  payment_required: boolean | null
  simulated: boolean
}

const DOCTORS = [
  { id: 'doctor-1', name: 'Médico tratante de prueba 1' },
  { id: 'doctor-2', name: 'Médico tratante de prueba 2' },
]

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function errorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : 'No se pudo completar la operación.'
}

function query(params: Record<string, string>): string {
  return new URLSearchParams(params).toString()
}

export default function ResultadoPantalla() {
  const [doctorId, setDoctorId] = useMockActor('medico_tratante')
  const [searchParams] = useSearchParams()
  const requestedStudyId = Number(searchParams.get('study_id'))
  const [results, setResults] = useState<ResultSummary[]>([])
  const [selected, setSelected] = useState<ResultDetail | null>(null)
  const [pathologies, setPathologies] = useState<Pathology[]>([])
  const [pathology, setPathology] = useState('')
  const [preview, setPreview] = useState<ReanalysisPreview | null>(null)
  const [request, setRequest] = useState<ReanalysisRequest | null>(null)
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    let cancelled = false

    setLoading(true)
    setSelected(null)
    setResults([])
    setPreview(null)
    setRequest(null)
    setPathology('')
    setError('')
    setSuccess('')

    Promise.all([
      api<ResultSummary[]>(
        `/bioinformatics/results?${query({
          role: 'medico_tratante',
          actor_id: doctorId,
        })}`,
      ),
      api<Pathology[]>('/bioinformatics/reanalysis/pathologies'),
    ])
      .then(([resultData, pathologyData]) => {
        if (cancelled) return
        setResults(resultData)
        setPathologies(pathologyData)
      })
      .catch((caught) => {
        if (!cancelled) setError(errorMessage(caught))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [doctorId])

  async function viewResult(studyId: number) {
    setBusy(true)
    setError('')
    setSuccess('')
    setSelected(null)
    setPreview(null)
    setRequest(null)
    setPathology('')

    try {
      const [detail, existingRequest] = await Promise.all([
        api<ResultDetail>(
          `/bioinformatics/results/${studyId}?${query({
            role: 'medico_tratante',
            actor_id: doctorId,
          })}`,
        ),
        api<ReanalysisRequest | null>(
          `/bioinformatics/studies/${studyId}/reanalysis?${query({
            doctor_id: doctorId,
          })}`,
        ),
      ])

      setSelected(detail)
      setRequest(existingRequest)
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setBusy(false)
    }
  }
  useEffect(() => {
    if (
      !Number.isSafeInteger(requestedStudyId) ||
      requestedStudyId <= 0 ||
      loading ||
      !results.some((result) => result.study_id === requestedStudyId)
    ) {
      return
    }

    void viewResult(requestedStudyId)
    // The URL is the source of the requested study.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestedStudyId, doctorId, results])

  async function downloadPdf(studyId: number) {
    setError('')

    try {
      const response = await fetch(
        `${API_URL}/bioinformatics/results/${studyId}/pdf?${query({
          role: 'medico_tratante',
          actor_id: doctorId,
        })}`,
      )

      if (!response.ok) {
        throw new Error('No se pudo descargar el PDF.')
      }

      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')

      link.href = url
      link.download = `resultado-estudio-${studyId}.pdf`
      document.body.appendChild(link)
      link.click()
      link.remove()

      URL.revokeObjectURL(url)
    } catch (caught) {
      setError(errorMessage(caught))
    }
  }

  async function previewReanalysis() {
    if (!selected || !pathology) return

    setBusy(true)
    setError('')
    setSuccess('')
    setPreview(null)

    try {
      const data = await api<ReanalysisPreview>(
        `/bioinformatics/studies/${selected.study_id}/reanalysis/preview?${query({
          doctor_id: doctorId,
          pathology,
        })}`,
      )
      setPreview(data)
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setBusy(false)
    }
  }

  async function submitReanalysis() {
    if (!selected || !preview?.can_request) return

    setBusy(true)
    setError('')
    setSuccess('')

    try {
      const data = await api<ReanalysisRequest>(
        `/bioinformatics/studies/${selected.study_id}/reanalysis`,
        {
          method: 'POST',
          ...json({
            doctor_id: doctorId,
            pathology: preview.pathology,
          }),
        },
      )

      setRequest(data)
      setPreview(null)
      setSuccess('La solicitud de reanálisis quedó registrada.')
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 409) {
        setPreview(null)
      }
      setError(errorMessage(caught))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-semibold">Resultado del estudio</h1>
        <p className="mt-2 text-sm text-gray-600">
          Escenarios 37 y 39 · M8-RF6 y M8-RF8.
          Consultá resultados y solicitá un reanálisis.
        </p>
      </header>

      <div className="max-w-md rounded-xl border bg-white p-4">
        <label htmlFor="result-doctor" className="block text-sm font-medium">
          Médico tratante de prueba
        </label>
        <select
          id="result-doctor"
          value={doctorId}
          disabled={busy}
          onChange={(event) => setDoctorId(event.target.value)}
          className="mt-2 w-full rounded-lg border p-3"
        >
          {DOCTORS.map((doctor) => (
            <option key={doctor.id} value={doctor.id}>
              {doctor.name}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <p
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 p-3 text-red-800"
        >
          {error}
        </p>
      )}

      {success && (
        <p
          role="status"
          className="rounded-lg border border-green-200 bg-green-50 p-3 text-green-800"
        >
          {success}
        </p>
      )}

      <div className="rounded-xl border bg-white p-5">
        <h2 className="mb-4 text-lg font-semibold">Resultados disponibles</h2>

        {loading && <p>Cargando...</p>}

        {!loading && results.length === 0 && !error && (
          <p className="text-sm text-gray-600">
            No hay resultados disponibles para este médico.
          </p>
        )}

        <div className="space-y-2">
          {results.map((result) => (
            <div
              key={result.study_id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-lg border p-3"
            >
              <div>
                <p className="font-medium">Estudio #{result.study_id}</p>
                <p className="text-sm text-gray-600">
                  {result.negative
                    ? 'Sin variantes registradas'
                    : `${result.variant_count} variante(s) registrada(s)`}
                </p>
              </div>

              <button
                type="button"
                disabled={busy || loading}
                onClick={() => void viewResult(result.study_id)}
                className="rounded-lg border px-4 py-2 disabled:opacity-50"
              >
                Ver resultado
              </button>
            </div>
          ))}
        </div>
      </div>

      {selected && (
        <>
          <div className="space-y-4 rounded-xl border bg-white p-5">
            <h2 className="text-lg font-semibold">
              Resultado original del estudio #{selected.study_id}
            </h2>

            <p className="text-sm">
              <strong>Estado:</strong> Resultado disponible
            </p>

            <p className="text-sm">
              <strong>Finalizado:</strong>{' '}
              {new Date(selected.completed_at).toLocaleString('es-AR')}
            </p>

            {selected.negative ? (
              <p className="text-sm">
                No se registraron variantes en el análisis simulado.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="p-3">Gen</th>
                      <th className="p-3">Variante</th>
                      <th className="p-3">Clasificación</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(selected.variants ?? []).map((variant) => (
                      <tr
                        key={`${variant.gene}:${variant.variant}`}
                        className="border-b"
                      >
                        <td className="p-3">{variant.gene}</td>
                        <td className="p-3">{variant.variant}</td>
                        <td className="p-3">{variant.classification}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <button
              type="button"
              onClick={() => void downloadPdf(selected.study_id)}
              className="rounded-lg bg-blue-600 px-4 py-2 text-white"
            >
              Descargar PDF original
            </button>
          </div>

          <div className="space-y-4 rounded-xl border bg-white p-5">
            <h2 className="text-lg font-semibold">
              Solicitar reanálisis
            </h2>

            <p className="text-sm text-gray-600">
              Seleccioná una nueva patología sospechada. Se reutilizarán
              los datos crudos originales y se excluirán los genes
              previamente analizados.
            </p>

            {request ? (
              <div className="space-y-2 rounded-lg border p-4">
                <p className="font-medium">
                  Solicitud #{request.id} registrada
                </p>
                <p className="text-sm">
                  <strong>Patología:</strong> {request.pathology}
                </p>
                <p className="text-sm">
                  <strong>Genes pendientes:</strong>{' '}
                  {request.pending_genes.join(', ')}
                </p>
                <p className="text-sm">
                  <strong>Fecha:</strong>{' '}
                  {new Date(request.requested_at).toLocaleString('es-AR')}
                </p>
                <p className="text-sm">
                  Pendiente de definición del flujo posterior.
                  No se generó un cobro ni un nuevo resultado.
                </p>
              </div>
            ) : (
              <>
                <div className="max-w-md">
                  <label
                    htmlFor="reanalysis-pathology"
                    className="block text-sm font-medium"
                  >
                    Nueva patología sospechada
                  </label>

                  <select
                    id="reanalysis-pathology"
                    value={pathology}
                    disabled={busy}
                    onChange={(event) => {
                      setPathology(event.target.value)
                      setPreview(null)
                      setSuccess('')
                    }}
                    className="mt-2 w-full rounded-lg border p-3"
                  >
                    <option value="">Seleccionar patología</option>
                    {pathologies.map((item) => (
                      <option key={item.name} value={item.name}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  type="button"
                  disabled={!pathology || busy}
                  onClick={() => void previewReanalysis()}
                  className="rounded-lg border px-4 py-2 disabled:opacity-50"
                >
                  Consultar genes
                </button>

                {preview && (
                  <div className="space-y-3 rounded-lg border p-4">
                    <p className="text-sm">
                      <strong>Genes de la nueva patología:</strong>{' '}
                      {preview.candidate_genes.join(', ')}
                    </p>

                    <p className="text-sm">
                      <strong>Genes ya analizados:</strong>{' '}
                      {preview.analyzed_genes.join(', ') || 'Ninguno'}
                    </p>

                    <p className="text-sm">
                      <strong>Genes excluidos:</strong>{' '}
                      {preview.excluded_genes.join(', ') || 'Ninguno'}
                    </p>

                    <p className="text-sm">
                      <strong>Genes nuevos por analizar:</strong>{' '}
                      {preview.pending_genes.join(', ') || 'Ninguno'}
                    </p>

                    {!preview.pending_genes.length && (
                      <p className="text-sm text-amber-700">
                        No hay genes nuevos. No se puede solicitar
                        este reanálisis.
                      </p>
                    )}

                    {preview.has_pending_request && (
                      <p className="text-sm text-amber-700">
                        Ya existe una solicitud para este estudio.
                      </p>
                    )}

                    <button
                      type="button"
                      disabled={!preview.can_request || busy}
                      onClick={() => void submitReanalysis()}
                      className="rounded-lg bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
                    >
                      Confirmar solicitud de reanálisis
                    </button>
                  </div>
                )}
              </>
            )}

            <p className="text-xs text-gray-500">
              Simulación de desarrollo. Las asociaciones entre patologías
              y genes son ficticias y no tienen validez clínica.
            </p>
          </div>
        </>
      )}
    </section>
  )
}
