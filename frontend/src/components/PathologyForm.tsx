import { useRef, useState } from 'react'
import { ApiError } from '../lib/api'
import {
  MIN_SECONDARY_SYMPTOMS,
  useCreatePathology,
  useReplacePathologySymptoms,
  type Pathology,
} from '../lib/pathologies'
import type { Symptom } from '../lib/symptoms'
import { Alert } from './Alert'
import { Button } from './Button'
import { SymptomSearch } from './SymptomSearch'
import { TextField } from './TextField'

interface Props {
  /** Con una patología se editan sus síntomas (escenario 6); sin ella se da de alta (escenario 5). */
  pathology?: Pathology
  onSaved: (pathology: Pathology) => void
  onCancel: () => void
}

function SymptomList({
  label,
  items,
  onRemove,
}: {
  label: string
  items: Symptom[]
  onRemove: (symptom: Symptom) => void
}) {
  if (items.length === 0) return null
  return (
    <ul aria-label={label} className="mt-2 flex flex-wrap gap-2">
      {items.map((symptom) => (
        <li
          key={symptom.code}
          className="flex items-center gap-2 rounded-md border border-slate-300 bg-white px-2 py-1 text-sm"
        >
          {symptom.term}
          <button
            type="button"
            aria-label={`Quitar ${symptom.term}`}
            onClick={() => onRemove(symptom)}
            className="rounded px-1 text-slate-600 hover:bg-slate-100"
          >
            ×
          </button>
        </li>
      ))}
    </ul>
  )
}

export function PathologyForm({ pathology, onSaved, onCancel }: Props) {
  const editing = pathology !== undefined
  const [name, setName] = useState(pathology?.name ?? '')
  const [cardinal, setCardinal] = useState<Symptom | null>(pathology?.cardinal ?? null)
  const [secondary, setSecondary] = useState<Symptom[]>(pathology?.secondary ?? [])

  const create = useCreatePathology()
  const replace = useReplacePathologySymptoms(pathology?.id ?? 0)
  const saving = create.isPending || replace.isPending
  const error = create.error ?? replace.error

  const [announcement, setAnnouncement] = useState('')
  const cardinalRef = useRef<HTMLDivElement>(null)
  const secondaryRef = useRef<HTMLDivElement>(null)

  const chooseCardinal = (symptom: Symptom) => {
    setAnnouncement(`Se eligió ${symptom.term} como síntoma cardinal.`)
    setCardinal(symptom)
    // Un síntoma no puede ser cardinal y secundario a la vez
    setSecondary((current) => current.filter((item) => item.code !== symptom.code))
  }

  const missing: string[] = []
  if (!editing && name.trim().length === 0) missing.push('el nombre')
  if (cardinal === null) missing.push('el síntoma cardinal')
  if (secondary.length < MIN_SECONDARY_SYMPTOMS)
    missing.push(`al menos ${MIN_SECONDARY_SYMPTOMS} síntomas secundarios`)
  const complete = missing.length === 0

  // Al quitar un síntoma el botón desaparece: el foco pasa al bloque para no perderse
  const removeCardinal = () => {
    setAnnouncement(`Se quitó ${cardinal?.term}.`)
    setCardinal(null)
    cardinalRef.current?.focus()
  }
  const removeSecondary = (symptom: Symptom) => {
    setAnnouncement(`Se quitó ${symptom.term}.`)
    setSecondary((current) => current.filter((item) => item.code !== symptom.code))
    secondaryRef.current?.focus()
  }

  const save = () => {
    if (!cardinal) return
    const options = { onSuccess: onSaved }
    if (editing) replace.mutate({ cardinal, secondary }, options)
    else create.mutate({ name: name.trim(), cardinal, secondary }, options)
  }

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        save()
      }}
      className="space-y-4 rounded-lg border border-slate-300 bg-slate-50 p-4"
    >
      <h2 className="text-lg font-semibold text-slate-900">
        {editing ? `Editar síntomas de ${pathology.name}` : 'Nueva patología'}
      </h2>

      {!editing && (
        <TextField
          label="Nombre de la patología"
          value={name}
          maxLength={100}
          onChange={(event) => setName(event.target.value)}
        />
      )}

      <div ref={cardinalRef} tabIndex={-1} className="outline-none">
        <SymptomSearch
          label="Buscar síntoma cardinal"
          single
          selected={cardinal ? [cardinal] : []}
          onSelect={chooseCardinal}
        />
        <SymptomList
          label="Síntoma cardinal elegido"
          items={cardinal ? [cardinal] : []}
          onRemove={removeCardinal}
        />
      </div>

      <div ref={secondaryRef} tabIndex={-1} className="outline-none">
        <SymptomSearch
          label="Buscar síntomas secundarios"
          selected={cardinal ? [cardinal, ...secondary] : secondary}
          onSelect={(symptom) => {
            setAnnouncement(`Se agregó ${symptom.term} a los síntomas secundarios.`)
            setSecondary((current) => [...current, symptom])
          }}
        />
        <SymptomList
          label="Síntomas secundarios elegidos"
          items={secondary}
          onRemove={removeSecondary}
        />
        <p id="secondary-help" className="mt-1 text-xs text-slate-500">
          Cargá al menos {MIN_SECONDARY_SYMPTOMS} síntomas secundarios.
        </p>
      </div>

      <p role="status" className="sr-only">
        {announcement}
      </p>

      {!complete && (
        <p id="missing-help" className="text-sm text-slate-700">
          Para guardar falta: {missing.join(', ')}.
        </p>
      )}

      {error && (
        <Alert kind="error">
          {error instanceof ApiError ? error.message : 'No pudimos guardar. Revisá tu conexión.'}
        </Alert>
      )}

      <div className="flex gap-2">
        <Button
          type="submit"
          loading={saving}
          disabled={!complete}
          aria-describedby={complete ? undefined : 'missing-help'}
        >
          {editing ? 'Guardar cambios' : 'Guardar patología'}
        </Button>
        <Button variant="secondary" onClick={onCancel}>
          Cancelar
        </Button>
      </div>
    </form>
  )
}
