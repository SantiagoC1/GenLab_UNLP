
import { useCallback, useEffect, useState } from 'react'
import { api } from '../../lib/api'
import FedexDateTimePicker from './FedexDateTimePicker'

type Batch = {
  id: number
  state: string
  study_count: number
  is_urgent: boolean
  has_permit: boolean
  can_schedule_pickup: boolean
  scheduled_pickup_at: string | null
  collected_at: string | null
  fedex_url: string | null
}

type Shipment = {
  batch_id: number
  scheduled_pickup_at: string
  collected_at: string | null
  status: string
  tracking_url: string
}

const API_URL =
  import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('es-AR', {
    dateStyle: 'short',
    timeStyle: 'short',
  })
}


export default function RetiroFedexPantalla() {
  const [batches, setBatches] = useState<Batch[]>([])
  const [selectedBatchId, setSelectedBatchId] = useState('')
  const [scheduledAt, setScheduledAt] = useState('')
  const [holidays, setHolidays] = useState<string[]>([])
  const [holidaysLoaded, setHolidaysLoaded] = useState(false)

  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const loadBatches = useCallback(async () => {
    try {
      const result = await api<Batch[]>('/logistics/batches')
      setBatches(result)
      setError('')
    } catch {
      setError('No se pudieron consultar los lotes.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadBatches()
  }, [loadBatches])

  useEffect(() => {
  let active = true

  async function loadHolidays() {
    try {
      const result = await api<string[]>('/logistics/fedex/holidays')

      if (active) {
        setHolidays(result)
        setHolidaysLoaded(true)
      }
    } catch {
      if (active) {
        setHolidaysLoaded(false)
        setError('No se pudo consultar el calendario de días no laborables.')
      }
    }
  }

  void loadHolidays()

  return () => {
    active = false
  }
}, [])

  const selectedBatch = batches.find(
    (batch) => batch.id === Number(selectedBatchId),
  )

  async function handleSchedule() {
    if (!selectedBatch?.can_schedule_pickup || isSubmitting) {
      return
    }

    if (!holidaysLoaded) {
      setError('No está disponible el calendario de días no laborables.')
      return
    }

    const [datePart, timePart] = scheduledAt.split('T')

    if (!datePart || !timePart) {
      setError('Seleccioná una fecha y un horario.')
      return
    }

    const selectedDate = new Date(`${datePart}T${timePart}:00`)

    if (Number.isNaN(selectedDate.getTime())) {
      setError('Seleccioná una fecha y un horario válidos.')
      return
    }

    setIsSubmitting(true)
    setError('')
    setSuccess('')

    try {
      await api<Shipment>(
        `/logistics/batches/${selectedBatch.id}/schedule-pickup`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            scheduled_at: selectedDate.toISOString(),
          }),
        },
      )

      setIsModalOpen(false)
      setSuccess('El retiro se programó correctamente.')
      await loadBatches()
    } catch {
      setIsModalOpen(false)
      setError(
        'No se pudo programar el retiro. Verificá que la fecha sea futura, hábil y entre las 9:00 y las 18:00, y que FedEx esté disponible.',
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="space-y-6 p-6">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">
            Programar retiro con FedEx
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Programá el retiro de lotes autorizados
            por el Ministerio de Salud.
          </p>
        </div>

        <button
          type="button"
          onClick={() => {
            setIsLoading(true)
            void loadBatches()
          }}
          disabled={isLoading}
          className="rounded-lg border px-4 py-2 text-sm disabled:opacity-50"
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

      {success && (
        <p role="status" className="text-sm text-green-700">
          {success}
        </p>
      )}

      {!isLoading && batches.length === 0 && (
        <p>No hay lotes disponibles.</p>
      )}

      {!isLoading && batches.length > 0 && (
        <div className="space-y-4">
          <div className="max-w-xl rounded-xl border bg-white p-5">
            <label
              htmlFor="fedex-batch"
              className="block text-sm font-medium"
            >
              Seleccionar lote
            </label>

            <select
              id="fedex-batch"
              value={selectedBatchId}
              onChange={(event) => {
                setSelectedBatchId(event.target.value)
                setError('')
                setSuccess('')
              }}
              className="mt-2 w-full rounded-lg border p-2"
            >
              <option value="">Elegí un lote</option>
              {batches.map((batch) => (
                <option key={batch.id} value={batch.id}>
                  Lote #{batch.id} — {batch.state}
                  {batch.is_urgent ? ' — Pompe urgente' : ''}
                </option>
              ))}
            </select>

            {selectedBatch && (
              <div className="mt-5 space-y-3">
                <p className="text-sm">
                  Estudios: {selectedBatch.study_count}
                </p>

                <p className="text-sm">
                  Estado: {selectedBatch.state}
                </p>

                {selectedBatch.is_urgent && (
                  <p className="rounded-lg bg-red-50 p-3 text-sm text-red-800">
                    Este lote tiene prioridad Pompe urgente.
                  </p>
                )}

                {selectedBatch.can_schedule_pickup ? (
                  <>
                    <label
                      htmlFor="fedex-date"
                      className="block text-sm font-medium"
                    >
                      Fecha y hora del retiro
                    </label>

                    <FedexDateTimePicker
                      value={scheduledAt}
                      onChange={setScheduledAt}
                      holidays={holidays}
                      disabled={!holidaysLoaded || isSubmitting}
                    />

                    <p className="text-xs text-gray-500">
                      Solo días hábiles, de 9:00 a 18:00.
                      Los feriados también están excluidos.
                    </p>

                    <button
                      type="button"
                      onClick={() => setIsModalOpen(true)}
                      className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
                      disabled={!scheduledAt || !holidaysLoaded || isSubmitting}
                    >
                      Programar retiro
                    </button>
                  </>
                ) : selectedBatch.state === 'RetiroProgramado' ? (
                  <div className="space-y-2">
                    <p className="text-sm text-blue-700">
                      El retiro ya está programado.
                    </p>

                    {selectedBatch.scheduled_pickup_at && (
                      <p className="text-sm">
                        Fecha programada:{' '}
                        {formatDateTime(
                          selectedBatch.scheduled_pickup_at,
                        )}
                      </p>
                    )}

                    {selectedBatch.fedex_url && (
                      <a
                        href={`${API_URL}${selectedBatch.fedex_url}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-block text-sm text-blue-700 underline"
                      >
                        Consultar seguimiento simulado
                      </a>
                    )}
                  </div>
                ) : selectedBatch.state === 'EnViajeACorea' ? (
                  <div className="space-y-2">
                    <p className="text-sm text-green-700">
                      FedEx retiró el lote. Está en viaje a Corea.
                    </p>

                    {selectedBatch.collected_at && (
                      <p className="text-sm">
                        Retirado el:{' '}
                        {formatDateTime(selectedBatch.collected_at)}
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-amber-700">
                    Este lote no está habilitado para programar
                    su retiro. Debe estar autorizado y contar
                    con el permiso del Ministerio.
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {isModalOpen && selectedBatch && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onMouseDown={(event) => {
            if (
              event.target === event.currentTarget &&
              !isSubmitting
            ) {
              setIsModalOpen(false)
            }
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="fedex-dialog-title"
            className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl"
            onKeyDown={(event) => {
              if (event.key === 'Escape' && !isSubmitting) {
                setIsModalOpen(false)
              }
            }}
          >
            <h2
              id="fedex-dialog-title"
              className="text-xl font-semibold"
            >
              Confirmar programación
            </h2>

            <p className="mt-3 text-sm text-gray-600">
              ¿Confirmás la programación del retiro
              del lote #{selectedBatch.id} para la fecha
              y hora seleccionadas?
            </p>

            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                disabled={isSubmitting}
                onClick={() => setIsModalOpen(false)}
                className="rounded-lg border px-4 py-2 text-sm disabled:opacity-50"
              >
                Cancelar
              </button>

              <button
                type="button"
                disabled={isSubmitting}
                onClick={handleSchedule}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white disabled:opacity-50"
              >
                {isSubmitting
                  ? 'Programando...'
                  : 'Confirmar retiro'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
