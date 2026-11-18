import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Alert } from '../../../components/Alert'
import { Button } from '../../../components/Button'
import { api, json } from '../../../lib/api'
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

interface MuestraRecibida {
  estudio_id: number
  estado: string
  volumen_ml: number
  volumen_suficiente: boolean
  listo_para_retirar: boolean
  remuestreo: { medico_avisado: boolean; paciente_avisado: boolean } | null
}

const AGENDA_KEY = ['turnos', 'agenda']
const VOLUMEN_MINIMO_ML = 2

/**
 * Simula al laboratorio de extracción, que no opera en la plataforma (M10-RF4): informa lo que
 * pasó con cada turno. Puede avisar que el paciente no asistió (escenario 23) o mandar el mensaje
 * del bot de Telegram con el estudio y el volumen de la muestra (escenario 24).
 */
export default function LaboratorioExtraccionSimulador() {
  const queryClient = useQueryClient()
  const [volumenes, setVolumenes] = useState<Record<number, string>>({})

  const agenda = useQuery({
    queryKey: AGENDA_KEY,
    queryFn: () => api<Agenda[]>('/turnos/agenda'),
  })

  const inasistencia = useMutation({
    mutationFn: (turno: number) =>
      api<Inasistencia>(`/turnos/${turno}/inasistencia`, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['turnos'] }),
  })

  const muestra = useMutation({
    mutationFn: (datos: { estudio: number; volumen: number }) =>
      api<MuestraRecibida>('/turnos/notificaciones-muestra', {
        method: 'POST',
        ...json({ estudio_id: datos.estudio, volumen_ml: datos.volumen }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['turnos'] }),
  })

  function limpiar() {
    inasistencia.reset()
    muestra.reset()
  }

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
        {muestra.isError && <Alert kind="error">{muestra.error.message}</Alert>}
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
        {muestra.isSuccess && (
          <Alert kind="success">
            Notificación recibida: estudio {muestra.data.estudio_id}, {muestra.data.volumen_ml} ml.{' '}
            {muestra.data.listo_para_retirar
              ? 'El estudio pasó a Listo para retirar.'
              : `El volumen es menor a ${VOLUMEN_MINIMO_ML} ml: no se habilita el retiro y se habilitó un remuestreo sin costo.`}
            {muestra.data.remuestreo &&
              ` Se avisó ${muestra.data.remuestreo.medico_avisado ? 'al médico y ' : ''}${
                muestra.data.remuestreo.paciente_avisado
                  ? 'al paciente'
                  : 'sin poder avisar al paciente'
              }.`}
          </Alert>
        )}
      </div>

      {agenda.data?.length === 0 && (
        <p className="mt-3 text-sm text-slate-500">No hay turnos programados.</p>
      )}
      <ul className="mt-3 divide-y divide-slate-200 rounded-lg border border-slate-200 empty:hidden">
        {agenda.data?.map((turno) => {
          const volumen = Number(volumenes[turno.turno_id])
          const volumenValido = volumenes[turno.turno_id] !== undefined && volumen > 0
          return (
            <li key={turno.turno_id} className="space-y-3 p-3 text-sm">
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

              <div className="flex flex-wrap items-end gap-3">
                <div>
                  <label
                    htmlFor={`volumen-${turno.turno_id}`}
                    className="block text-xs font-medium text-slate-700"
                  >
                    Volumen de la muestra (ml)
                  </label>
                  <input
                    id={`volumen-${turno.turno_id}`}
                    type="number"
                    min={0}
                    step={0.1}
                    value={volumenes[turno.turno_id] ?? ''}
                    onChange={(e) =>
                      setVolumenes((actuales) => ({
                        ...actuales,
                        [turno.turno_id]: e.target.value,
                      }))
                    }
                    className="mt-1 w-28 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
                  />
                </div>
                <Button
                  disabled={!volumenValido}
                  loading={muestra.isPending && muestra.variables?.estudio === turno.estudio_id}
                  onClick={() => {
                    limpiar()
                    muestra.mutate({ estudio: turno.estudio_id, volumen })
                  }}
                >
                  Enviar mensaje de Telegram
                </Button>
                <Button
                  variant="secondary"
                  disabled={!turno.ya_paso}
                  title={turno.ya_paso ? undefined : 'El horario del turno todavía no pasó'}
                  loading={inasistencia.isPending && inasistencia.variables === turno.turno_id}
                  onClick={() => {
                    limpiar()
                    inasistencia.mutate(turno.turno_id)
                  }}
                >
                  Registrar inasistencia
                </Button>
              </div>
              {volumenValido && (
                <p className="text-xs text-slate-500">
                  Mensaje del bot: «Muestra tomada · estudio {turno.estudio_id} · {volumen} ml»
                </p>
              )}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
