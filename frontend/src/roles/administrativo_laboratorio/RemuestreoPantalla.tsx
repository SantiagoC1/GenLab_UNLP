import { useId, useState, type FormEvent } from 'react'
import { Alert } from '../../components/Alert'
import { Button } from '../../components/Button'
import { EmptyState } from '../../components/EmptyState'
import { PageContainer } from '../../components/PageContainer'
import { PageHeader } from '../../components/PageHeader'
import { SelectField } from '../../components/SelectField'
import { LoadingBlock } from '../../components/Skeleton'
import { FIELD_CLASS } from '../../components/TextField'
import { errorMessage } from '../../lib/api'
import {
  DETALLE_MAXIMO,
  DETALLE_MINIMO,
  MOTIVOS_REMUESTREO,
  describirAvisos,
  useEstudiosRemuestreables,
  usePedirRemuestreo,
  type EstudioRemuestreable,
  type MotivoRemuestreo,
} from '../../lib/remuestreo'
import { STATE_LABELS } from '../../lib/studies'

interface Errores {
  motivo?: string
  detalle?: string
}

function validar(motivo: MotivoRemuestreo | '', detalle: string): Errores {
  const errores: Errores = {}
  if (!motivo) errores.motivo = 'Elegí el motivo del remuestreo.'
  if (detalle.trim().length < DETALLE_MINIMO) {
    errores.detalle = `Escribí el detalle del remuestreo (al menos ${DETALLE_MINIMO} caracteres).`
  }
  return errores
}

/**
 * Remuestreo pedido por el administrativo (M6-RF10, escenario 25): la muestra llegó a Corea con
 * mala calidad, o el ADN no alcanzó. El estudio vuelve a Turno sacado, sin costo, y se avisa al
 * médico tratante y al paciente.
 */
