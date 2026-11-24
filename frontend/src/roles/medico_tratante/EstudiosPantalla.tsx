import { PageContainer } from '../../components/PageContainer'
import { PageHeader } from '../../components/PageHeader'
import { StudyList } from '../../components/StudyList'
import { useDoctorStudies } from '../../lib/studies'

/** Los estudios que pidió el médico tratante, con el estado de cada uno. */
export default function EstudiosPantalla() {
  const studies = useDoctorStudies()
  return (
    <PageContainer>
      <PageHeader title="Mis estudios" reference="Escenario 37 · M8-RF6" />
      <StudyList query={studies} emptyMessage="Todavía no pediste ningún estudio." />
    </PageContainer>
  )
}
