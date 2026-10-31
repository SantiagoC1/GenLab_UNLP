
import { useEffect, useState } from 'react'
import { api } from '../../lib/api'

type DeliveryStatus = {
  route_id: number
  date: string
  total_stops: number
  completed_stops: number
  can_deliver: boolean
  delivered_at: string | null
  study_count: number | null
}

type DeliveryResponse = {
  route_id: number
  date: string
  delivered_at: string
  study_count: number
  batch_ids: number[]
}

function getLocalDate(): string {
  const now = new Date()

  return new Date(
    now.getTime() - now.getTimezoneOffset() * 60000,
  )
    .toISOString()
    .slice(0, 10)
}

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('es-AR', {
    dateStyle: 'short',
    timeStyle: 'short',
  })
}

export default function EntregaDeMuestrasPantalla() {
  const [selectedDate] = useState(getLocalDate)
  const [deliveryStatus, setDeliveryStatus] =
    useState<DeliveryStatus | null>(null)

  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  async function loadStatus() {
    const status = await api<DeliveryStatus>(
      `/logistics/delivery/status?date=${encodeURIComponent(selectedDate)}`,
    )

    setDeliveryStatus(status)
  }

  useEffect(() => {
    let isActive = true

    api<DeliveryStatus>(
      `/logistics/delivery/status?date=${encodeURIComponent(selectedDate)}`,
    )
      .then((status) => {
        if (isActive) {
          setDeliveryStatus(status)
        }
      })
      .catch(() => {
        if (isActive) {
          setError('No se pudo consultar el estado de la entrega.')
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

  async function handleDelivery() {
    if (!deliveryStatus?.can_deliver || isSubmitting) {
      return
    }

    setIsSubmitting(true)
    setError('')
    setSuccess('')

    try {
      const result = await api<DeliveryResponse>(
        `/logistics/delivery?date=${encodeURIComponent(selectedDate)}`,
        { method: 'POST' },
      )

      setIsModalOpen(false)

      setSuccess(
        `La entrega se registró correctamente. Se recibieron ${result.study_count} estudios.`,
      )

      try {
        await loadStatus()
      } catch {
        setError(
          'La entrega se registró, pero no se pudo actualizar su estado. Recargá la página.',
        )
      }
    } catch {
      setIsModalOpen(false)
      setError(
        'No se pudo registrar la entrega. Verificá el estado del recorrido antes de volver a intentarlo.',
      )

      try {
        await loadStatus()
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
          Entrega de muestras
        </h1>

        <p className="text-sm text-gray-500">
          Registrá la llegada y entrega de las muestras
          en el laboratorio central.
        </p>
      </header>

      {isLoading ? (
        <p role="status">Cargando información de la entrega...</p>
      ) : deliveryStatus ? (
        <div className="max-w-2xl space-y-4">
          <div className="rounded-lg border bg-white p-5">
            <h2 className="text-lg font-semibold">
              Estado del recorrido
            </h2>

            <p className="mt-3 text-sm text-gray-600">
              Laboratorios completados
            </p>

            <p className="mt-1 text-xl font-semibold">
              {deliveryStatus.completed_stops} de{' '}
              {deliveryStatus.total_stops}
            </p>

            <p
              className={`mt-3 text-sm font-medium ${
                deliveryStatus.delivered_at
                  ? 'text-green-700'
                  : deliveryStatus.can_deliver
                    ? 'text-blue-700'
                    : 'text-amber-700'
              }`}
            >
              {deliveryStatus.delivered_at
                ? 'Entrega completada'
                : deliveryStatus.can_deliver
                  ? 'Listo para entregar'
                  : 'Retiro de muestras pendiente'}
            </p>

            {deliveryStatus.delivered_at && (
              <div className="mt-4 rounded-lg bg-green-50 p-4">
                <p className="font-medium text-green-800">
                  Las muestras fueron entregadas correctamente.
                </p>

                <p className="mt-2 text-sm text-green-700">
                  Fecha y hora:{' '}
                  {formatDateTime(deliveryStatus.delivered_at)}
                </p>

                <p className="mt-1 text-sm text-green-700">
                  Estudios recibidos: {deliveryStatus.study_count}
                </p>
              </div>
            )}

            {!deliveryStatus.delivered_at && (
              <button
                type="button"
                disabled={!deliveryStatus.can_deliver}
                onClick={() => setIsModalOpen(true)}
                className="mt-5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300"
              >
                Confirmar entrega
              </button>
            )}
          </div>

          {!deliveryStatus.can_deliver &&
            !deliveryStatus.delivered_at && (
              <p className="text-sm text-gray-600">
                Para registrar la entrega, primero debés
                completar el retiro de muestras en todos
                los laboratorios del recorrido.
              </p>
            )}
        </div>
      ) : null}

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

      {isModalOpen && (
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
            aria-labelledby="delivery-dialog-title"
            aria-describedby="delivery-dialog-description"
            className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl"
            onKeyDown={(event) => {
              if (event.key === 'Escape' && !isSubmitting) {
                setIsModalOpen(false)
              }
            }}
          >
            <h2
              id="delivery-dialog-title"
              className="text-xl font-semibold"
            >
              Confirmar entrega de muestras
            </h2>

            <p
              id="delivery-dialog-description"
              className="mt-3 text-sm text-gray-600"
            >
              ¿Confirmás que llegaste al laboratorio central
              y entregaste todas las muestras recolectadas
              durante el recorrido?
            </p>

            <p className="mt-4 text-sm text-gray-500">
              Una vez registrada, la entrega no podrá
              confirmarse nuevamente.
            </p>

            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                disabled={isSubmitting}
                onClick={() => setIsModalOpen(false)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Cancelar
              </button>

              <button
                type="button"
                disabled={isSubmitting}
                onClick={handleDelivery}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {isSubmitting
                  ? 'Registrando...'
                  : 'Confirmar entrega'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
