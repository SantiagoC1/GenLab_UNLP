import { useId } from 'react'
import { MAX_AGE, MAX_NAME_LENGTH, type Kinship, type RelativeForm } from '../lib/familiograma'
import type { Pathology } from '../lib/pathologies'
import { SEX_LABELS, type Sex } from '../lib/patients'
import type { Errors } from '../lib/validation'
import { Button } from './Button'
import { FIELD_CLASS, TextField } from './TextField'
import { SymptomSearch } from './SymptomSearch'

interface Props {
  number: number
  form: RelativeForm
  kinships: Kinship[]
  pathologies: Pathology[]
  errors: Errors
  onChange: (patch: Partial<RelativeForm>) => void
  onRemove: () => void
}

/**
 * Los datos de un familiar: parentesco, nombre, sexo, edad, síntomas y diagnósticos. Es un
 * `fieldset` con el número del familiar como leyenda, para que un lector de pantalla sepa a cuál
 * pertenece cada campo.
 */
export function RelativeFields({
  number,
  form,
  kinships,
  pathologies,
  errors,
  onChange,
  onRemove,
}: Props) {
  const kinshipId = useId()
  const kinshipErrorId = `${kinshipId}-error`
  const sexErrorId = useId()

  /** Agrega o quita un diagnóstico de la lista del familiar. */
  const togglePathology = (id: number) =>
    onChange({
      pathologyIds: form.pathologyIds.includes(id)
        ? form.pathologyIds.filter((item) => item !== id)
        : [...form.pathologyIds, id],
    })

  return (
    <fieldset className="space-y-4 rounded-control border border-line bg-surface p-4">
      <legend className="px-1 text-sm font-semibold text-ink">Familiar {number}</legend>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor={kinshipId} className="block text-sm font-medium text-ink">
            Parentesco
          </label>
          <select
            id={kinshipId}
            className={FIELD_CLASS}
            value={form.kinshipId}
            aria-invalid={errors.kinshipId ? true : undefined}
            aria-describedby={errors.kinshipId ? kinshipErrorId : undefined}
            onChange={(event) => onChange({ kinshipId: event.target.value })}
          >
            <option value="">Elegí un parentesco</option>
            {kinships.map((kinship) => (
              <option key={kinship.id} value={kinship.id}>
                {kinship.name}
              </option>
            ))}
          </select>
          {errors.kinshipId && (
            <p id={kinshipErrorId} className="mt-1 text-sm text-danger">
              {errors.kinshipId}
            </p>
          )}
        </div>
        <TextField
          label="Edad (años)"
          type="number"
          min={0}
          max={MAX_AGE}
          step="any"
          value={form.age}
          error={errors.age}
          hint="Si no se conoce, dejala vacía."
          onChange={(event) => onChange({ age: event.target.value })}
        />
        <TextField
          label="Nombre"
          maxLength={MAX_NAME_LENGTH}
          value={form.firstName}
          error={errors.firstName}
          onChange={(event) => onChange({ firstName: event.target.value })}
        />
        <TextField
          label="Apellido"
          maxLength={MAX_NAME_LENGTH}
          value={form.lastName}
          error={errors.lastName}
          onChange={(event) => onChange({ lastName: event.target.value })}
        />
      </div>

      <fieldset aria-describedby={errors.sex ? sexErrorId : undefined}>
        <legend className="text-sm font-medium text-ink">Sexo</legend>
        <div className="mt-1 flex flex-wrap gap-4">
          {(Object.keys(SEX_LABELS) as Sex[]).map((sex) => (
            <label key={sex} className="flex items-center gap-2 text-sm text-ink">
              <input
                type="radio"
                name={`sex-${form.key}`}
                value={sex}
                checked={form.sex === sex}
                onChange={() => onChange({ sex })}
              />
              {SEX_LABELS[sex]}
            </label>
          ))}
        </div>
        {errors.sex && (
          <p id={sexErrorId} className="mt-1 text-sm text-danger">
            {errors.sex}
          </p>
        )}
      </fieldset>

      <label className="flex items-center gap-2 text-sm text-ink">
        <input
          type="checkbox"
          checked={form.deceased}
          onChange={(event) => onChange({ deceased: event.target.checked })}
        />
        Fallecido/a
      </label>

      <fieldset>
        <legend className="text-sm font-medium text-ink">
          Diagnóstico (patologías lisosomales)
        </legend>
        <div className="mt-1 flex flex-wrap gap-4">
          {pathologies.map((pathology) => (
            <label key={pathology.id} className="flex items-center gap-2 text-sm text-ink">
              <input
                type="checkbox"
                checked={form.pathologyIds.includes(pathology.id)}
                onChange={() => togglePathology(pathology.id)}
              />
              {pathology.name}
            </label>
          ))}
        </div>
      </fieldset>

      <div>
        <SymptomSearch
          label={`Buscar síntomas del familiar ${number}`}
          selected={form.symptoms}
          onSelect={(symptom) => onChange({ symptoms: [...form.symptoms, symptom] })}
        />
        {form.symptoms.length > 0 && (
          <ul aria-label={`Síntomas del familiar ${number}`} className="mt-2 flex flex-wrap gap-2">
            {form.symptoms.map((symptom) => (
              <li
                key={symptom.code}
                className="flex items-center gap-2 rounded-control border border-line bg-surface px-2 py-1 text-sm text-ink"
              >
                {symptom.term}
                <button
                  type="button"
                  aria-label={`Quitar ${symptom.term} del familiar ${number}`}
                  onClick={() =>
                    onChange({
                      symptoms: form.symptoms.filter((item) => item.code !== symptom.code),
                    })
                  }
                  className="rounded px-1 text-muted hover:bg-page"
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <Button variant="secondary" onClick={onRemove}>
        Quitar al familiar {number}
      </Button>
    </fieldset>
  )
}
