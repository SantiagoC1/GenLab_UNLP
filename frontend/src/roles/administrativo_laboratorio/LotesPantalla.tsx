
import { useCallback, useEffect, useState } from 'react'
import { api } from '../../lib/api'

type Batch = {
  id: number
  state: string
  study_count: number
  is_urgent: boolean
  closed_at: string | null
  authorized_at: string | null
  has_csv: boolean
  has_permit: boolean
  authorization_error: string | null
  can_schedule_pickup: boolean
}

const API_URL =
  import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('es-AR', {
    dateStyle: 'short',
    timeStyle: 'short',
  })
}

function getStatusClasses(state: string): string {
  if (state === 'Autorizado') {
    return 'bg-green-100 text-green-800'
  }

  if (state === 'Cerrado') {
    return 'bg-amber-100 text-amber-800'
  }

  return 'bg-gray-100 text-gray-700'
}

export default function LotesPantalla() {
  const [batches, setBatches] = useState<Batch[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  const loadBatches = useCallback(async () => {
    setError('')

    try {
      const result = await api<Batch[]>('/logistics/batches')
      setBatches(result)
    } catch {
      setError('No se pudo cargar la información de los lotes.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadBatches()
  }, [loadBatches])

  return (
    <section className="space-y-6 p-6">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">
            Lotes de estudios
          </h1>

          <p className="mt-1 text-sm text-gray-500">
            Consultá el estado de los lotes y sus
            autorizaciones del Ministerio de Salud.
          </p>
        </div>

        <button
          type="button"
          onClick={() => {
            setIsLoading(true)
            void loadBatches()
          }}
          disabled={isLoading}
          className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
        >
          Actualizar
        </button>
      </header>

      {isLoading && (
        <p role="status">Cargando lotes...</p>
      )}

      {error && (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      )}

      {!isLoading && !error && batches.length === 0 && (
        <div className="rounded-lg border bg-white p-6">
          <p className="text-gray-600">
            Todavía no se registraron lotes de estudios.
          </p>
        </div>
      )}

      {!isLoading && batches.length > 0 && (
        <div className="grid gap-4">
          {batches.map((batch) => (
            <article
              key={batch.id}
              className="rounded-xl border bg-white p-5 shadow-sm"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold">
                    Lote #{batch.id}
                  </h2>
                  {batch.is_urgent && (
                    <span className="mt-2 inline-flex rounded-full bg-red-100 px-3 py-1 text-xs font-semibold text-red-800">
                      Pompe urgente
                    </span>
                  )}
                  <p className="mt-1 text-sm text-gray-600">
                    {batch.study_count} de 10 estudios
                  </p>

                </div>

                <span
                  className={`rounded-full px-3 py-1 text-xs font-medium ${getStatusClasses(batch.state)}`}
                >
                  {batch.state}
                </span>
              </div>

              <div className="mt-4 space-y-2 text-sm text-gray-600">
                {batch.is_urgent && (
                  <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
                    Este lote se cerró anticipadamente porque contiene
                    un estudio con prioridad Pompe urgente.
                    Requiere el permiso del Ministerio de Salud y
                    atención prioritaria para programar su retiro.
                  </p>
                )}

                {batch.closed_at && (
                  <p>
                    Cierre: {formatDateTime(batch.closed_at)}
                  </p>
                )}

                {batch.closed_at && (
                  <p>
                    Cierre: {formatDateTime(batch.closed_at)}
                  </p>
                )}

                {batch.authorized_at && (
                  <p>
                    Autorización:{' '}
                    {formatDateTime(batch.authorized_at)}
                  </p>
                )}

                {batch.state === 'Abierto' && (
                  <p>
                    El lote continúa recibiendo estudios.
                    Se cerrará al completar 10.
                  </p>
                )}

                {batch.state === 'Cerrado' && (
                  <p className="text-amber-700">
                    El lote está cerrado, pero todavía no
                    cuenta con un permiso del Ministerio.
                  </p>
                )}

                {batch.state === 'Autorizado' && (
                  <p className="text-green-700">
                    El Ministerio devolvió un permiso simulado.
                    El lote cumple la condición de autorización
                    para programar su retiro.
                  </p>
                )}

                {batch.authorization_error && (
                  <p role="alert" className="text-red-700">
                    {batch.authorization_error}
                  </p>
                )}
              </div>

              {(batch.has_csv || batch.has_permit) && (
                <div className="mt-5 flex flex-wrap gap-3 border-t pt-4">
                  {batch.has_csv && (
                    <a
                      href={`${API_URL}/logistics/batches/${batch.id}/csv`}
                      download
                      className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                    >
                      Descargar CSV
                    </a>
                  )}

                  {batch.has_permit && (
                    <a
                      href={`${API_URL}/logistics/batches/${batch.id}/permit`}
                      download
                      className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
                    >
                      Descargar permiso PDF
                    </a>
                  )}
                </div>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
