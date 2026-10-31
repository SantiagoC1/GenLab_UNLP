import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Alert } from '../../components/Alert'
import { Button } from '../../components/Button'
import { api } from '../../lib/api'
import {
  HABILITADOS_KEY,
  LIMITE_INASISTENCIAS,
  MIS_TURNOS_KEY,
  formatearFechaHora,
  type Habilitado,
  type Turno,
} from '../../lib/turnos'

interface Cancelacion {
  turno: Turno
  estudio_estado: string
}

export default function TurnosPantalla() {
  const queryClient = useQueryClient()
  const [confirmando, setConfirmando] = useState<number | null>(null)

  const turnos = useQuery({
    queryKey: MIS_TURNOS_KEY,
    queryFn: () => api<Turno[]>('/turnos/mis-turnos'),
  })

  const habilitados = useQuery({
    queryKey: HABILITADOS_KEY,
    queryFn: () => api<Habilitado[]>('/turnos/habilitados'),
  })
  // M6-RF8: studies that missed an appointment and can book again.
  const reprogramables = (habilitados.data ?? []).filter(
    (h) => h.motivo === 'nueva_reserva' && h.inasistencias > 0,
  )

  const cancelar = useMutation({
    mutationFn: (turno: number) =>
      api<Cancelacion>(`/turnos/${turno}/cancelar`, { method: 'POST' }),
    onSuccess: () => {
      setConfirmando(null)
      return queryClient.invalidateQueries({ queryKey: ['turnos'] })
    },
    onError: () => setConfirmando(null),
  })

  return (
    <section>
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">Mis turnos</h1>
      <p className="mt-1 text-sm text-slate-500">Escenarios 22 y 23 · M6-RF7, RF8</p>

      <div className="mt-4 space-y-3">
        {turnos.isPending && <p className="text-sm text-slate-500">Cargando…</p>}
        {turnos.isError && <Alert kind="error">{turnos.error.message}</Alert>}
        {cancelar.isError && <Alert kind="error">{cancelar.error.message}</Alert>}
        {cancelar.isSuccess && (
          <Alert kind="success">
            Cancelaste el turno, sin costo. Tu estudio vuelve a estar habilitado para{' '}
            <Link to="../turno" className="font-medium underline">
              sacar un turno nuevo
            </Link>
            .
          </Alert>
        )}
      </div>

      {reprogramables.map((h) => (
        <Alert key={h.estudio_id} kind="info">
          Estudio {h.estudio_id}: registramos {h.inasistencias}{' '}
          {h.inasistencias === 1 ? 'inasistencia' : 'inasistencias'}.{' '}
          {h.inasistencias >= LIMITE_INASISTENCIAS &&
            `Llegaste al límite de ${LIMITE_INASISTENCIAS} inasistencias; por ahora no se aplica ninguna restricción. `}
          <Link to="../turno" className="font-medium underline">
            Reprogramar el turno
          </Link>
        </Alert>
      ))}

      {turnos.data?.length === 0 && (
        <p className="mt-4 text-sm text-slate-500">
          Todavía no sacaste ningún turno.{' '}
          <Link to="../turno" className="font-medium text-teal-700 underline">
            Sacar un turno
          </Link>
        </p>
      )}

      <ul className="mt-6 space-y-4">
        {turnos.data?.map((turno) => (
          <li key={turno.id} className="max-w-xl rounded-lg border border-slate-200 p-4 text-sm">
            <div className="flex justify-between gap-4">
              <p className="font-medium text-slate-900">Estudio {turno.estudio_id}</p>
              <span className="rounded bg-slate-100 px-2 py-0.5 text-slate-700">
                {turno.estado}
              </span>
            </div>
            <p className="mt-1">{formatearFechaHora(turno.inicio)}</p>
            <p className="text-slate-600">
              {turno.laboratorio.nombre} · {turno.laboratorio.direccion}
            </p>

            {turno.estado === 'Programado' && !turno.puede_cancelar && (
              <p className="mt-2 text-slate-500">
                El horario de este turno ya pasó, por eso no se puede cancelar.
              </p>
            )}

            {turno.puede_cancelar &&
              (confirmando === turno.id ? (
                <div className="mt-3 space-y-2 rounded-md bg-slate-50 p-3">
                  <p>¿Querés cancelar este turno? No tiene costo y vas a poder sacar uno nuevo.</p>
                  <div className="flex gap-2">
                    <Button loading={cancelar.isPending} onClick={() => cancelar.mutate(turno.id)}>
                      Sí, cancelar el turno
                    </Button>
                    <Button variant="secondary" onClick={() => setConfirmando(null)}>
                      No, conservarlo
                    </Button>
                  </div>
                </div>
              ) : (
                <Button
                  variant="secondary"
                  className="mt-3"
                  onClick={() => {
                    cancelar.reset()
                    setConfirmando(turno.id)
                  }}
                >
                  Cancelar el turno
                </Button>
              ))}
          </li>
        ))}
      </ul>
    </section>
  )
}
