import { useState } from 'react'
import { Alert } from '../../components/Alert'
import { Button } from '../../components/Button'
import { PathologyForm } from '../../components/PathologyForm'
import { ApiError } from '../../lib/api'
import { usePathologies, type Pathology } from '../../lib/pathologies'

type Mode = { kind: 'idle' } | { kind: 'creating' } | { kind: 'editing'; id: number }

export default function PatologiasPantalla() {
  const pathologies = usePathologies()
  const [mode, setMode] = useState<Mode>({ kind: 'idle' })
  const [saved, setSaved] = useState('')

  const finish = (pathology: Pathology) => {
    setSaved(`Se guardó la patología ${pathology.name}.`)
    setMode({ kind: 'idle' })
  }

  const open = (next: Mode) => {
    setSaved('')
    setMode(next)
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">Patologías lisosomales</h1>
        {mode.kind !== 'creating' && (
          <Button onClick={() => open({ kind: 'creating' })}>Nueva patología</Button>
        )}
      </div>

      {saved && <Alert kind="success">{saved}</Alert>}

      {mode.kind === 'creating' && (
        <PathologyForm onSaved={finish} onCancel={() => setMode({ kind: 'idle' })} />
      )}

      {pathologies.isPending && <Alert>Cargando patologías…</Alert>}

      {pathologies.isError && (
        <Alert kind="error">
          {pathologies.error instanceof ApiError
            ? pathologies.error.message
            : 'No pudimos cargar las patologías. Revisá tu conexión.'}{' '}
          <Button variant="secondary" onClick={() => pathologies.refetch()}>
            Reintentar
          </Button>
        </Alert>
      )}

      {pathologies.data?.length === 0 && <Alert>Todavía no hay patologías cargadas.</Alert>}

      <ul className="space-y-4">
        {pathologies.data?.map((pathology) => (
          <li key={pathology.id}>
            {mode.kind === 'editing' && mode.id === pathology.id ? (
              <PathologyForm
                pathology={pathology}
                onSaved={finish}
                onCancel={() => setMode({ kind: 'idle' })}
              />
            ) : (
              <article className="rounded-lg border border-slate-300 bg-white p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h2 className="text-lg font-semibold text-slate-900">{pathology.name}</h2>
                  <Button
                    variant="secondary"
                    aria-label={`Editar síntomas de ${pathology.name}`}
                    onClick={() => open({ kind: 'editing', id: pathology.id })}
                  >
                    Editar síntomas
                  </Button>
                </div>
                <p className="mt-2 text-sm text-slate-800">
                  <span className="font-medium">Síntoma cardinal:</span>{' '}
                  {pathology.cardinal?.term ?? 'Sin definir'}
                </p>
                <p className="mt-1 text-sm text-slate-800">
                  <span className="font-medium">Síntomas secundarios:</span>{' '}
                  {pathology.secondary.map((symptom) => symptom.term).join(', ') || 'Sin definir'}
                </p>
              </article>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
