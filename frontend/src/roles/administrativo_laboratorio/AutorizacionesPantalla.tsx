import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Alert } from '../../components/Alert'
import { Button } from '../../components/Button'
import { FIELD_CLASS } from '../../components/TextField'
import { api, json } from '../../lib/api'
import { downloadFile } from '../../lib/download'

interface Pendiente {
  estudio_id: number
  paciente: string
  obra_social: string
  porcentaje: number
  importe_usd: number
  estado_estudio: string
  motivo_rechazo: string | null
  con_demanda: boolean
  demanda_nombre: string | null
}

interface Registrada {
  estudio_id: number
  estado: string
  resultado: string
  paciente_avisado: boolean
}

const RAIZ = '/presupuesto_pago'
const PENDIENTES_KEY = ['autorizaciones', 'pendientes']

export default function AutorizacionesPantalla() {
  const queryClient = useQueryClient()
  const [seleccionado, setSeleccionado] = useState<number | null>(null)
  const [resultado, setResultado] = useState<'Autorizado' | 'Rechazado'>('Autorizado')
  const [motivo, setMotivo] = useState('')
  const [errorDescarga, setErrorDescarga] = useState<string | null>(null)

  const bandeja = useQuery({
    queryKey: PENDIENTES_KEY,
    queryFn: () => api<Pendiente[]>(`${RAIZ}/autorizaciones-pendientes`),
  })

  const registrar = useMutation({
    mutationFn: (estudio: number) =>
      api<Registrada>(`${RAIZ}/estudios/${estudio}/autorizacion`, {
        method: 'POST',
        ...json({ resultado, ...(resultado === 'Rechazado' ? { motivo: motivo.trim() } : {}) }),
      }),
    onSuccess: () => {
      setSeleccionado(null)
      setMotivo('')
      setResultado('Autorizado')
      return queryClient.invalidateQueries({ queryKey: PENDIENTES_KEY })
    },
  })

  const estudio = bandeja.data?.find((p) => p.estudio_id === seleccionado)
  const faltaMotivo = resultado === 'Rechazado' && motivo.trim() === ''

  return (
    <section>
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">
        Registrar la autorización de la obra social
      </h1>
      <p className="mt-1 text-sm text-slate-500">Escenario 18 · M4-RF7</p>

      <div className="mt-4 space-y-3">
        {registrar.isError && <Alert kind="error">{registrar.error.message}</Alert>}
        {registrar.isSuccess && (
          <Alert kind="success">
            Respuesta registrada: estudio {registrar.data.resultado}.
            {registrar.data.paciente_avisado
              ? ' El paciente recibió un aviso.'
              : ' No se pudo avisar al paciente.'}
          </Alert>
        )}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div>
          <h2 className="font-medium text-slate-900">Autorizaciones pendientes</h2>
          {bandeja.isPending && <p className="mt-2 text-sm text-slate-500">Cargando…</p>}
          {bandeja.isError && <Alert kind="error">{bandeja.error.message}</Alert>}
          {bandeja.data?.length === 0 && (
            <p className="mt-2 text-sm text-slate-500">No hay autorizaciones pendientes.</p>
          )}
          <ul className="mt-2 divide-y divide-slate-200 rounded-lg border border-slate-200 empty:hidden">
            {bandeja.data?.map((p) => (
              <li key={p.estudio_id}>
                <button
                  type="button"
                  aria-pressed={seleccionado === p.estudio_id}
                  onClick={() => {
                    registrar.reset()
                    setErrorDescarga(null)
                    setSeleccionado(p.estudio_id)
                  }}
                  className="flex w-full justify-between gap-4 p-3 text-left text-sm hover:bg-slate-50 aria-pressed:bg-slate-100"
                >
                  <span>
                    Estudio {p.estudio_id} · {p.paciente}
                  </span>
                  <span className="text-slate-500">
                    {p.obra_social}
                    {p.con_demanda && ' · con demanda'}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>

        {estudio && (
          <form
            className="space-y-4 rounded-lg border border-slate-200 p-4 text-sm"
            onSubmit={(event) => {
              event.preventDefault()
              if (!faltaMotivo) registrar.mutate(estudio.estudio_id)
            }}
          >
            <h2 className="font-medium text-slate-900">Respuesta de la obra social</h2>
            <p>
              Paciente: <strong>{estudio.paciente}</strong>
              <br />
              Obra social: <strong>{estudio.obra_social}</strong> (cubre el {estudio.porcentaje}%)
              <br />
              Importe del presupuesto: USD {estudio.importe_usd}
            </p>
            {estudio.con_demanda ? (
              <div className="space-y-1 rounded-md bg-slate-50 p-3">
                <p>
                  El estudio fue rechazado: <em>{estudio.motivo_rechazo}</em>
                </p>
                <p>
                  El paciente adjuntó una demanda ({estudio.demanda_nombre}) para pedir la
                  reautorización.
                </p>
                <button
                  type="button"
                  className="text-teal-700 underline"
                  onClick={() => {
                    setErrorDescarga(null)
                    downloadFile(
                      `${RAIZ}/estudios/${estudio.estudio_id}/demanda`,
                      `demanda-estudio-${estudio.estudio_id}.pdf`,
                    ).catch((error: Error) => setErrorDescarga(error.message))
                  }}
                >
                  Descargar la demanda
                </button>
                {errorDescarga && <Alert kind="error">{errorDescarga}</Alert>}
              </div>
            ) : (
              <p className="text-slate-500">
                Gestioná la autorización por teléfono con la obra social y registrá acá su
                respuesta.
              </p>
            )}
            <fieldset className="space-y-1">
              <legend className="font-medium text-slate-800">Respuesta</legend>
              {(['Autorizado', 'Rechazado'] as const).map((opcion) => (
                <label key={opcion} className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="resultado"
                    value={opcion}
                    checked={resultado === opcion}
                    onChange={() => setResultado(opcion)}
                  />
                  {opcion}
                </label>
              ))}
            </fieldset>
            {resultado === 'Rechazado' && (
              <div>
                <label htmlFor="motivo" className="block font-medium text-slate-800">
                  Motivo del rechazo
                </label>
                <textarea
                  id="motivo"
                  rows={3}
                  maxLength={500}
                  className={FIELD_CLASS}
                  value={motivo}
                  onChange={(e) => setMotivo(e.target.value)}
                />
              </div>
            )}
            <Button type="submit" loading={registrar.isPending} disabled={faltaMotivo}>
              Registrar la respuesta
            </Button>
          </form>
        )}
      </div>
    </section>
  )
}
