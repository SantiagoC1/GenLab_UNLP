
import { useEffect, useState } from 'react'
import { api, ApiError } from '../../lib/api'
import { useSearchParams } from 'react-router-dom'
import { useMockActor } from '../../lib/mockIdentity'

type ResultSummary = {
  study_id: number
  state: string
  variant_count: number
  negative: boolean
  completed_at: string
}

const PATIENTS = [
  { id: 'patient-1', name: 'Paciente de prueba 1' },
  { id: 'patient-2', name: 'Paciente de prueba 2' },
]

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export default function ResultadoPantalla() {
  const [patientId, setPatientId] = useMockActor('paciente')
  const [searchParams] = useSearchParams()
  const requestedStudyId = Number(searchParams.get('study_id'))
  const [results, setResults] = useState<ResultSummary[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')

    api<ResultSummary[]>(
      `/bioinformatics/results?role=paciente&actor_id=${encodeURIComponent(patientId)}`,
    )
      .then((data) => {
        if (!cancelled) setResults(data)
      })
      .catch((caught) => {
        if (!cancelled) {
          setError(
            caught instanceof ApiError
              ? caught.message
              : 'No se pudieron cargar los resultados.',
          )
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [patientId])

  async function downloadPdf(studyId: number) {
    setError('')

    try {
      const response = await fetch(
        `${API_URL}/bioinformatics/results/${studyId}/pdf?role=paciente&actor_id=${encodeURIComponent(patientId)}`,
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
      setError(
        caught instanceof Error
          ? caught.message
          : 'No se pudo descargar el PDF.',
      )
    }
  }

  return (
    <section className="space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-semibold">
          Descargar el resultado del estudio
        </h1>
        <p className="mt-2 text-sm text-gray-600">
          Escenario 38 · M8-RF7. Descargá los resultados disponibles
          desde la plataforma.
        </p>
      </header>

      <div className="max-w-md rounded-xl border bg-white p-4">
        <label htmlFor="result-patient" className="block text-sm font-medium">
          Paciente de prueba
        </label>
        <select
          id="result-patient"
          value={patientId}
          onChange={(event) => setPatientId(event.target.value)}
          className="mt-2 w-full rounded-lg border p-3"
        >
          {PATIENTS.map((patient) => (
            <option key={patient.id} value={patient.id}>
              {patient.name}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-red-800">
          {error}
        </p>
      )}

      <div className="rounded-xl border bg-white p-5">
        <h2 className="mb-4 text-lg font-semibold">
          Mis resultados disponibles
        </h2>

        {loading && <p>Cargando...</p>}

        {!loading && results.length === 0 && (
          <p className="text-sm text-gray-600">
            Todavía no hay resultados disponibles.
          </p>
        )}

        <div className="space-y-3">
          {results.map((result) => (
            <div
              key={result.study_id}
              className={`flex flex-wrap items-center justify-between gap-3 rounded-lg border p-4 ${
                result.study_id === requestedStudyId
                  ? 'border-teal-600 bg-teal-50'
                  : ''
              }`}
            >
              <div>
                <p className="font-medium">
                  Estudio #{result.study_id}
                </p>
                <p className="text-sm text-gray-600">
                  Resultado disponible
                </p>
              </div>

              <button
                type="button"
                disabled={loading}
                onClick={() => void downloadPdf(result.study_id)}
                className="rounded-lg bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
              >
                Descargar PDF
              </button>
            </div>
          ))}
        </div>
      </div>

      <p className="text-xs text-gray-500">
        Los resultados son ficticios y no tienen validez clínica.
        El PDF se descarga desde la plataforma; no se envía adjunto por correo.
      </p>
    </section>
  )
}
