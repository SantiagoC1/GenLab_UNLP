import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Alert } from '../../components/Alert'
import { Button } from '../../components/Button'
import { SelectField } from '../../components/SelectField'
import { api } from '../../lib/api'
import { MIS_ESTUDIOS_KEY, useMisEstudios } from '../../lib/presupuesto'

interface DemandaEnviada {
  estudio_id: number
  demanda_nombre: string
  administrativo_avisado: boolean
}

function esPdf(archivo: File): boolean {
  return archivo.type === 'application/pdf' || archivo.name.toLowerCase().endsWith('.pdf')
}

export default function DemandaPantalla() {
  const queryClient = useQueryClient()
  const estudios = useMisEstudios()
  const [estudioId, setEstudioId] = useState<number | null>(null)
  const [archivo, setArchivo] = useState<File | null>(null)
  const [errorArchivo, setErrorArchivo] = useState<string | null>(null)

  const enviar = useMutation({
    mutationFn: (datos: { estudio: number; archivo: File }) =>
      api<DemandaEnviada>(`/presupuesto_pago/mis-estudios/${datos.estudio}/demanda`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/pdf',
          'X-Nombre-Archivo': encodeURIComponent(datos.archivo.name),
        },
        body: datos.archivo,
      }),
    onSuccess: () => {
      setArchivo(null)
      return queryClient.invalidateQueries({ queryKey: MIS_ESTUDIOS_KEY })
    },
  })

  const rechazados = (estudios.data ?? []).filter((e) => e.estado === 'Rechazado')
  const estudio = rechazados.find((e) => e.id === (estudioId ?? rechazados[0]?.id))
  const cobertura = estudio?.cobertura

  return (
    <section>
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">
        Solicitar la reautorización con una demanda
      </h1>
      <p className="mt-1 text-sm text-slate-500">Escenario 19 · M4-RF8</p>

      <div className="mt-4 space-y-3">
        {estudios.isPending && <p className="text-sm text-slate-500">Cargando…</p>}
        {estudios.isError && <Alert kind="error">{estudios.error.message}</Alert>}
        {enviar.isError && <Alert kind="error">{enviar.error.message}</Alert>}
        {enviar.isSuccess && (
          <Alert kind="success">
            Recibimos tu demanda ({enviar.data.demanda_nombre}). El laboratorio la va a revisar y
            vas a recibir un aviso con la respuesta.
          </Alert>
        )}
      </div>

      {estudios.data && !estudio && (
        <p className="mt-4 text-sm text-slate-500">No tenés estudios Rechazados.</p>
      )}

      {estudio && cobertura && (
        <div className="mt-6 max-w-lg space-y-4 text-sm">
          {rechazados.length > 1 && (
            <SelectField
              label="Estudio"
              value={estudio.id}
              onChange={(e) => {
                setEstudioId(Number(e.target.value))
                enviar.reset()
              }}
            >
              {rechazados.map((e) => (
                <option key={e.id} value={e.id}>
                  Estudio {e.id}
                </option>
              ))}
            </SelectField>
          )}
          <div className="rounded-lg border border-slate-200 p-4">
            <p>
              La obra social <strong>{cobertura.obra_social}</strong> rechazó el estudio{' '}
              {estudio.id}.
            </p>
            <p className="mt-2 text-slate-500">Motivo del rechazo</p>
            <p className="font-medium text-slate-900">{cobertura.motivo_rechazo}</p>
          </div>

          {cobertura.demanda_enviada ? (
            <Alert kind="info">
              Ya enviaste la demanda ({cobertura.demanda_nombre}). El estudio sigue Rechazado hasta
              que el laboratorio registre la nueva respuesta de la obra social.
            </Alert>
          ) : (
            <form
              className="space-y-3"
              onSubmit={(event) => {
                event.preventDefault()
                if (archivo) enviar.mutate({ estudio: estudio.id, archivo })
              }}
            >
              <div>
                <label htmlFor="demanda" className="block font-medium text-slate-800">
                  PDF de la demanda
                </label>
                <input
                  id="demanda"
                  type="file"
                  accept="application/pdf"
                  className="mt-1 block w-full"
                  onChange={(e) => {
                    const elegido = e.target.files?.[0] ?? null
                    enviar.reset()
                    if (elegido && !esPdf(elegido)) {
                      setArchivo(null)
                      setErrorArchivo('Solo se aceptan archivos PDF.')
                      return
                    }
                    setErrorArchivo(null)
                    setArchivo(elegido)
                  }}
                />
              </div>
              {errorArchivo && <Alert kind="error">{errorArchivo}</Alert>}
              <Button type="submit" loading={enviar.isPending} disabled={!archivo}>
                Pedir la reautorización
              </Button>
            </form>
          )}
        </div>
      )}
    </section>
  )
}
