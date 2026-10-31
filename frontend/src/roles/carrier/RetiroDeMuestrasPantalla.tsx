
import { useEffect, useState } from 'react'
import { api } from '../../lib/api'

type RouteStop = {
  laboratory_id: number
  laboratory: string
  address: string
  province: string
  position: number
  picked_up_at: string | null
}

type DailyRoute = {
  id: number | null
  date: string
  province: string | null
  arrived_at: string | null
  stops: RouteStop[]
}

type PickupResponse = {
  laboratory_id: number
  picked_up_at: string
  status: string
}

function getLocalDate(): string {
  const now = new Date()

  return new Date(
    now.getTime() - now.getTimezoneOffset() * 60000,
  )
    .toISOString()
    .slice(0, 10)
}

function formatDate(value: string): string {
  const [year, month, day] = value.split('-')

  return `${day}/${month}/${year}`
}

export default function RetiroDeMuestrasPantalla() {
  const [selectedDate] = useState(getLocalDate)
  const [dailyRoute, setDailyRoute] = useState<DailyRoute | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [selectedStop, setSelectedStop] = useState<RouteStop | null>(null)

  useEffect(() => {
    let isActive = true

    api<DailyRoute>(
      `/logistics/daily-route?date=${encodeURIComponent(selectedDate)}`,
    )
      .then((route) => {
        if (isActive) {
          setDailyRoute(route)
          setError('')
        }
      })
      .catch(() => {
        if (isActive) {
          setError('No se pudo cargar el recorrido del día.')
        }
      })
      .finally(() => {
        if (isActive) {
          setIsLoading(false)
        }
      })

    return () => {
      isActive = false
    }
  }, [selectedDate])

  const stops = [...(dailyRoute?.stops ?? [])].sort(
    (a, b) => a.position - b.position,
  )

  const nextPendingStop = stops.find(
    (stop) => stop.picked_up_at === null,
  )

  function openConfirmation(stop: RouteStop) {
    if (isSubmitting) {
      return
    }

    if (nextPendingStop?.laboratory_id !== stop.laboratory_id) {
      return
    }

    setError('')
    setSuccess('')
    setSelectedStop(stop)
  }

  function closeConfirmation() {
    if (!isSubmitting) {
      setSelectedStop(null)
    }
  }

  async function handlePickup() {
    if (!selectedStop || isSubmitting) {
      return
    }

    const stop = selectedStop

    setIsSubmitting(true)
    setError('')
    setSuccess('')

    try {
      await api<PickupResponse>(
        `/logistics/daily-route/stops/${stop.laboratory_id}/pickup?date=${encodeURIComponent(selectedDate)}`,
        { method: 'POST' },
      )

      setSelectedStop(null)

      setSuccess(
        `Se registró correctamente el retiro de muestras de ${stop.laboratory}.`,
      )

      try {
        const updatedRoute = await api<DailyRoute>(
          `/logistics/daily-route?date=${encodeURIComponent(selectedDate)}`,
        )

        setDailyRoute(updatedRoute)
      } catch {
        setError(
          'El retiro fue registrado, pero no se pudo actualizar el recorrido. Recargá la página para ver el estado actual.',
        )
      }
    } catch {
      setSelectedStop(null)

      setError(
        'No se pudo confirmar el retiro. Verificá el estado del recorrido antes de volver a intentarlo.',
      )

      try {
        const updatedRoute = await api<DailyRoute>(
          `/logistics/daily-route?date=${encodeURIComponent(selectedDate)}`,
        )

        setDailyRoute(updatedRoute)
      } catch {
        // Preserve the original error message.
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="space-y-5 p-6">
      <header>
        <h1 className="text-2xl font-semibold">
          Retiro de muestras
        </h1>

        <p className="text-sm text-gray-500">
          Registrá el retiro de las muestras de cada laboratorio.
        </p>
      </header>

      <p className="text-sm text-gray-600">
        Los laboratorios deben completarse en el orden establecido
        por el recorrido.
      </p>

      {isLoading ? (
        <p role="status">Cargando recorrido...</p>
      ) : !dailyRoute?.id ? (
        <p>No tenés un recorrido asignado para hoy.</p>
      ) : (
        <>
          <p className="text-sm">
            Fecha: {formatDate(selectedDate)} · Provincia:{' '}
            {dailyRoute.province}
          </p>

          {stops.length > 0 && !nextPendingStop && (
            <p className="rounded-lg bg-green-50 p-3 text-green-800">
              Se completaron todos los retiros del recorrido.
            </p>
          )}

          <ol className="space-y-3">
            {stops.map((stop) => {
              const isCompleted = stop.picked_up_at !== null
              const isNext =
                nextPendingStop?.laboratory_id === stop.laboratory_id

              return (
                <li
                  key={stop.laboratory_id}
                  className="rounded-lg border bg-white p-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h2 className="font-semibold">
                        {stop.position}. {stop.laboratory}
                      </h2>

                      <p className="mt-1 text-sm text-gray-600">
                        {stop.address}, {stop.province}
                      </p>

                      <p
                        className={`mt-2 text-sm font-medium ${
                          isCompleted
                            ? 'text-green-700'
                            : 'text-amber-700'
                        }`}
                      >
                        {isCompleted
                          ? 'Completado'
                          : 'Sin recolectar'}
                      </p>
                    </div>

                    {!isCompleted && (
                      <button
                        type="button"
                        disabled={!isNext || isSubmitting}
                        onClick={() => openConfirmation(stop)}
                        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300"
                      >
                        Confirmar retiro
                      </button>
                    )}
                  </div>
                </li>
              )
            })}
          </ol>
        </>
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

      {selectedStop && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              closeConfirmation()
            }
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="pickup-dialog-title"
            aria-describedby="pickup-dialog-description"
            className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl"
            onKeyDown={(event) => {
              if (event.key === 'Escape') {
                closeConfirmation()
              }
            }}
          >
            <h2
              id="pickup-dialog-title"
              className="text-xl font-semibold text-gray-900"
            >
              Confirmar retiro de muestras
            </h2>

            <p
              id="pickup-dialog-description"
              className="mt-3 text-sm text-gray-600"
            >
              ¿Confirmás que retiraste todas las muestras
              asignadas al siguiente laboratorio?
            </p>

            <div className="mt-4 rounded-lg bg-gray-50 p-4">
              <p className="font-medium text-gray-900">
                {selectedStop.laboratory}
              </p>

              <p className="mt-1 text-sm text-gray-600">
                {selectedStop.address}, {selectedStop.province}
              </p>
            </div>

            <p className="mt-4 text-sm text-gray-500">
              Una vez confirmado, el laboratorio quedará marcado
              como completado.
            </p>

            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                disabled={isSubmitting}
                onClick={closeConfirmation}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Cancelar
              </button>

              <button
                type="button"
                disabled={isSubmitting}
                onClick={handlePickup}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {isSubmitting
                  ? 'Registrando...'
                  : 'Confirmar retiro'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
