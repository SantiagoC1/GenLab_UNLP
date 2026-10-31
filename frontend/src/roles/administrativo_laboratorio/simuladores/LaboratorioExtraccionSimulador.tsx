import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert } from '../../../components/Alert'
import { Button } from '../../../components/Button'
import { api } from '../../../lib/api'
import { formatearFechaHora } from '../../../lib/turnos'

interface Agenda {
  turno_id: number
  estudio_id: number
  paciente: string
  laboratorio: string
  inicio: string
  ya_paso: boolean
  inasistencias: number
}

interface Inasistencia {
  turno: { id: number }
  inasistencias: number
  limite: number
  limite_alcanzado: boolean
  paciente_avisado: boolean
}

const AGENDA_KEY = ['turnos', 'agenda']

/**
 * Simula al laboratorio de extracción, que no opera en la plataforma (M10-RF4): informa lo que
 * pasó con cada turno, por ejemplo que el paciente no asistió.
 */
export default function LaboratorioExtraccionSimulador() {
  const queryClient = useQueryClient()

  const agenda = useQuery({
    queryKey: AGENDA_KEY,
    queryFn: () => api<Agenda[]>('/turnos/agenda'),
  })

  const inasistencia = useMutation({
    mutationFn: (turno: number) =>
      api<Inasistencia>(`/turnos/${turno}/inasistencia`, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['turnos'] }),
  })

  return (
    <section aria-labelledby="simulador-laboratorio">
      <h2 id="simulador-laboratorio" className="text-lg font-semibold text-slate-900">
        Laboratorio de extracción
      </h2>
      <p className="mt-1 text-sm text-slate-500">
        Turnos programados de los laboratorios de extracción. El laboratorio no opera en la
        plataforma: acá se informa lo que ocurrió con cada turno.
      </p>

      <div className="mt-4 space-y-3">
        {agenda.isPending && <p className="text-sm text-slate-500">Cargando…</p>}
        {agenda.isError && <Alert kind="error">{agenda.error.message}</Alert>}
        {inasistencia.isError && <Alert kind="error">{inasistencia.error.message}</Alert>}
        {inasistencia.isSuccess && (
          <Alert kind="success">
            Inasistencia registrada: el paciente acumula {inasistencia.data.inasistencias} de{' '}
            {inasistencia.data.limite}.
            {inasistencia.data.limite_alcanzado && ' Llegó al límite de inasistencias.'}
            {inasistencia.data.paciente_avisado
              ? ' Se le avisó al paciente.'
              : ' No se pudo avisar al paciente.'}
          </Alert>
        )}
      </div>

      {agenda.data?.length === 0 && (
        <p className="mt-3 text-sm text-slate-500">No hay turnos programados.</p>
      )}
      <ul className="mt-3 divide-y divide-slate-200 rounded-lg border border-slate-200 empty:hidden">
        {agenda.data?.map((turno) => (
          <li
            key={turno.turno_id}
            className="flex flex-wrap items-center justify-between gap-3 p-3 text-sm"
          >
            <div>
              <p className="font-medium text-slate-900">
                {turno.paciente} · estudio {turno.estudio_id}
              </p>
              <p className="text-slate-600">
                {formatearFechaHora(turno.inicio)} · {turno.laboratorio}
              </p>
              {turno.inasistencias > 0 && (
                <p className="text-slate-500">Inasistencias previas: {turno.inasistencias}</p>
              )}
            </div>
            <Button
              variant="secondary"
              disabled={!turno.ya_paso}
              title={turno.ya_paso ? undefined : 'El horario del turno todavía no pasó'}
              loading={inasistencia.isPending && inasistencia.variables === turno.turno_id}
              onClick={() => {
                inasistencia.reset()
                inasistencia.mutate(turno.turno_id)
              }}
            >
              Registrar inasistencia
            </Button>
          </li>
        ))}
      </ul>
    </section>
  )
}
