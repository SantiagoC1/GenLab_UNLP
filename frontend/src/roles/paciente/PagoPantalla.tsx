import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Alert } from '../../components/Alert'
import { Button } from '../../components/Button'
import { SelectField } from '../../components/SelectField'
import { api, json } from '../../lib/api'
import { MIS_ESTUDIOS_KEY, useMisEstudios } from '../../lib/presupuesto'

interface Pago {
  estudio_id: number
  estado: string
  importe_usd: number
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

  const pagar = useMutation({
    mutationFn: (estudio: number) =>
      api<Pago>(`/presupuesto_pago/mis-estudios/${estudio}/pago`, {
        method: 'POST',
        ...json({ metodo }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: MIS_ESTUDIOS_KEY }),
  })

  // A study with a coverage in progress cannot be paid privately.
  const pagables = (estudios.data ?? []).filter(
    (e) => e.estado === 'Creado' && e.importe_usd !== null && e.cobertura === null,
  )
  const estudio = pagables.find((e) => e.id === (estudioId ?? pagables[0]?.id))

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
            Pago registrado: USD {pagar.data.importe_usd}. Tu estudio está Pagado y ya podés{' '}
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
        <form
          className="mt-6 max-w-md space-y-4"
          onSubmit={(event) => {
            event.preventDefault()
            pagar.mutate(estudio.id)
          }}
        >
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
          <p className="text-sm text-slate-700">
            Importe a abonar: <strong className="text-lg">USD {estudio.importe_usd}</strong>
            <br />
            Incluye la extracción y el turno.
          </p>
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
            Pagar USD {estudio.importe_usd}
          </Button>
        </form>
      )}
    </section>
  )
}
