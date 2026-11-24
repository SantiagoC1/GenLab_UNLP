import { PageContainer } from '../../components/PageContainer'
import { PageHeader } from '../../components/PageHeader'
import { StudyList } from '../../components/StudyList'
import { usePatientStudies } from '../../lib/studies'

/** Los estudios del paciente, con el estado de cada uno. */
export default function EstudiosPantalla() {
  const studies = usePatientStudies()
  return (
    <PageContainer>
      <PageHeader title="Mis estudios" reference="Escenarios 11 a 14" />
      <StudyList query={studies} emptyMessage="Todavía no tenés estudios." />
    </PageContainer>
  )
}
