import { useQuery } from '@tanstack/react-query'
import { useRef, useState } from 'react'
import { ApiError } from '../lib/api'
import { MIN_SEARCH_LENGTH, searchSymptoms, type Symptom } from '../lib/symptoms'
import { useDebouncedValue } from '../lib/useDebouncedValue'
import { Alert } from './Alert'
import { Button } from './Button'
import { TextField } from './TextField'

interface Props {
  /** Los síntomas que la pantalla ya cargó: no se vuelven a ofrecer. */
  selected: Symptom[]
  onSelect: (symptom: Symptom) => void
  label?: string
  /** Para el síntoma cardinal (un solo síntoma): con uno elegido, el buscador se deshabilita. */
  single?: boolean
  debounceMs?: number
}

/**
 * Escenario 7: buscador de síntomas con SNOMED, sin texto libre. REUTILIZABLE: lo usan las
 * pantallas de patologías (M2) y de pacientes y familiares (M3). La selección vive en la
 * pantalla que lo usa, así un error del buscador no hace perder lo que ya se cargó.
 */
export function SymptomSearch({
  selected,
  onSelect,
  label = 'Buscar síntoma',
  single = false,
  debounceMs = 300,
}: Props) {
  const [text, setText] = useState('')
  const [page, setPage] = useState(1)
  const container = useRef<HTMLDivElement>(null)

  const trimmed = text.trim()
  const debounced = useDebouncedValue(trimmed, debounceMs)
  const active = trimmed.length >= MIN_SEARCH_LENGTH && debounced.length >= MIN_SEARCH_LENGTH
  const locked = single && selected.length > 0

  const search = useQuery({
    queryKey: ['symptoms', debounced, page],
    queryFn: ({ signal }) => searchSymptoms(debounced, page, signal),
    enabled: active,
  })

  const change = (value: string) => {
    setText(value)
    setPage(1)
  }

  const choose = (symptom: Symptom) => {
    onSelect(symptom)
    change('')
    container.current?.querySelector('input')?.focus()
  }

  // Mientras el texto espera el debounce, la consulta anterior sigue en caché: no se muestra.
  const data = active ? search.data : undefined
  const failed = active && search.isError
  const offered = data?.items.filter((item) => !selected.some((s) => s.code === item.code))

  return (
    <div ref={container}>
      <TextField
        label={label}
        type="search"
        autoComplete="off"
        value={text}
        disabled={locked}
        hint={
          locked
            ? 'Quitá el síntoma elegido para buscar otro.'
            : `Escribí al menos ${MIN_SEARCH_LENGTH} letras y elegí un término de la lista.`
        }
        onChange={(event) => change(event.target.value)}
        // El texto escrito nunca se agrega solo: solo se puede elegir un resultado de SNOMED.
        onKeyDown={(event) => event.key === 'Enter' && event.preventDefault()}
      />

      <div className="mt-2 space-y-2" aria-live="polite">
        {active && search.isFetching && !data && <Alert>Buscando…</Alert>}

        {failed && (
          <Alert kind="error">
            {search.error instanceof ApiError
              ? search.error.message
              : 'No pudimos buscar síntomas. Revisá tu conexión.'}{' '}
            <Button variant="secondary" onClick={() => search.refetch()}>
              Reintentar
            </Button>
          </Alert>
        )}

        {offered && offered.length > 0 && (
          <ul
            aria-label="Resultados de la búsqueda"
            className="divide-y divide-slate-200 rounded-md border border-slate-300 bg-white"
          >
            {offered.map((item) => (
              <li key={item.code}>
                <button
                  type="button"
                  onClick={() => choose(item)}
                  className="block w-full px-3 py-2 text-left text-sm text-slate-900 hover:bg-slate-100"
                >
                  {item.term}
                </button>
              </li>
            ))}
          </ul>
        )}

        {data && offered?.length === 0 && (
          <Alert>
            {data.items.length > 0
              ? 'Ya elegiste todos los síntomas de esta página.'
              : page > 1
                ? 'No hay más resultados.'
                : `No hay resultados para «${debounced}». Solo se pueden cargar síntomas de SNOMED.`}
          </Alert>
        )}

        {data && (page > 1 || data.has_more) && (
          <div className="flex gap-2">
            <Button variant="secondary" disabled={page === 1} onClick={() => setPage(page - 1)}>
              Anterior
            </Button>
            <Button variant="secondary" disabled={!data.has_more} onClick={() => setPage(page + 1)}>
              Siguiente
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
