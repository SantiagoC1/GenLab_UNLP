import { useState } from 'react'
import { Alert } from '../../components/Alert'
import { Button } from '../../components/Button'
import { ApiError } from '../../lib/api'
import {
  CDSS_STRATEGIES,
  useCdssStrategy,
  useSaveCdssStrategy,
  type CdssStrategy,
} from '../../lib/pathologies'

export default function EstrategiaCdssPantalla() {
  const current = useCdssStrategy()
  const save = useSaveCdssStrategy()
  const [chosen, setChosen] = useState<CdssStrategy | null>(null)

  const selected = chosen ?? current.data?.strategy ?? null
  const changed = selected !== null && selected !== current.data?.strategy

  return (
    <section className="space-y-6">
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">Estrategia del CDSS</h1>

      {current.isPending && <Alert>Cargando la estrategia…</Alert>}

      {current.isError && (
        <Alert kind="error">
          {current.error instanceof ApiError
            ? current.error.message
            : 'No pudimos cargar la estrategia. Revisá tu conexión.'}{' '}
          <Button variant="secondary" onClick={() => current.refetch()}>
            Reintentar
          </Button>
        </Alert>
      )}

      {current.data && (
        <form
          onSubmit={(event) => {
            event.preventDefault()
            if (selected) save.mutate(selected, { onSuccess: () => setChosen(null) })
          }}
          className="space-y-4"
        >
          <fieldset className="space-y-3">
            <legend className="text-sm font-medium text-slate-800">
              Cómo elige la patología el sistema de soporte a la decisión
            </legend>
            {CDSS_STRATEGIES.map((strategy) => (
              <label
                key={strategy.value}
                className="flex cursor-pointer items-start gap-3 rounded-md border border-slate-300 bg-white p-3"
              >
                <input
                  type="radio"
                  name="cdss-strategy"
                  value={strategy.value}
                  checked={selected === strategy.value}
                  onChange={() => {
                    save.reset()
                    setChosen(strategy.value)
                  }}
                  className="mt-1"
                />
                <span>
                  <span className="block text-sm font-medium text-slate-900">{strategy.label}</span>
                  <span className="block text-sm text-slate-600">{strategy.description}</span>
                </span>
              </label>
            ))}
          </fieldset>

          {save.isError && (
            <Alert kind="error">
              {save.error instanceof ApiError
                ? save.error.message
                : 'No pudimos guardar. Revisá tu conexión.'}
            </Alert>
          )}
          {save.isSuccess && <Alert kind="success">Se guardó la estrategia del CDSS.</Alert>}

          <Button type="submit" loading={save.isPending} disabled={!changed}>
            Guardar estrategia
          </Button>
        </form>
      )}
    </section>
  )
}
