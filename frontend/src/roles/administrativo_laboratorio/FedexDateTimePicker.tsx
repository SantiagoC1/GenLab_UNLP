
import { useMemo, useState } from 'react'

type Props = {
  value: string
  onChange: (value: string) => void
  holidays: string[]
  disabled?: boolean
}

const WEEKDAYS = ['Lu', 'Ma', 'Mi', 'Ju', 'Vi']

const TIME_OPTIONS = Array.from({ length: 19 }, (_, index) => {
  const totalMinutes = 9 * 60 + index * 30
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60

  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`
})

function toDateKey(year: number, month: number, day: number): string {
  return [
    year,
    String(month + 1).padStart(2, '0'),
    String(day).padStart(2, '0'),
  ].join('-')
}

function todayKey(): string {
  const now = new Date()

  return toDateKey(
    now.getFullYear(),
    now.getMonth(),
    now.getDate(),
  )
}

function isPastTime(dateKey: string, time: string): boolean {
  if (!dateKey || !time) return false

  const selected = new Date(`${dateKey}T${time}:00`)

  return selected.getTime() <= Date.now()
}

export default function FedexDateTimePicker({
  value,
  onChange,
  holidays,
  disabled = false,
}: Props) {
  const [selectedDate = '', selectedTime = ''] = value.split('T')

  const [visibleMonth, setVisibleMonth] = useState(() => {
    const initial = selectedDate
      ? new Date(`${selectedDate}T12:00:00`)
      : new Date()

    return new Date(initial.getFullYear(), initial.getMonth(), 1)
  })

  const holidaySet = useMemo(() => new Set(holidays), [holidays])

  const year = visibleMonth.getFullYear()
  const month = visibleMonth.getMonth()

  const daysInMonth = new Date(year, month + 1, 0).getDate()

  const firstWeekday = (new Date(year, month, 1).getDay() + 6) % 7

  const weekdayOffset = Math.min(firstWeekday, 5)

  const cells: (number | null)[] = [
    ...Array.from({ length: weekdayOffset }, () => null),
    ...Array.from({ length: daysInMonth }, (_, index) => index + 1)
      .filter((day) => {
        const weekday = new Date(year, month, day).getDay()
        return weekday !== 0 && weekday !== 6
      }),
  ]

  while (cells.length % 5 !== 0) {
   cells.push(null)
  }

  function changeMonth(offset: number) {
    setVisibleMonth(new Date(year, month + offset, 1))
  }

  function selectDate(dateKey: string) {
    const validTime = TIME_OPTIONS.find(
      (time) => !isPastTime(dateKey, time),
    )

    if (!validTime) return

    const nextTime =
      selectedTime &&
      TIME_OPTIONS.includes(selectedTime) &&
      !isPastTime(dateKey, selectedTime)
        ? selectedTime
        : validTime

    onChange(`${dateKey}T${nextTime}`)
  }

  const monthLabel = visibleMonth.toLocaleDateString('es-AR', {
    month: 'long',
    year: 'numeric',
  })

  const previousMonth = new Date(year, month - 1, 1)
  const currentMonth = new Date()
  const canGoPrevious =
    previousMonth.getFullYear() > currentMonth.getFullYear() ||
    (
      previousMonth.getFullYear() === currentMonth.getFullYear() &&
      previousMonth.getMonth() >= currentMonth.getMonth()
    )

  return (
    <div className="space-y-4">
      <div className="max-w-sm rounded-xl border border-gray-200 bg-white p-4">
        <div className="mb-4 flex items-center justify-between">
          <button
            type="button"
            aria-label="Mes anterior"
            disabled={disabled || !canGoPrevious}
            onClick={() => changeMonth(-1)}
            className="rounded-lg border px-3 py-1 disabled:opacity-30"
          >
            ‹
          </button>

          <h3 className="font-semibold capitalize">{monthLabel}</h3>

          <button
            type="button"
            aria-label="Mes siguiente"
            disabled={disabled}
            onClick={() => changeMonth(1)}
            className="rounded-lg border px-3 py-1 disabled:opacity-30"
          >
            ›
          </button>
        </div>

        <div className="grid grid-cols-5 gap-1 text-center">
          {WEEKDAYS.map((weekday) => (
            <div
              key={weekday}
              className="py-2 text-xs font-semibold text-gray-500"
            >
              {weekday}
            </div>
          ))}

          {cells.map((day, index) => {
            if (day === null) {
              return <div key={`empty-${index}`} />
            }

            const dateKey = toDateKey(year, month, day)
            const isHoliday = holidaySet.has(dateKey)
            const isPast = dateKey < todayKey()
            const hasAvailableTime = TIME_OPTIONS.some(
              (time) => !isPastTime(dateKey, time),
            )

            const isUnavailable =
                isHoliday ||
                isPast ||
                !hasAvailableTime

            const isSelected = selectedDate === dateKey

            const tooltip = isHoliday
                ? 'Feriado'
                : isPast || !hasAvailableTime
                    ? 'Fecha no disponible'
                    : undefined

            return (
              <div
                key={dateKey}
                title={tooltip}
                className="relative"
              >
                <button
                  type="button"
                  disabled={disabled || isUnavailable}
                  aria-label={`${day} de ${monthLabel}${tooltip ? ` - ${tooltip}` : ''}`}
                  aria-pressed={isSelected}
                  onClick={() => selectDate(dateKey)}
                  className={[
                    'h-10 w-full rounded-lg text-sm transition-colors',
                    isSelected
                      ? 'bg-blue-600 font-semibold text-white'
                      : isUnavailable
                        ? 'cursor-not-allowed bg-gray-100 text-gray-400'
                        : 'hover:bg-blue-100',
                    isHoliday ? 'line-through' : '',
                  ].join(' ')}
                >
                  {day}
                </button>
              </div>
            )
          })}
        </div>

        <div className="mt-4 flex flex-wrap gap-3 text-xs text-gray-500">
          <span>Gris: no disponible</span>
          <span className="line-through">Tachado: feriado</span>
        </div>
      </div>

      <div className="max-w-sm">
        <label
          htmlFor="fedex-pickup-time"
          className="mb-2 block text-sm font-medium"
        >
          Horario de retiro
        </label>

        <select
          id="fedex-pickup-time"
          value={selectedTime}
          disabled={disabled || !selectedDate}
          onChange={(event) =>
            onChange(`${selectedDate}T${event.target.value}`)
          }
          className="w-full rounded-lg border border-gray-300 bg-white p-3 disabled:bg-gray-100"
        >
          <option value="">Seleccioná un horario</option>

          {TIME_OPTIONS.map((time) => (
            <option
              key={time}
              value={time}
              disabled={isPastTime(selectedDate, time)}
            >
              {time}
            </option>
          ))}
        </select>

        <p className="mt-2 text-xs text-gray-500">
          Horarios disponibles: de 9:00 a 18:00, cada 30 minutos.
        </p>
      </div>
    </div>
  )
}
