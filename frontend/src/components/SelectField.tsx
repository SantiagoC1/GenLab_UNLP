import { useId, type SelectHTMLAttributes } from 'react'
import { FIELD_CLASS } from './TextField'

interface Props extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string
  error?: string
}

export function SelectField({ label, error, children, ...select }: Props) {
  const id = useId()
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-ink">
        {label}
      </label>
      <select
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-message` : undefined}
        className={FIELD_CLASS}
        {...select}
      >
        {children}
      </select>
      {error && (
        <p id={`${id}-message`} className="mt-1 text-sm text-danger">
          {error}
        </p>
      )}
    </div>
  )
}
