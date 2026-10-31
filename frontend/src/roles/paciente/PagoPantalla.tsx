import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Alert } from '../../components/Alert'
import { Button } from '../../components/Button'
import { SelectField } from '../../components/SelectField'
import { TextField } from '../../components/TextField'
import { api, json } from '../../lib/api'
import type { Cupon } from '../../lib/cupones'
import { downloadFile } from '../../lib/download'
import { MIS_ESTUDIOS_KEY, useMisEstudios } from '../../lib/presupuesto'

interface Pago {
  estudio_id: number
  estado: string
  importe_original_usd: number
  importe_usd: number
  cupon: string | null
  cupon_informado: boolean
  metodo: string
  pagado_en: string
}

const METODOS = [
  { valor: 'tarjeta_credito', texto: 'Tarjeta de crédito' },
  { valor: 'tarjeta_debito', texto: 'Tarjeta de débito' },
  { valor: 'transferencia', texto: 'Transferencia' },
]

export default function PagoPantalla() {
  const queryClient = useQueryClient()
  const estudios = useMisEstudios()
  const [estudioId, setEstudioId] = useState<number | null>(null)
  const [metodo, setMetodo] = useState(METODOS[0].valor)
  const [codigo, setCodigo] = useState('')

  // M5-RF3: the coupons the treating doctor gave to the patient are published here.
  const cupones = useQuery({
    queryKey: ['cupones', 'asignados'],
    queryFn: () => api<Cupon[]>('/cupones/asignados'),
  })

  const refrescar = () => queryClient.invalidateQueries({ queryKey: MIS_ESTUDIOS_KEY })

  const pagar = useMutation({
    mutationFn: (estudio: number) =>
      api<Pago>(`/presupuesto_pago/mis-estudios/${estudio}/pago`, {
        method: 'POST',
        ...json({ metodo }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['cupones', 'asignados'] })
      return refrescar()
    },
  })

  const aplicarCodigo = useMutation({
    mutationFn: (datos: { estudio: number; codigo: string }) =>
      api(`/presupuesto_pago/mis-estudios/${datos.estudio}/cupon`, {
        method: 'POST',
        ...json({ codigo: datos.codigo }),
      }),
    onSuccess: () => {
      setCodigo('')
      return refrescar()
    },
  })

  const aplicarPdf = useMutation({
    mutationFn: (datos: { estudio: number; archivo: File }) =>
      api(`/presupuesto_pago/mis-estudios/${datos.estudio}/cupon-pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/pdf' },
        body: datos.archivo,
      }),
    onSuccess: refrescar,
  })

  const quitar = useMutation({
    mutationFn: (estudio: number) =>
      api(`/presupuesto_pago/mis-estudios/${estudio}/cupon`, { method: 'DELETE' }),
    onSuccess: refrescar,
  })

  // A study with a coverage in progress cannot be paid privately.
  const pagables = (estudios.data ?? []).filter(
    (e) => e.estado === 'Creado' && e.importe_usd !== null && e.cobertura === null,
  )
  const estudio = pagables.find((e) => e.id === (estudioId ?? pagables[0]?.id))
  const aplicado = estudio?.cupon_aplicado ?? null
  const importe = aplicado ? aplicado.importe_con_descuento_usd : estudio?.importe_usd
  const errorCupon = aplicarCodigo.error ?? aplicarPdf.error ?? quitar.error

  function aplicar(codigoCupon: string) {
    if (!estudio) return
    aplicarPdf.reset()
    quitar.reset()
    aplicarCodigo.mutate({ estudio: estudio.id, codigo: codigoCupon })
  }

  return (
    <section>
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">Pagar el estudio</h1>
      <p className="mt-1 text-sm text-slate-500">Escenarios 13 y 14 · M4-RF5, RF6</p>

      <div className="mt-4 space-y-3">
        {estudios.isPending && <p className="text-sm text-slate-500">Cargando…</p>}
        {estudios.isError && <Alert kind="error">{estudios.error.message}</Alert>}
        {pagar.isError && <Alert kind="error">{pagar.error.message}</Alert>}
        {pagar.isSuccess && (
          <Alert kind="success">
            Pago registrado: USD {pagar.data.importe_usd}.
            {pagar.data.cupon && ` Se informó el uso del cupón ${pagar.data.cupon}.`} Tu estudio
            está Pagado y ya podés{' '}
            <Link to="../turno" className="font-medium underline">
              sacar tu turno de extracción
            </Link>
            .
          </Alert>
        )}
      </div>

      {estudios.data && !estudio && !pagar.isSuccess && (
        <p className="mt-4 text-sm text-slate-500">No tenés estudios para pagar.</p>
      )}

      {estudio && (
        <div className="mt-6 max-w-md space-y-6">
          {pagables.length > 1 && (
            <SelectField
              label="Estudio"
              value={estudio.id}
              onChange={(e) => setEstudioId(Number(e.target.value))}
            >
              {pagables.map((e) => (
                <option key={e.id} value={e.id}>
                  Estudio {e.id}
                </option>
              ))}
            </SelectField>
          )}

          <div className="text-sm text-slate-700">
            {aplicado ? (
              <>
                <p>
                  Importe del presupuesto: <s>USD {estudio.importe_usd}</s>
                </p>
                <p>
                  Cupón {aplicado.codigo}: {aplicado.descuento}% de descuento
                </p>
              </>
            ) : null}
            <p>
              Importe a abonar: <strong className="text-lg">USD {importe}</strong>
            </p>
            <p>Incluye la extracción y el turno.</p>
          </div>

          <fieldset className="space-y-3 rounded-lg border border-slate-200 p-3">
            <legend className="px-1 text-sm font-medium text-slate-800">Cupón de descuento</legend>
            <form
              className="flex items-end gap-2"
              onSubmit={(event) => {
                event.preventDefault()
                if (codigo.trim()) aplicar(codigo.trim())
              }}
            >
              <div className="flex-1">
                <TextField
                  label="Código del cupón"
                  value={codigo}
                  onChange={(e) => setCodigo(e.target.value)}
                />
              </div>
              <Button
                type="submit"
                variant="secondary"
                loading={aplicarCodigo.isPending}
                disabled={!codigo.trim()}
              >
                Aplicar cupón
              </Button>
            </form>
            <div>
              <label htmlFor="cupon-pdf" className="block text-sm font-medium text-slate-800">
                O adjuntá el PDF del cupón
              </label>
              <input
                id="cupon-pdf"
                type="file"
                accept="application/pdf"
                className="mt-1 block w-full text-sm"
                onChange={(e) => {
                  const archivo = e.target.files?.[0]
                  if (archivo) {
                    aplicarCodigo.reset()
                    quitar.reset()
                    aplicarPdf.mutate({ estudio: estudio.id, archivo })
                  }
                  e.target.value = ''
                }}
              />
            </div>
            {errorCupon && <Alert kind="error">{errorCupon.message}</Alert>}
            {aplicado && (
              <Button
                variant="secondary"
                loading={quitar.isPending}
                onClick={() => {
                  aplicarCodigo.reset()
                  aplicarPdf.reset()
                  quitar.mutate(estudio.id)
                }}
              >
                Quitar el cupón
              </Button>
            )}
          </fieldset>

          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault()
              pagar.mutate(estudio.id)
            }}
          >
            <SelectField
              label="Método de pago"
              value={metodo}
              onChange={(e) => setMetodo(e.target.value)}
            >
              {METODOS.map((m) => (
                <option key={m.valor} value={m.valor}>
                  {m.texto}
                </option>
              ))}
            </SelectField>
            <p className="text-xs text-slate-500">
              El pago es simulado: no se cobra nada, pero queda asentado en el registro financiero.
            </p>
            <Button type="submit" loading={pagar.isPending}>
              Pagar USD {importe}
            </Button>
          </form>
        </div>
      )}

      {cupones.data && cupones.data.length > 0 && (
        <div className="mt-8">
          <h2 className="font-medium text-slate-900">Mis cupones de descuento</h2>
          <ul className="mt-2 grid gap-3 sm:grid-cols-2">
            {cupones.data.map((cupon) => (
              <li key={cupon.codigo} className="flex gap-3 rounded-lg border border-slate-200 p-3">
                {cupon.qr && (
                  <img src={cupon.qr} alt={`QR del cupón ${cupon.codigo}`} className="h-16 w-16" />
                )}
                <div className="text-sm">
                  <p className="font-semibold text-slate-900">{cupon.codigo}</p>
                  <p>
                    {cupon.descuento}% de descuento · {cupon.estado}
                  </p>
                  <div className="mt-1 flex gap-3">
                    {estudio && cupon.estado === 'Vigente' && (
                      <button
                        type="button"
                        className="text-teal-700 underline"
                        onClick={() => aplicar(cupon.codigo)}
                      >
                        Usar este cupón
                      </button>
                    )}
                    <button
                      type="button"
                      className="text-teal-700 underline"
                      onClick={() => {
                        downloadFile(cupon.pdf_url, `cupon-${cupon.codigo}.pdf`).catch(() => {})
                      }}
                    >
                      Descargar PDF
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