export default function RemuestreoPantalla() {
  const estudios = useEstudiosRemuestreables()
  const pedido = usePedirRemuestreo()
  const [seleccionado, setSeleccionado] = useState<number | null>(null)
  const [motivo, setMotivo] = useState<MotivoRemuestreo | ''>('')
  const [detalle, setDetalle] = useState('')
  const [errores, setErrores] = useState<Errores>({})
  const detalleId = useId()

  const estudio = estudios.data?.find((e) => e.estudio_id === seleccionado)

  function elegir(elegido: EstudioRemuestreable) {
    pedido.reset()
    setSeleccionado(elegido.estudio_id)
    setMotivo('')
    setDetalle('')
    setErrores({})
  }

  function enviar(evento: FormEvent) {
    evento.preventDefault()
    if (!estudio) return
    const encontrados = validar(motivo, detalle)
    setErrores(encontrados)
    if (Object.keys(encontrados).length > 0 || motivo === '') return
    pedido.mutate(
      { estudioId: estudio.estudio_id, motivo, detalle },
      { onSuccess: () => setSeleccionado(null) },
    )
  }

  return (
    <PageContainer wide>
      <PageHeader title="Pedir el remuestreo de un estudio" reference="Escenario 25 · M6-RF10">
        <p className="mt-1 text-sm text-muted">
          Si la muestra de sangre llegó a Corea con mala calidad, o el ADN no alcanzó, pedí una
          nueva. Es el mismo estudio y no tiene costo para el paciente.
        </p>
      </PageHeader>

      <div className="space-y-3">
        {pedido.isSuccess && (
          <Alert kind="success">
            Remuestreo pedido para el estudio {pedido.data.estudio_id}. El estudio volvió a Turno
            sacado, sin costo. {describirAvisos(pedido.data)}
          </Alert>
        )}
        {pedido.isError && <Alert kind="error">{errorMessage(pedido.error)}</Alert>}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <section aria-labelledby="remuestreables-titulo">
          <h2 id="remuestreables-titulo" className="font-medium text-ink">
            Estudios en viaje a Corea o en bioinformática
          </h2>

          {estudios.isPending && (
            <div className="mt-3">
              <LoadingBlock label="Cargando los estudios…" />
            </div>
          )}
          {estudios.isError && (
            <div className="mt-3 space-y-3">
              <Alert kind="error">
                No se pudieron cargar los estudios: {errorMessage(estudios.error)}
              </Alert>
              <Button variant="secondary" onClick={() => void estudios.refetch()}>
                Reintentar
              </Button>
            </div>
          )}
          {estudios.data?.length === 0 && (
            <div className="mt-3">
              <EmptyState>
                No hay estudios en viaje a Corea ni en el área de bioinformática.
              </EmptyState>
            </div>
          )}
          {estudios.data && estudios.data.length > 0 && (
            <ul className="mt-3 divide-y divide-hair overflow-hidden rounded-card border border-hair bg-panel">
              {estudios.data.map((e) => (
                <li key={e.estudio_id}>
                  <button
                    type="button"
                    onClick={() => elegir(e)}
                    aria-pressed={seleccionado === e.estudio_id}
                    className="flex min-h-11 w-full flex-col gap-1 p-3 text-left text-sm text-ink transition-colors duration-150 hover:bg-panel-2 aria-pressed:bg-brand-soft"
                  >
                    <span className="font-medium">
                      Estudio {e.estudio_id} · {e.paciente}
                    </span>
                    <span className="text-muted">
                      DNI {e.dni} · {STATE_LABELS[e.estado] ?? e.estado}
                    </span>
                    {e.remuestreo_pendiente && (
                      <span className="w-fit rounded-control border border-warn bg-panel px-2 py-0.5 text-xs font-medium text-warn">
                        Remuestreo pendiente
                      </span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        {estudio && (
          <section
            aria-labelledby="remuestreo-form-titulo"
            className="h-fit rounded-card border border-hair bg-panel p-4 sm:p-6"
          >
            <h2 id="remuestreo-form-titulo" className="font-medium text-ink">
              Estudio {estudio.estudio_id} · {estudio.paciente}
            </h2>
            <p className="mt-1 text-sm text-muted">
              DNI {estudio.dni} · {STATE_LABELS[estudio.estado] ?? estudio.estado}
            </p>

            {estudio.remuestreo_pendiente ? (
              <div className="mt-4">
                <Alert kind="warning">
                  Este estudio ya tiene un remuestreo pendiente: el paciente todavía no sacó el
                  nuevo turno. No se puede pedir otro.
                </Alert>
              </div>
            ) : (
              <form onSubmit={enviar} noValidate className="mt-4 space-y-4">
                <SelectField
                  label="Motivo del remuestreo"
                  value={motivo}
                  onChange={(e) => setMotivo(e.target.value as MotivoRemuestreo | '')}
                  error={errores.motivo}
                  disabled={pedido.isPending}
                >
                  <option value="">Elegí un motivo</option>
                  {MOTIVOS_REMUESTREO.map((m) => (
                    <option key={m.value} value={m.value}>
                      {m.label}
                    </option>
                  ))}
                </SelectField>

                <div>
                  <label htmlFor={detalleId} className="block text-sm font-medium text-ink">
                    Detalle
                  </label>
                  <textarea
                    id={detalleId}
                    rows={4}
                    maxLength={DETALLE_MAXIMO}
                    value={detalle}
                    onChange={(e) => setDetalle(e.target.value)}
                    disabled={pedido.isPending}
                    aria-invalid={errores.detalle ? true : undefined}
                    aria-describedby={`${detalleId}-ayuda`}
                    className={FIELD_CLASS}
                  />
                  <p
                    id={`${detalleId}-ayuda`}
                    className={`mt-1 text-sm ${errores.detalle ? 'text-error' : 'text-muted'}`}
                  >
                    {errores.detalle ??
                      `Qué pasó con la muestra. Es lo que se le informa al médico tratante y al paciente. ${detalle.length}/${DETALLE_MAXIMO}`}
                  </p>
                </div>

                <Button type="submit" loading={pedido.isPending}>
                  Pedir remuestreo
                </Button>
              </form>
            )}
          </section>
        )}
      </div>
    </PageContainer>
  )
}
