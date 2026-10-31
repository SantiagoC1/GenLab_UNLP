import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../../lib/api'

interface EstudioPendiente {
  id: number
  paciente: string
  cantidad_genes: number
}

interface DetalleEstudio {
  id: number
  paciente: string
  genes: string[]
  cantidad_genes: number
  importe_usd: number
  presupuesto_emitido: boolean
}

const RAIZ = '/presupuesto_pago'

export default function PresupuestosPantalla() {
  const queryClient = useQueryClient()
  const [seleccionado, setSeleccionado] = useState<number | null>(null)

  const bandeja = useQuery({
    queryKey: ['presupuestos', 'pendientes'],
    queryFn: () => api<EstudioPendiente[]>(`${RAIZ}/estudios-pendientes`),
  })

  const detalle = useQuery({
    queryKey: ['presupuestos', 'detalle', seleccionado],
    queryFn: () => api<DetalleEstudio>(`${RAIZ}/estudios/${seleccionado}`),
    enabled: seleccionado !== null,
  })

  const emitir = useMutation({
    mutationFn: (id: number) => api(`${RAIZ}/estudios/${id}/presupuesto`, { method: 'POST' }),
    onSuccess: () => {
      setSeleccionado(null)
      return queryClient.invalidateQueries({ queryKey: ['presupuestos'] })
    },
  })

  return (
    <section>
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">Emitir el presupuesto</h1>
      <p className="mt-1 text-sm text-slate-500">Escenario 11 · M4-RF1</p>

      {emitir.isSuccess && (
        <p role="status" className="mt-4 rounded-lg bg-green-50 p-3 text-sm text-green-800">
          Presupuesto emitido. El paciente recibió un aviso.
        </p>
      )}
      {emitir.isError && (
        <p role="alert" className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-800">
          {emitir.error.message}
        </p>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div>
          <h2 className="font-medium text-slate-900">Estudios sin presupuesto</h2>
          {bandeja.isPending && <p className="mt-2 text-sm text-slate-500">Cargando…</p>}
          {bandeja.isError && (
            <p role="alert" className="mt-2 text-sm text-red-700">
              No se pudo cargar la bandeja: {bandeja.error.message}
            </p>
          )}
          {bandeja.data?.length === 0 && (
            <p className="mt-2 text-sm text-slate-500">No hay estudios sin presupuesto.</p>
          )}
          <ul className="mt-2 divide-y divide-slate-200 rounded-lg border border-slate-200">
            {bandeja.data?.map((estudio) => (
              <li key={estudio.id}>
                <button
                  type="button"
                  onClick={() => {
                    emitir.reset()
                    setSeleccionado(estudio.id)
                  }}
                  aria-pressed={seleccionado === estudio.id}
                  className="flex w-full justify-between gap-4 p-3 text-left text-sm hover:bg-slate-50 aria-pressed:bg-slate-100"
                >
                  <span>
                    Estudio {estudio.id} · {estudio.paciente}
                  </span>
                  <span className="text-slate-500">{estudio.cantidad_genes} genes</span>
                </button>
              </li>
            ))}
          </ul>
        </div>

        {seleccionado !== null && (
          <div>
            <h2 className="font-medium text-slate-900">Detalle del estudio</h2>
            {detalle.isPending && <p className="mt-2 text-sm text-slate-500">Cargando…</p>}
            {detalle.isError && (
              <p role="alert" className="mt-2 text-sm text-red-700">
                No se pudo cargar el estudio: {detalle.error.message}
              </p>
            )}
            {detalle.data && (
              <div className="mt-2 rounded-lg border border-slate-200 p-4 text-sm">
                <p>
                  Paciente: <strong>{detalle.data.paciente}</strong>
                </p>
                <p className="mt-3 text-slate-500">Genes ({detalle.data.cantidad_genes})</p>
                <ul className="mt-1 flex flex-wrap gap-2">
                  {detalle.data.genes.map((gen) => (
                    <li key={gen} className="rounded bg-slate-100 px-2 py-0.5">
                      {gen}
                    </li>
                  ))}
                </ul>
                <p className="mt-4 text-lg font-semibold text-slate-900">
                  Importe: USD {detalle.data.importe_usd}
                </p>
                <p className="text-slate-500">Incluye la extracción y el turno.</p>
                <button
                  type="button"
                  onClick={() => emitir.mutate(detalle.data.id)}
                  disabled={emitir.isPending}
                  className="mt-4 rounded-lg bg-slate-900 px-4 py-2 text-white disabled:opacity-50"
                >
                  Emitir presupuesto
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  )
}
