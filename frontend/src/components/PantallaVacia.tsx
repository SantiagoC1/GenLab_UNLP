import { EmptyState } from './EmptyState'
import { PageContainer } from './PageContainer'
import { PageHeader } from './PageHeader'

interface Props {
  titulo: string
  referencia?: string
}

export function PantallaVacia({ titulo, referencia }: Props) {
  return (
    <PageContainer>
      <PageHeader title={titulo} reference={referencia} />
      <EmptyState>Pantalla pendiente de implementar.</EmptyState>
    </PageContainer>
  )
}
