import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Alert } from '../../components/Alert'
import { Button } from '../../components/Button'
import { EmptyState } from '../../components/EmptyState'
import { PageContainer } from '../../components/PageContainer'
import { PageHeader } from '../../components/PageHeader'
import { SelectField } from '../../components/SelectField'
import { LoadingBlock } from '../../components/Skeleton'
import { errorMessage } from '../../lib/api'
import {
  formatearMonto,
  useCondicionesDePago,
  useIrAPagarConMercadoPago,
} from '../../lib/mercadopago'
import { useMisEstudios } from '../../lib/presupuesto'

/**
 * Antes de ir a pagar con Mercado Pago (M4-RF5): el importe, las cuotas y el medio de pago. Las
 * cuotas las elige y las maneja Mercado Pago. Al hacer clic, el paciente va a su checkout y vuelve
 * a la pantalla del resultado del pago.
 */
export default function PagoMercadoPagoPantalla() {
  const estudios = useMisEstudios()
  const [estudioId, setEstudioId] = useState<number | null>(null)

  // A study with a coverage in progress cannot be paid privately.
  const pagables = (estudios.data ?? []).filter(
    (e) => e.estado === 'Creado' && e.importe_usd !== null && e.cobertura === null,
  )
  const estudio = pagables.find((e) => e.id === (estudioId ?? pagables[0]?.id))
  const condiciones = useCondicionesDePago(estudio?.id)
  const pagar = useIrAPagarConMercadoPago()

  return (
    <PageContainer>
      <PageHeader title="Pagar con Mercado Pago" reference="Escenarios 13 y 14 · M4-RF5">
        <p className="mt-1 text-sm text-muted">
          Pagás en el sitio de Mercado Pago y volvés acá. Si pagás con tarjeta de crédito, elegís
          las cuotas ahí.
        </p>
      </PageHeader>

      {estudios.isPending && <LoadingBlock label="Cargando tus estudios…" />}
      {estudios.isError && (
        <div className="space-y-3">
          <Alert kind="error">{errorMessage(estudios.error)}</Alert>
          <Button variant="secondary" onClick={() => void estudios.refetch()}>
            Reintentar
          </Button>
        </div>
      )}
      {estudios.data && !estudio && (
        <EmptyState>No tenés estudios para pagar con Mercado Pago.</EmptyState>
      )}

      {estudio && (
        <div className="space-y-6">
          {pagables.length > 1 && (
            <SelectField
              label="Estudio"
              value={estudio.id}
              onChange={(e) => {
                pagar.reset()
                setEstudioId(Number(e.target.value))
              }}
            >
              {pagables.map((e) => (
                <option key={e.id} value={e.id}>
                  Estudio {e.id}
                </option>
              ))}
            </SelectField>
          )}

          <section
            aria-labelledby="pago-mp-titulo"
            className="space-y-4 rounded-card border border-hair bg-panel p-4 text-sm text-ink sm:p-6"
          >
            <h2 id="pago-mp-titulo" className="font-medium">
              Estudio {estudio.id}
            </h2>

            {condiciones.isPending && <LoadingBlock label="Calculando el importe…" />}
            {condiciones.isError && (
              <div className="space-y-3">
                <Alert kind="error">{errorMessage(condiciones.error)}</Alert>
                <Button variant="secondary" onClick={() => void condiciones.refetch()}>
                  Reintentar
                </Button>
              </div>
            )}

            {condiciones.data && (
              <>
                <div>
                  {condiciones.data.cupon && (
                    <>
                      <p>
                        Importe del presupuesto: <s>USD {condiciones.data.importe_original_usd}</s>
                      </p>
                      <p>Cupón {condiciones.data.cupon} aplicado.</p>
                    </>
                  )}
                  <p>
                    Importe a abonar:{' '}
                    <strong className="text-lg">USD {condiciones.data.importe_usd}</strong>
                  </p>
                  <p className="text-muted">Incluye la extracción y el turno.</p>
                  <p className="mt-2">
                    Mercado Pago te cobra{' '}
                    <strong>
                      {formatearMonto(condiciones.data.importe, condiciones.data.moneda)}
                    </strong>
                    .
                  </p>
                </div>

                <dl className="space-y-2 rounded-control bg-brand-soft p-3">
                  <div>
                    <dt className="font-medium">Cuotas</dt>
                    <dd>
                      Podés pagar en hasta {condiciones.data.cuotas_maximas} cuotas con tarjeta de
                      crédito. Elegís la cantidad al pagar en Mercado Pago.
                    </dd>
                  </div>
                  <div>
                    <dt className="font-medium">Medio de pago</dt>
                    <dd>Mercado Pago: tarjeta de crédito o de débito, o dinero en tu cuenta.</dd>
                  </div>
                </dl>

                <p className="text-muted">
                  ¿Tenés un cupón de descuento? Aplicalo antes en{' '}
                  <Link to="/paciente/pago" className="font-medium text-brand underline">
                    Pagar el estudio
                  </Link>
                  .
                </p>
              </>
            )}

            {pagar.isError && <Alert kind="error">{errorMessage(pagar.error)}</Alert>}

            <Button
              onClick={() => pagar.mutate(estudio.id)}
              loading={pagar.isPending || pagar.isSuccess}
              disabled={!condiciones.data}
            >
              Pagar con Mercado Pago
            </Button>
            {pagar.isSuccess && (
              <p role="status" className="text-sm text-muted">
                Te llevamos a Mercado Pago…
              </p>
            )}
          </section>
        </div>
      )}
    </PageContainer>
  )
}
