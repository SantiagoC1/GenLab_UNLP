import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Alert } from '../../components/Alert'
import { Button } from '../../components/Button'
import { TextField } from '../../components/TextField'
import { api, json } from '../../lib/api'
import { CUPONES_KEY, type Cupon } from '../../lib/cupones'
import { downloadFile } from '../../lib/download'

export default function GenerarCuponesPantalla() {
  const queryClient = useQueryClient()
  const [descuento, setDescuento] = useState('')
  const [cantidad, setCantidad] = useState('')
  const [errorPdf, setErrorPdf] = useState<string | null>(null)

  const cupones = useQuery({
    queryKey: CUPONES_KEY,
    queryFn: () => api<Cupon[]>('/cupones'),
  })

  const generar = useMutation({
    mutationFn: () =>
      api<Cupon[]>('/cupones/generar', {
        method: 'POST',
        ...json({ descuento: Number(descuento), cantidad: Number(cantidad) }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CUPONES_KEY }),
  })

  const descuentoValido = Number.isInteger(Number(descuento)) && Number(descuento) >= 1
  const cantidadValida = Number.isInteger(Number(cantidad)) && Number(cantidad) >= 1
  const puedeGenerar = descuentoValido && cantidadValida && Number(descuento) <= 100

  return (
    <section>
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">
        Generar cupones de descuento
      </h1>
      <p className="mt-1 text-sm text-slate-500">Escenario 15 · M5-RF1, RF5</p>

      <form
        className="mt-6 grid max-w-xl gap-4 sm:grid-cols-2"
        onSubmit={(event) => {
          event.preventDefault()
          if (puedeGenerar) generar.mutate()
        }}
      >
        <TextField
          label="Descuento (%)"
          type="number"
          min={1}
          max={100}
          value={descuento}
          onChange={(e) => setDescuento(e.target.value)}
        />
        <TextField
          label="Cantidad de cupones"
          type="number"
          min={1}
          max={100}
          value={cantidad}
          onChange={(e) => setCantidad(e.target.value)}
        />
        <div className="sm:col-span-2">
          <Button type="submit" loading={generar.isPending} disabled={!puedeGenerar}>
            Generar cupones
          </Button>
        </div>
      </form>

      <div className="mt-4 space-y-3">
        {generar.isError && <Alert kind="error">{generar.error.message}</Alert>}
        {generar.isSuccess && (
          <Alert kind="success">
            Se generaron {generar.data.length} cupones Vigentes con el {generar.data[0]?.descuento}%
            de descuento.
          </Alert>
        )}
        {errorPdf && <Alert kind="error">{errorPdf}</Alert>}
      </div>

      <h2 className="mt-8 font-medium text-slate-900">Cupones</h2>
      {cupones.isPending && <p className="mt-2 text-sm text-slate-500">Cargando…</p>}
      {cupones.isError && <Alert kind="error">{cupones.error.message}</Alert>}
      {cupones.data?.length === 0 && (
        <p className="mt-2 text-sm text-slate-500">Todavía no hay cupones generados.</p>
      )}
      <ul className="mt-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {cupones.data?.map((cupon) => (
          <li key={cupon.codigo} className="flex gap-3 rounded-lg border border-slate-200 p-3">
            {cupon.qr && (
              <img src={cupon.qr} alt={`QR del cupón ${cupon.codigo}`} className="h-20 w-20" />
            )}
            <div className="min-w-0 text-sm">
              <p className="font-semibold text-slate-900">{cupon.codigo}</p>
              <p>
                {cupon.descuento}% · {cupon.estado}
              </p>
              <button
                type="button"
                className="mt-1 text-teal-700 underline"
                onClick={() => {
                  setErrorPdf(null)
                  downloadFile(cupon.pdf_url, `cupon-${cupon.codigo}.pdf`).catch((error: Error) =>
                    setErrorPdf(error.message),
                  )
                }}
              >
                Descargar PDF
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
