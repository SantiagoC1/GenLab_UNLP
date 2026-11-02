import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Alert } from '../../components/Alert'
import { Button } from '../../components/Button'
import { SelectField } from '../../components/SelectField'
import { api, json } from '../../lib/api'
import { MIS_ESTUDIOS_KEY, useMisEstudios, type EstudioDelPaciente } from '../../lib/presupuesto'

interface ObraSocial {
  nombre: string
  cobertura: number
}

const NO_FIGURA = '__no_figura__'

export default function CoberturaPantalla() {
  const queryClient = useQueryClient()
  const estudios = useMisEstudios()
  const [estudioId, setEstudioId] = useState<number | null>(null)
  const [obraSocial, setObraSocial] = useState('')

  const obrasSociales = useQuery({
    queryKey: ['presupuesto', 'obras-sociales'],
    queryFn: () => api<ObraSocial[]>('/presupuesto_pago/obras-sociales'),
  })

  const elegir = useMutation({
    mutationFn: (datos: { estudio: number; obra_social: string }) =>
      api<EstudioDelPaciente>(`/presupuesto_pago/mis-estudios/${datos.estudio}/cobertura`, {
        method: 'POST',
        ...json({ obra_social: datos.obra_social }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: MIS_ESTUDIOS_KEY }),
  })

  const elegibles = (estudios.data ?? []).filter(
    (e) => e.estado === 'Creado' && e.importe_usd !== null && e.cobertura === null,
  )
  const enEspera = (estudios.data ?? []).filter((e) => e.cobertura?.estado === 'Pendiente')
  const estudio = elegibles.find((e) => e.id === (estudioId ?? elegibles[0]?.id))
  const porcentaje = obrasSociales.data?.find((o) => o.nombre === obraSocial)?.cobertura

  return (
    <section>
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">
        Elegir la cobertura por obra social
      </h1>
      <p className="mt-1 text-sm text-slate-500">Escenario 12 · M4-RF3, RF4</p>

      <div className="mt-4 space-y-3">
        {estudios.isPending && <p className="text-sm text-slate-500">Cargando…</p>}
        {estudios.isError && <Alert kind="error">{estudios.error.message}</Alert>}
        {obrasSociales.isError && (
          <Alert kind="error">
            No se pudo cargar la lista de obras sociales: {obrasSociales.error.message}
          </Alert>
        )}
        {elegir.isError && <Alert kind="error">{elegir.error.message}</Alert>}
        {elegir.isSuccess && (
          <Alert kind="success">
            Tu estudio quedó a la espera de la autorización de la obra social. Te vamos a avisar
            cuando la tengamos.
          </Alert>
        )}
      </div>

      {enEspera.map((e) => (
        <p key={e.id} className="mt-4 rounded-lg border border-slate-200 p-3 text-sm">
          Estudio {e.id}: a la espera de la autorización de {e.cobertura?.obra_social} (cubre el{' '}
          {e.cobertura?.porcentaje}%).
        </p>
      ))}

      {estudios.data && elegibles.length === 0 && enEspera.length === 0 && (
        <p className="mt-4 text-sm text-slate-500">
          No tenés estudios con presupuesto para elegir la cobertura.
        </p>
      )}

      {estudio && (
        <form
          className="mt-6 max-w-md space-y-4"
          onSubmit={(event) => {
            event.preventDefault()
            if (obraSocial && obraSocial !== NO_FIGURA) {
              elegir.mutate({ estudio: estudio.id, obra_social: obraSocial })
            }
          }}
        >
          {elegibles.length > 1 && (
            <SelectField
              label="Estudio"
              value={estudio.id}
              onChange={(e) => setEstudioId(Number(e.target.value))}
            >
              {elegibles.map((e) => (
                <option key={e.id} value={e.id}>
                  Estudio {e.id}
                </option>
              ))}
            </SelectField>
          )}
          <p className="text-sm">
            Presupuesto: <strong>USD {estudio.importe_usd}</strong> ({estudio.cantidad_genes} genes)
          </p>

          <SelectField
            label="Obra social"
            value={obraSocial}
            onChange={(e) => setObraSocial(e.target.value)}
          >
            <option value="">Elegí tu obra social</option>
            {obrasSociales.data?.map((o) => (
              <option key={o.nombre} value={o.nombre}>
                {o.nombre} · cubre el {o.cobertura}%
              </option>
            ))}
            <option value={NO_FIGURA}>Mi obra social no figura en la lista</option>
          </SelectField>

          {porcentaje !== undefined && (
            <p className="text-sm text-slate-700">
              Esta obra social cubre el <strong>{porcentaje}%</strong> del estudio.
            </p>
          )}
          {obraSocial === NO_FIGURA && (
            <Alert kind="info">
              Si tu obra social no figura en la lista, solo podés pagar de forma particular.{' '}
              <Link to="../pago" className="font-medium underline">
                Ir al pago particular
              </Link>
            </Alert>
          )}

          <Button
            type="submit"
            loading={elegir.isPending}
            disabled={!obraSocial || obraSocial === NO_FIGURA}
          >
            Dejar a la espera de la autorización
          </Button>
        </form>
      )}
    </section>
  )
}
