import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Alert } from '../../components/Alert'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { EmptyState } from '../../components/EmptyState'
import { PageContainer } from '../../components/PageContainer'
import { PageHeader } from '../../components/PageHeader'
import { SelectField } from '../../components/SelectField'
import { LoadingBlock } from '../../components/Skeleton'
import { Stepper } from '../../components/Stepper'
import { api, json } from '../../lib/api'
import { MIS_ESTUDIOS_KEY, useMisEstudios, type EstudioDelPaciente } from '../../lib/presupuesto'

interface ObraSocial {
  nombre: string
  cobertura: number
}

const NO_FIGURA = '__no_figura__'
const STEPS = ['Cobertura', 'Pago', 'Turno de extracción', 'Resultado']

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

  const canSubmit = Boolean(obraSocial) && obraSocial !== NO_FIGURA

  return (
    <PageContainer>
      <PageHeader
        title="Elegir la cobertura por obra social"
        reference="Escenario 12 · M4-RF3, RF4"
      />
      <Stepper steps={STEPS} current={0} />

      <div className="space-y-3">
        {estudios.isPending && <LoadingBlock />}
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
        <Card key={e.id} className="mt-4">
          <p className="text-sm">
            Estudio {e.id}: a la espera de la autorización de {e.cobertura?.obra_social} (cubre el{' '}
            {e.cobertura?.porcentaje}%).
          </p>
        </Card>
      ))}

      {estudios.data && elegibles.length === 0 && enEspera.length === 0 && (
        <div className="mt-4">
          <EmptyState>No tenés estudios con presupuesto para elegir la cobertura.</EmptyState>
        </div>
      )}

      {estudio && (
        <form
          className="mt-4 space-y-4"
          onSubmit={(event) => {
            event.preventDefault()
            if (canSubmit) {
              elegir.mutate({ estudio: estudio.id, obra_social: obraSocial })
            }
          }}
        >
          <Card className="space-y-5">
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

            <div className="rounded-control bg-brand-tint p-4">
              <p className="text-sm text-muted">Presupuesto</p>
              <p className="text-3xl font-semibold text-brand-strong">
                <strong>USD {estudio.importe_usd}</strong>
              </p>
              <p className="text-sm text-muted">{estudio.cantidad_genes} genes</p>
            </div>

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
              <p className="text-sm text-ink-soft">
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
          </Card>

          <div className="space-y-2">
            <Button
              type="submit"
              loading={elegir.isPending}
              disabled={!canSubmit}
              aria-describedby="submit-help"
              className="w-full sm:w-auto"
            >
              Dejar a la espera de la autorización
            </Button>
            {!canSubmit && (
              <p id="submit-help" className="text-sm text-muted">
                {obraSocial === NO_FIGURA
                  ? 'Para continuar, elegí el pago particular.'
                  : 'Elegí tu obra social para continuar.'}
              </p>
            )}
          </div>
        </form>
      )}
    </PageContainer>
  )
}
