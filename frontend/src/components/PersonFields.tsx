import { ETIQUETA_ROL, type Rol } from '../roles/roles'
import type { Catalogs } from '../lib/access'
import type { Errors, PersonData } from '../lib/validation'
import { SelectField } from './SelectField'
import { TextField } from './TextField'

interface Props {
  values: PersonData
  errors: Errors
  roles: readonly Rol[]
  catalogs?: Catalogs
  onChange: <K extends keyof PersonData>(field: K, value: PersonData[K]) => void
}

/** Fields shared by sign-up (scenario 1) and creation by the admin (scenario 2). */
export function PersonFields({ values, errors, roles, catalogs, onChange }: Props) {
  const toggleSpecialty = (id: number) =>
    onChange(
      'specialties',
      values.specialties.includes(id)
        ? values.specialties.filter((s) => s !== id)
        : [...values.specialties, id],
    )

  return (
    <>
      <SelectField
        label="Rol"
        value={values.rol}
        error={errors.rol}
        onChange={(e) => onChange('rol', e.target.value as Rol | '')}
      >
        <option value="">Elegí un rol</option>
        {roles.map((r) => (
          <option key={r} value={r}>
            {ETIQUETA_ROL[r]}
          </option>
        ))}
      </SelectField>
      <TextField
        label="Nombre"
        autoComplete="given-name"
        value={values.firstName}
        error={errors.firstName}
        onChange={(e) => onChange('firstName', e.target.value)}
      />
      <TextField
        label="Apellido"
        autoComplete="family-name"
        value={values.lastName}
        error={errors.lastName}
        onChange={(e) => onChange('lastName', e.target.value)}
      />
      <TextField
        label="Teléfono de contacto"
        type="tel"
        autoComplete="tel"
        value={values.phone}
        error={errors.phone}
        onChange={(e) => onChange('phone', e.target.value)}
      />
      <TextField
        label="Mail"
        type="email"
        autoComplete="email"
        value={values.email}
        error={errors.email}
        onChange={(e) => onChange('email', e.target.value)}
      />

      {values.rol === 'medico_tratante' && (
        <>
          <TextField
            label="Matrícula"
            value={values.licenseNumber}
            error={errors.licenseNumber}
            onChange={(e) => onChange('licenseNumber', e.target.value)}
          />
          <fieldset>
            <legend className="text-sm font-medium text-slate-800">Especialidades</legend>
            <div className="mt-1 grid gap-1 sm:grid-cols-2">
              {catalogs?.specialties.map((s) => (
                <label key={s.id} className="flex items-center gap-2 text-sm text-slate-800">
                  <input
                    type="checkbox"
                    checked={values.specialties.includes(s.id)}
                    onChange={() => toggleSpecialty(s.id)}
                  />
                  {s.name}
                </label>
              ))}
            </div>
            {errors.specialties && (
              <p className="mt-1 text-xs text-red-700">{errors.specialties}</p>
            )}
          </fieldset>
        </>
      )}

      {values.rol === 'transportista' && (
        <SelectField
          label="Provincia que cubre"
          value={values.province}
          error={errors.province}
          onChange={(e) => onChange('province', e.target.value)}
        >
          <option value="">Elegí una provincia</option>
          {catalogs?.provinces.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </SelectField>
      )}
    </>
  )
}
