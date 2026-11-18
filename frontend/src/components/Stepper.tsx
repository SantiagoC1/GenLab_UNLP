interface Props {
  steps: string[]
  /** Zero-based index of the current step. */
  current: number
}

export function Stepper({ steps, current }: Props) {
  return (
    <nav aria-label="Pasos del estudio" className="mb-6">
      <ol className="flex items-start gap-1 sm:gap-2">
        {steps.map((step, index) => {
          const state = index < current ? 'done' : index === current ? 'current' : 'todo'
          return (
            <li
              key={step}
              aria-current={state === 'current' ? 'step' : undefined}
              className="flex min-w-0 flex-1 flex-col items-center gap-1 text-center"
            >
              <span
                className={`flex size-7 items-center justify-center rounded-full border text-xs font-semibold ${
                  state === 'todo'
                    ? 'border-line bg-surface text-muted'
                    : 'border-brand bg-brand text-white'
                }`}
              >
                {state === 'done' ? '✓' : index + 1}
              </span>
              <span
                className={`text-xs leading-tight ${state === 'current' ? 'font-semibold text-ink' : 'text-muted'}`}
              >
                {step}
              </span>
              <span className="sr-only">
                {state === 'done' ? '(completado)' : state === 'current' ? '(paso actual)' : ''}
              </span>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
