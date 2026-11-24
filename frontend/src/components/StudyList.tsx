import type { UseQueryResult } from '@tanstack/react-query'
import type { StudyListItem } from '../lib/studies'
import { STATE_LABELS } from '../lib/studies'
import { Alert } from './Alert'
import { Card } from './Card'
import { EmptyState } from './EmptyState'
import { LoadingBlock } from './Skeleton'

interface Props {
  query: UseQueryResult<StudyListItem[]>
  emptyMessage: string
}

/** Fecha corta en español, por ejemplo "20/11/2026". */
function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('es-AR')
}

/**
 * Lista de estudios con su paciente, patologías y estado. La comparten
 * "Mis estudios" del médico y la del paciente: cambia solo la consulta.
 */
export function StudyList({ query, emptyMessage }: Props) {
  if (query.isPending) return <LoadingBlock />
  if (query.isError) return <Alert kind="error">{query.error.message}</Alert>
  if (query.data.length === 0) return <EmptyState>{emptyMessage}</EmptyState>

  return (
    <ul className="space-y-3">
      {query.data.map((study) => (
        <li key={study.id}>
          <Card>
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h2 className="font-medium text-ink">
                  Estudio {study.id} · {study.patient_name}
                </h2>
                <p className="text-sm text-muted">DNI {study.patient_dni}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                {study.pompe_urgent && (
                  <span className="rounded-control bg-red-100 px-2 py-1 text-sm font-medium text-red-800">
                    Pompe urgente
                  </span>
                )}
                <span className="rounded-control bg-brand-tint px-2 py-1 text-sm font-medium text-brand-strong">
                  {STATE_LABELS[study.state] ?? study.state}
                </span>
              </div>
            </div>
            <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-3">
              <div>
                <dt className="text-muted">Patologías</dt>
                <dd>{study.pathologies.join(', ')}</dd>
              </div>
              <div>
                <dt className="text-muted">Genes a analizar</dt>
                <dd>{study.gene_count}</dd>
              </div>
              <div>
                <dt className="text-muted">Pedido el</dt>
                <dd>{formatDate(study.created_at)}</dd>
              </div>
            </dl>
          </Card>
        </li>
      ))}
    </ul>
  )
}
