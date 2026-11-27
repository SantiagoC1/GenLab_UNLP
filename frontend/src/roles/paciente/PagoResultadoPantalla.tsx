import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Alert } from '../../components/Alert'
import { Button } from '../../components/Button'
import { PageContainer } from '../../components/PageContainer'
import { PageHeader } from '../../components/PageHeader'
import { LoadingBlock } from '../../components/Skeleton'
import { errorMessage } from '../../lib/api'
import {
  describirMetodo,
  describirRechazo,
  formatearMonto,
  useConfirmarPago,
  type ConfirmacionDePago,
} from '../../lib/mercadopago'

const PAGAR_DE_NUEVO = '/paciente/pagar-con-mercadopago'

/** Mercado Pago manda el id del pago en `payment_id` (o en `collection_id`); a veces dice "null". */
function idDelPago(params: URLSearchParams): string | null {
  const id = params.get('payment_id') ?? params.get('collection_id')
  return id && id !== 'null' ? id : null
}

/**
 * A donde vuelve el paciente desde Mercado Pago: se confirma el pago por su id (no hay avisos de
 * Mercado Pago hacia un servidor de desarrollo) y se muestra el resultado.
 */
export default function PagoResultadoPantalla() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const paymentId = idDelPago(params)
  const confirmacion = useConfirmarPago(paymentId)

  return (
    <PageContainer>
      <PageHeader title="Resultado del pago" reference="Escenarios 13 y 14 · M4-RF5" />

      {paymentId === null && (
        <div className="space-y-3">
          <Alert kind="warning">
            No se realizó el pago: no recibimos ningún pago de Mercado Pago. No se te cobró nada y
            tu estudio sigue sin pagar.
          </Alert>
          <Button onClick={() => navigate(PAGAR_DE_NUEVO)}>Volver a intentar el pago</Button>
        </div>
      )}

      {paymentId !== null && confirmacion.isPending && (
        <LoadingBlock label="Confirmando tu pago con Mercado Pago…" />
      )}

      {confirmacion.isError && (
        <div className="space-y-3">
          <Alert kind="error">{errorMessage(confirmacion.error)}</Alert>
          <div className="flex flex-wrap gap-3">
            <Button variant="secondary" onClick={() => void confirmacion.refetch()}>
              Reintentar
            </Button>
            <Button variant="secondary" onClick={() => navigate('/paciente/estudios')}>
              Ir a mis estudios
            </Button>
          </div>
        </div>
      )}

      {confirmacion.data?.resultado === 'aprobado' && <Aprobado pago={confirmacion.data} />}

      {confirmacion.data?.resultado === 'pendiente' && (
        <div className="space-y-3">
          <Alert kind="info">
            Tu pago está pendiente de acreditación. Cuando Mercado Pago lo apruebe lo vamos a
            registrar y tu estudio va a pasar a Pagado. Todavía no se registró ningún pago.
          </Alert>
          <div className="flex flex-wrap gap-3">
            <Button variant="secondary" onClick={() => void confirmacion.refetch()}>
              Volver a consultar
            </Button>
            <Button variant="secondary" onClick={() => navigate('/paciente/estudios')}>
              Ir a mis estudios
            </Button>
          </div>
        </div>
      )}

      {confirmacion.data?.resultado === 'rechazado' && (
        <div className="space-y-3">
          <Alert kind="error">
            El pago no se realizó. {describirRechazo(confirmacion.data.detalle_mp)} No se registró
            ningún pago y tu estudio sigue sin pagar.
          </Alert>
          <Button onClick={() => navigate(PAGAR_DE_NUEVO)}>Reintentar el pago</Button>
        </div>
      )}
    </PageContainer>
  )
}

function Aprobado({ pago }: { pago: ConfirmacionDePago }) {
  const cuotas = pago.cuotas ?? 1
  return (
    <div className="space-y-4">
      <Alert kind="success">
        Pago aprobado. Tu estudio {pago.estudio_id} está {pago.estado_estudio} y ya podés{' '}
        <Link to="/paciente/turno" className="font-medium underline">
          sacar tu turno de extracción
        </Link>
        .
      </Alert>

      <section
        aria-labelledby="plan-de-pago"
        className="space-y-3 rounded-card border border-hair bg-panel p-4 text-sm text-ink sm:p-6"
      >
        <h2 id="plan-de-pago" className="font-medium">
          Tu plan de pago
        </h2>
        <dl className="space-y-2">
          <div>
            <dt className="text-muted">Importe del estudio</dt>
            <dd>
              USD {pago.importe_usd}
              {pago.cupon && ` (con el cupón ${pago.cupon})`}
            </dd>
          </div>
          <div>
            <dt className="text-muted">Medio de pago</dt>
            <dd>{describirMetodo(pago.metodo)}</dd>
          </div>
          <div className="rounded-control bg-brand-soft p-3">
            <dt className="text-muted">Cuotas</dt>
            <dd className="font-medium">
              {cuotas === 1
                ? 'Pago en una sola cuota'
                : `${cuotas} cuotas${
                    pago.valor_cuota !== null && pago.moneda
                      ? ` de ${formatearMonto(pago.valor_cuota, pago.moneda)}`
                      : ''
                  }`}
            </dd>
          </div>
          {pago.mp_payment_id && (
            <div>
              <dt className="text-muted">Número de pago de Mercado Pago</dt>
              <dd>{pago.mp_payment_id}</dd>
            </div>
          )}
        </dl>
        <p className="text-muted">Las cuotas las maneja Mercado Pago.</p>
      </section>
    </div>
  )
}
