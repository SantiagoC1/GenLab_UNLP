import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Alert } from '../../components/Alert'
import { Button } from '../../components/Button'
import { api } from '../../lib/api'
import { downloadFile } from '../../lib/download'
import { MIS_TURNOS_KEY, formatearFechaHora, type Turno } from '../../lib/turnos'

export default function DocumentosPantalla() {
  const [error, setError] = useState<string | null>(null)

  const turnos = useQuery({
    queryKey: MIS_TURNOS_KEY,
    queryFn: () => api<Turno[]>('/turnos/mis-turnos'),
  })
  const vigentes = (turnos.data ?? []).filter((t) => t.estado === 'Programado')

  function descargar(ruta: string | null, nombre: string) {
    if (!ruta) return
    setError(null)
    downloadFile(ruta, nombre).catch((e: Error) => setError(e.message))
  }

  return (
    <section>
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">
        Orden de extracción y consentimiento informado
      </h1>
      <p className="mt-1 text-sm text-slate-500">Escenario 21 · M6-RF6</p>

      <div className="mt-4 space-y-3">
        {turnos.isPending && <p className="text-sm text-slate-500">Cargando…</p>}
        {turnos.isError && <Alert kind="error">{turnos.error.message}</Alert>}
        {error && <Alert kind="error">{error}</Alert>}
      </div>

      {turnos.data && vigentes.length === 0 && (
        <p className="mt-4 text-sm text-slate-500">
          No tenés un turno de extracción vigente.{' '}
          <Link to="../turno" className="font-medium text-teal-700 underline">
            Sacar un turno
          </Link>
        </p>
      )}

      <ul className="mt-6 space-y-4">
        {vigentes.map((turno) => (
          <li key={turno.id} className="max-w-xl rounded-lg border border-slate-200 p-4 text-sm">
            <p className="font-medium text-slate-900">Estudio {turno.estudio_id}</p>
            <p>{formatearFechaHora(turno.inicio)}</p>
            <p className="text-slate-600">
              {turno.laboratorio.nombre} · {turno.laboratorio.direccion}
            </p>
            <div className="mt-3 flex flex-wrap gap-3">
              <Button
                variant="secondary"
                onClick={() =>
                  descargar(turno.orden_extraccion_url, `orden-extraccion-${turno.id}.pdf`)
                }
              >
                Descargar la orden de extracción
              </Button>
              <Button
                variant="secondary"
                onClick={() => descargar(turno.consentimiento_url, 'consentimiento-informado.pdf')}
              >
                Descargar el consentimiento informado
              </Button>
            </div>
            <p className="mt-3 text-slate-600">
              Imprimí el consentimiento informado, completalo y firmalo (si sos menor de edad lo
              firman tus padres). Se entrega en papel en el laboratorio de extracción el día del
              turno: no se sube a la plataforma.
            </p>
          </li>
        ))}
      </ul>
    </section>
  )
}
