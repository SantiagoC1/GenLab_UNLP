import { useId, type InputHTMLAttributes } from 'react'

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  error?: string
  hint?: string
}

export const FIELD_CLASS =
  'mt-1 block min-h-11 w-full rounded-control border border-line bg-surface px-3 py-2 text-base text-ink transition-colors duration-150 placeholder:text-muted aria-[invalid=true]:border-danger'

export function TextField({ label, error, hint, ...input }: Props) {
  const id = useId()
  const messageId = `${id}-message`
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-ink">
        {label}
      </label>
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={error || hint ? messageId : undefined}
        className={FIELD_CLASS}
        {...input}
      />
      {(error || hint) && (
        <p id={messageId} className={`mt-1 text-sm ${error ? 'text-danger' : 'text-muted'}`}>
          {error ?? hint}
        </p>
      )}
    </div>
  )
}
