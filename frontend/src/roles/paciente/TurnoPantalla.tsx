import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Alert } from '../../components/Alert'
import { Button } from '../../components/Button'
import { MapaLaboratorios } from '../../components/MapaLaboratorios'
import { SelectField } from '../../components/SelectField'
import { TextField } from '../../components/TextField'
import { api, ApiError, json } from '../../lib/api'
import {
  HORIZONTE_DIAS,
  formatearFechaHora,
  formatearHora,
  HABILITADOS_KEY,
  hoyEnArgentina,
  sumarDias,
  type Habilitado,
  type Laboratorio,
  type Turno,
} from '../../lib/turnos'

interface TurnosLibres {
  laboratorio_id: number
  fecha: string
  turnos: string[]
  motivo: string | null
}

export default function TurnoPantalla() {
  const queryClient = useQueryClient()
  const hoy = hoyEnArgentina()
  const [estudioId, setEstudioId] = useState<number | null>(null)
  const [provincia, setProvincia] = useState('')
  const [laboratorio, setLaboratorio] = useState<Laboratorio | null>(null)
  const [fecha, setFecha] = useState(hoy)
  const [inicio, setInicio] = useState<string | null>(null)

  const habilitados = useQuery({
    queryKey: HABILITADOS_KEY,
    queryFn: () => api<Habilitado[]>('/turnos/habilitados'),
  })
  const laboratorios = useQuery({
    queryKey: ['turnos', 'laboratorios'],
    queryFn: () => api<Laboratorio[]>('/turnos/laboratorios'),
  })
  const libres = useQuery({
    queryKey: ['turnos', 'libres', laboratorio?.id, fecha],
    queryFn: () =>
      api<TurnosLibres>(`/turnos/laboratorios/${laboratorio?.id}/turnos-libres?fecha=${fecha}`),
    enabled: laboratorio !== null && fecha !== '',
  })

  const reservar = useMutation({
    mutationFn: (datos: { estudio: number; laboratorio: number; inicio: string }) =>
      api<Turno>('/turnos/reservas', {
        method: 'POST',
        ...json({
          estudio_id: datos.estudio,
          laboratorio_id: datos.laboratorio,
          inicio: datos.inicio,
        }),
      }),
    onSuccess: () => {
      setInicio(null)
      return queryClient.invalidateQueries({ queryKey: ['turnos'] })
    },
    onError: (error) => {
      // M6-RF5: if someone took the appointment first, show the free ones again.
      setInicio(null)
      if (error instanceof ApiError && error.code === 'turno_ocupado') {
        return queryClient.invalidateQueries({ queryKey: ['turnos', 'libres'] })
      }
    },
  })

  const estudio = habilitados.data?.some((h) => h.estudio_id === estudioId)
    ? estudioId
    : (habilitados.data?.[0]?.estudio_id ?? null)
  const provincias = [...new Set((laboratorios.data ?? []).map((l) => l.provincia))].sort()
  const visibles = (laboratorios.data ?? []).filter((l) => !provincia || l.provincia === provincia)

  function elegirLaboratorio(lab: Laboratorio) {
    reservar.reset()
    setInicio(null)
    setLaboratorio(lab)
  }

  return (
    <section>
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">
        Sacar turno de extracción
      </h1>
      <p className="mt-1 text-sm text-slate-500">Escenario 20 · M6-RF1 a RF5</p>

      <div className="mt-4 space-y-3">
        {habilitados.isError && <Alert kind="error">{habilitados.error.message}</Alert>}
        {laboratorios.isError && <Alert kind="error">{laboratorios.error.message}</Alert>}
        {reservar.isError && <Alert kind="error">{reservar.error.message}</Alert>}
        {reservar.isSuccess && (
          <Alert kind="success">
            Turno reservado en {reservar.data.laboratorio.nombre} para el{' '}
            {formatearFechaHora(reservar.data.inicio)}. Te vamos a mandar un recordatorio por mail.
            Tu orden de extracción y el consentimiento informado ya están en{' '}
            <Link to="../documentos" className="font-medium underline">
              Documentos
            </Link>
            .
          </Alert>
        )}
      </div>

      {habilitados.data && habilitados.data.length === 0 && !reservar.isSuccess && (
        <p className="mt-4 text-sm text-slate-500">
          No tenés estudios habilitados para sacar turno. Un estudio puede sacar turno cuando está
          Pagado o Autorizado.
        </p>
      )}

      {estudio !== null && (
        <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,20rem)_1fr]">
          <div className="space-y-4">
            {habilitados.data && habilitados.data.length > 1 && (
              <SelectField
                label="Estudio"
                value={estudio}
                onChange={(e) => setEstudioId(Number(e.target.value))}
              >
                {habilitados.data.map((h) => (
                  <option key={h.estudio_id} value={h.estudio_id}>
                    Estudio {h.estudio_id}
                  </option>
                ))}
              </SelectField>
            )}
            <SelectField
              label="Provincia"
              value={provincia}
              onChange={(e) => setProvincia(e.target.value)}
            >
              <option value="">Todo el país</option>
              {provincias.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </SelectField>
            <MapaLaboratorios
              laboratorios={visibles}
              seleccionado={laboratorio?.id ?? null}
              onElegir={elegirLaboratorio}
            />
          </div>

          <div className="space-y-4">
            <div>
              <h2 className="font-medium text-slate-900">Laboratorios de extracción</h2>
              {laboratorios.isPending && <p className="mt-2 text-sm text-slate-500">Cargando…</p>}
              <ul className="mt-2 max-h-64 divide-y divide-slate-200 overflow-y-auto rounded-lg border border-slate-200">
                {visibles.map((lab) => (
                  <li key={lab.id}>
                    <button
                      type="button"
                      aria-pressed={laboratorio?.id === lab.id}
                      onClick={() => elegirLaboratorio(lab)}
                      className="block w-full p-3 text-left text-sm hover:bg-slate-50 aria-pressed:bg-slate-100"
                    >
                      <span className="font-medium">{lab.nombre}</span>
                      <span className="block text-slate-500">
                        {lab.direccion}
                        {lab.proximo_turno
                          ? ` · Próximo turno: ${formatearFechaHora(lab.proximo_turno)}`
                          : ' · Sin turnos libres'}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>

            {laboratorio && (
              <div className="space-y-3">
                <h2 className="font-medium text-slate-900">Turnos de {laboratorio.nombre}</h2>
                <div className="max-w-xs">
                  <TextField
                    label="Día"
                    type="date"
                    min={hoy}
                    max={sumarDias(hoy, HORIZONTE_DIAS)}
                    value={fecha}
                    onChange={(e) => {
                      setInicio(null)
                      setFecha(e.target.value)
                    }}
                  />
                </div>
                {libres.isPending && <p className="text-sm text-slate-500">Cargando turnos…</p>}
                {libres.isError && <Alert kind="error">{libres.error.message}</Alert>}
                {libres.data?.motivo && (
                  <p className="text-sm text-slate-600">{libres.data.motivo}</p>
                )}
                <ul className="flex flex-wrap gap-2">
                  {libres.data?.turnos.map((turno) => (
                    <li key={turno}>
                      <button
                        type="button"
                        aria-pressed={inicio === turno}
                        onClick={() => setInicio(turno)}
                        className="rounded-md border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50 aria-pressed:border-teal-700 aria-pressed:bg-teal-700 aria-pressed:text-white"
                      >
                        {formatearHora(turno)}
                      </button>
                    </li>
                  ))}
                </ul>
                <Button
                  loading={reservar.isPending}
                  disabled={inicio === null}
                  onClick={() =>
                    inicio && reservar.mutate({ estudio, laboratorio: laboratorio.id, inicio })
                  }
                >
                  Reservar el turno
                </Button>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  )
}
