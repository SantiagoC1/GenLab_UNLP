
import { useEffect, useState } from 'react'
import { api } from '../../lib/api'

type RouteStop = {
  laboratory_id: number
  laboratory: string
  address: string
  province: string
  position: number
  latitude: number | null
  longitude: number | null
  picked_up_at: string | null
}

type DailyRoute = {
  id: number | null
  date: string
  province: string | null
  arrived_at: string | null
  stops: RouteStop[]
}

function getLocalDate(): string {
  const now = new Date()

  const localDate = new Date(
    now.getTime() - now.getTimezoneOffset() * 60000,
  )

  return localDate.toISOString().slice(0, 10)
}

export default function DailyRoutePage() {
  const [selectedDate, setSelectedDate] = useState(getLocalDate)
  const [dailyRoute, setDailyRoute] = useState<DailyRoute | null>(null)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let isActive = true

    setIsLoading(true)

    api<DailyRoute>(
      `/logistics/daily-route?date=${encodeURIComponent(selectedDate)}`,
    )
      .then((result) => {
        if (isActive) {
          setDailyRoute(result)
          setError('')
        }
      })
      .catch(() => {
        if (isActive) {
          setDailyRoute(null)
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

  return (
    <section className="space-y-5 p-6">
      <header>
        <h1 className="text-2xl font-semibold">
          Recorrido del día
        </h1>

        <p className="text-sm text-gray-500">
          Consultá los laboratorios asignados para la fecha seleccionada.
        </p>
      </header>

      <label className="flex max-w-xs flex-col gap-1 text-sm">
        Fecha
        <input
          className="rounded border p-2"
          type="date"
          value={selectedDate}
          onChange={(event) => setSelectedDate(event.target.value)}
        />
      </label>

      {isLoading ? (
        <p role="status">Cargando recorrido...</p>
      ) : error ? (
        <p role="alert">{error}</p>
      ) : !dailyRoute?.id ? (
        <p>No tenés un recorrido asignado para esta fecha.</p>
      ) : (
        <>
          <p>
            Provincia: {dailyRoute.province} ·{' '}
            {dailyRoute.stops.length}{' '}
            {dailyRoute.stops.length === 1 ? 'parada' : 'paradas'}
          </p>

          <p className="text-sm text-gray-600">
            El recorrido tiene un orden establecido.
            Las paradas no se pueden saltear ni reordenar.
          </p>

          {dailyRoute.stops.length === 0 ? (
            <p>Este recorrido todavía no tiene paradas asignadas.</p>
          ) : (
            <ol className="space-y-3">
              {dailyRoute.stops.map((stop) => (
                <li
                  key={stop.laboratory_id}
                  className="rounded-lg border p-4"
                >
                  <strong>
                    {stop.position}. {stop.laboratory}
                  </strong>

                  <p>
                    {stop.address}, {stop.province}
                  </p>

                  <p
                    className={`mt-2 text-sm font-medium ${
                      stop.picked_up_at
                        ? 'text-green-700'
                        : 'text-amber-700'
                    }`}
                  >
                    {stop.picked_up_at
                      ? 'Completado'
                      : 'Sin recolectar'}
                  </p>
                </li>
              ))}
            </ol>
          )}
        </>
      )}
    </section>
  )
}
