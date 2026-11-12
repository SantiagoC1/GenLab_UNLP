
import { useCallback, useEffect, useState } from 'react'
import { api, ApiError, json } from '../../lib/api'

type Assignment = {
  study_id: number
  batch_id: number
  analyst_id: string
  analyst_name: string
  assigned_at: string
  state: string
}

type Variant = {
  gene: string
  variant: string
  classification: string
}

type Analysis = {
  study_id: number
  variants: Variant[]
}

type GeneResponse = {
  study_id: number
  genes: string[]
  simulated: boolean
}

type VariantResponse = {
  study_id: number
  gene: string
  variants: Variant[]
  simulated: boolean
}

type Completion = {
  study_id: number
  state: string
  variant_count: number
  negative: boolean
  completed_at: string
  pdf_available: boolean
  notification_count: number
}

const ANALYSTS = [
  { id: 'analyst-1', name: 'Bioinformático de prueba 1' },
  { id: 'analyst-2', name: 'Bioinformático de prueba 2' },
]

function getErrorMessage(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : 'No se pudo completar la operación.'
}

export default function AnalisisPantalla() {
  const [analystId, setAnalystId] = useState('analyst-1')
  const [assignments, setAssignments] = useState<Assignment[]>([])
  const [studyId, setStudyId] = useState<number | null>(null)
  const [genes, setGenes] = useState<string[]>([])
  const [gene, setGene] = useState('')
  const [options, setOptions] = useState<Variant[]>([])
  const [selectedVariant, setSelectedVariant] = useState('')
  const [registered, setRegistered] = useState<Variant[]>([])
  const [completion, setCompletion] = useState<Completion | null>(null)
  const [showConfirmation, setShowConfirmation] = useState(false)
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const loadAssignments = useCallback(async (analyst: string) => {
    const result = await api<Assignment[]>(
      `/bioinformatics/studies/assigned?analyst_id=${encodeURIComponent(analyst)}`,
    )
    setAssignments(result.filter((item) => item.state === 'EnAnalisisPorUnBioinformatico'))
  }, [])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setAssignments([])
    setStudyId(null)
    setGenes([])
    setOptions([])
    setRegistered([])
    setCompletion(null)
    setError('')
    setMessage('')

    api<Assignment[]>(
      `/bioinformatics/studies/assigned?analyst_id=${encodeURIComponent(analystId)}`,
    )
      .then((result) => {
        if (!cancelled) {
          setAssignments(
            result.filter((item) => item.state === 'EnAnalisisPorUnBioinformatico'),
          )
        }
      })
      .catch((caught) => {
        if (!cancelled) setError(getErrorMessage(caught))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [analystId])

  async function openStudy(id: number) {
    setLoading(true)
    setError('')
    setMessage('')
    setCompletion(null)
    setStudyId(null)
    setGene('')
    setOptions([])

    try {
      const query = `analyst_id=${encodeURIComponent(analystId)}`
      const [geneResult, analysisResult] = await Promise.all([
        api<GeneResponse>(
          `/bioinformatics/studies/${id}/analysis/genes?${query}`,
        ),
        api<Analysis>(
          `/bioinformatics/studies/${id}/analysis?${query}`,
        ),
      ])

      setGenes(geneResult.genes)
      setRegistered(analysisResult.variants)
      setStudyId(id)
    } catch (caught) {
      setError(getErrorMessage(caught))
    } finally {
      setLoading(false)
    }
  }

  async function selectGene(value: string) {
    setGene(value)
    setOptions([])
    setSelectedVariant('')
    setError('')

    if (!studyId || !value) return

    setLoading(true)
    try {
      const response = await api<VariantResponse>(
        `/bioinformatics/studies/${studyId}/analysis/genes/${encodeURIComponent(value)}/variants?analyst_id=${encodeURIComponent(analystId)}`,
      )
      setOptions(response.variants)
    } catch (caught) {
      setError(getErrorMessage(caught))
    } finally {
      setLoading(false)
    }
  }

  async function addVariant() {
    if (!studyId || !gene || !selectedVariant || busy) return

    setBusy(true)
    setError('')
    setMessage('')

    try {
      const result = await api<Variant>(
        `/bioinformatics/studies/${studyId}/analysis/variants`,
        {
          method: 'POST',
          ...json({
            analyst_id: analystId,
            gene,
            variant: selectedVariant,
          }),
        },
      )

      setRegistered((current) => [...current, result])
      setSelectedVariant('')
      setMessage('Variante registrada correctamente.')
    } catch (caught) {
      setError(getErrorMessage(caught))
    } finally {
      setBusy(false)
    }
  }

  async function removeVariant(item: Variant) {
    if (!studyId || busy) return

    setBusy(true)
    setError('')
    setMessage('')

    try {
      await api<{ removed: boolean }>(
        `/bioinformatics/studies/${studyId}/analysis/variants/remove`,
        {
          method: 'POST',
          ...json({
            analyst_id: analystId,
            gene: item.gene,
            variant: item.variant,
          }),
        },
      )

      setRegistered((current) =>
        current.filter(
          (value) =>
            value.gene !== item.gene || value.variant !== item.variant,
        ),
      )
      setMessage('Variante quitada correctamente.')
    } catch (caught) {
      setError(getErrorMessage(caught))
    } finally {
      setBusy(false)
    }
  }

  async function completeAnalysis() {
    if (!studyId || busy) return

    setBusy(true)
    setError('')
    setMessage('')

    try {
      const result = await api<Completion>(
        `/bioinformatics/studies/${studyId}/analysis/complete`,
        {
          method: 'POST',
          ...json({ analyst_id: analystId }),
        },
      )

      setCompletion(result)
      setShowConfirmation(false)
      setMessage('El análisis se finalizó correctamente.')
      await loadAssignments(analystId)
    } catch (caught) {
      setError(getErrorMessage(caught))
      setShowConfirmation(false)
    } finally {
      setBusy(false)
    }
  }

  async function downloadPdf() {
    if (!studyId) return

    setError('')

    try {
      const baseUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
      const response = await fetch(
        `${baseUrl}/bioinformatics/studies/${studyId}/analysis/result.pdf?analyst_id=${encodeURIComponent(analystId)}`,
      )

      if (!response.ok) {
        throw new Error('No se pudo descargar el resultado.')
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
          : 'No se pudo descargar el resultado.',
      )
    }
  }

  const selectedOption = options.find(
    (item) => item.variant === selectedVariant,
  )

  return (
    <section className="space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-semibold">
          Registrar variantes y finalizar el análisis
        </h1>
        <p className="mt-2 text-sm text-gray-600">
          Registrá los hallazgos del análisis realizado fuera de GenLab.
          Los genes y variantes mostrados son datos simulados.
        </p>
      </header>

      <div className="max-w-md rounded-xl border bg-white p-4">
        <label htmlFor="analysis-analyst" className="block text-sm font-medium">
          Bioinformático de prueba
        </label>
        <select
          id="analysis-analyst"
          value={analystId}
          disabled={busy}
          onChange={(event) => setAnalystId(event.target.value)}
          className="mt-2 w-full rounded-lg border p-3"
        >
          {ANALYSTS.map((analyst) => (
            <option key={analyst.id} value={analyst.id}>
              {analyst.name}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-red-800">
          {error}
        </p>
      )}

      {message && (
        <p role="status" className="rounded-lg border border-green-200 bg-green-50 p-3 text-green-800">
          {message}
        </p>
      )}

      <div className="rounded-xl border bg-white p-5">
        <h2 className="mb-4 text-lg font-semibold">Mis estudios en análisis</h2>

        {loading && <p className="text-sm">Cargando...</p>}

        {!loading && assignments.length === 0 && (
          <p className="text-sm text-gray-600">
            No tenés estudios pendientes de análisis.
          </p>
        )}

        <div className="flex flex-wrap gap-2">
          {assignments.map((item) => (
            <button
              key={item.study_id}
              type="button"
              disabled={busy || loading}
              onClick={() => void openStudy(item.study_id)}
              className={`rounded-lg border px-4 py-2 text-sm ${
                studyId === item.study_id
                  ? 'border-blue-600 bg-blue-50'
                  : 'bg-white'
              }`}
            >
              Estudio #{item.study_id}
            </button>
          ))}
        </div>
      </div>

      {studyId !== null && !completion && (
        <div className="space-y-5 rounded-xl border bg-white p-5">
          <h2 className="text-lg font-semibold">
            Análisis del estudio #{studyId}
          </h2>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label htmlFor="analysis-gene" className="block text-sm font-medium">
                Gen
              </label>
              <select
                id="analysis-gene"
                value={gene}
                disabled={busy || loading}
                onChange={(event) => void selectGene(event.target.value)}
                className="mt-2 w-full rounded-lg border p-3"
              >
                <option value="">Seleccionar gen</option>
                {genes.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="analysis-variant" className="block text-sm font-medium">
                Variante encontrada
              </label>
              <select
                id="analysis-variant"
                value={selectedVariant}
                disabled={!gene || busy || loading}
                onChange={(event) => setSelectedVariant(event.target.value)}
                className="mt-2 w-full rounded-lg border p-3"
              >
                <option value="">Seleccionar variante</option>
                {options.map((item) => (
                  <option key={item.variant} value={item.variant}>
                    {item.variant}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {selectedOption && (
            <p className="text-sm">
              <strong>Clasificación de Apigen:</strong>{' '}
              {selectedOption.classification}
              <span className="ml-2 text-gray-500">(no editable)</span>
            </p>
          )}

          <button
            type="button"
            disabled={!selectedVariant || busy || loading}
            onClick={() => void addVariant()}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            Registrar variante
          </button>

          <div>
            <h3 className="mb-3 font-semibold">Variantes registradas</h3>

            {registered.length === 0 ? (
              <p className="text-sm text-gray-600">
                No se registraron variantes. Podés finalizar el análisis
                sin hallazgos.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="p-3">Gen</th>
                      <th className="p-3">Variante</th>
                      <th className="p-3">Clasificación</th>
                      <th className="p-3">Acción</th>
                    </tr>
                  </thead>
                  <tbody>
                    {registered.map((item) => (
                      <tr key={`${item.gene}:${item.variant}`} className="border-b">
                        <td className="p-3">{item.gene}</td>
                        <td className="p-3">{item.variant}</td>
                        <td className="p-3">{item.classification}</td>
                        <td className="p-3">
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => void removeVariant(item)}
                            className="rounded-lg border px-3 py-2 disabled:opacity-50"
                          >
                            Quitar
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <button
            type="button"
            disabled={busy || loading}
            onClick={() => setShowConfirmation(true)}
            className="rounded-lg bg-green-700 px-5 py-3 font-medium text-white disabled:opacity-50"
          >
            Finalizar análisis
          </button>
        </div>
      )}

      {completion && studyId !== null && (
        <div className="space-y-3 rounded-xl border bg-white p-5">
          <h2 className="text-lg font-semibold">
            Resultado disponible — Estudio #{studyId}
          </h2>
          <p>
            {completion.negative
              ? 'Sin variantes registradas (resultado negativo simulado).'
              : `${completion.variant_count} variante(s) registrada(s).`}
          </p>
          <p className="text-sm text-gray-600">
            Se registraron {completion.notification_count} avisos por
            correo simulados.
          </p>
          <button
            type="button"
            onClick={() => void downloadPdf()}
            className="rounded-lg border px-4 py-2"
          >
            Descargar resultado PDF
          </button>
        </div>
      )}

      {showConfirmation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="complete-analysis-title"
            className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl"
          >
            <h2 id="complete-analysis-title" className="text-xl font-semibold">
              Confirmar finalización
            </h2>
            <p className="mt-3 text-sm">
              ¿Querés finalizar el estudio #{studyId} con{' '}
              {registered.length} variante(s) registrada(s)?
            </p>
            <p className="mt-3 text-sm text-gray-600">
              Después de confirmar no podrás modificar este análisis.
              Se generará un resultado PDF simulado.
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                disabled={busy}
                onClick={() => setShowConfirmation(false)}
                className="rounded-lg border px-4 py-2"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => void completeAnalysis()}
                className="rounded-lg bg-green-700 px-4 py-2 text-white disabled:opacity-50"
              >
                {busy ? 'Finalizando...' : 'Confirmar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
