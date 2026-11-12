import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useDebouncedValue } from './useDebouncedValue'

describe('useDebouncedValue', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('empieza con el valor inicial', () => {
    const { result } = renderHook(() => useDebouncedValue('hip', 300))
    expect(result.current).toBe('hip')
  })

  it('espera a que el valor deje de cambiar', () => {
    const { result, rerender } = renderHook(({ value }) => useDebouncedValue(value, 300), {
      initialProps: { value: 'hip' },
    })

    rerender({ value: 'hipo' })
    act(() => vi.advanceTimersByTime(200))
    rerender({ value: 'hipot' })
    act(() => vi.advanceTimersByTime(200))
    expect(result.current).toBe('hip')

    act(() => vi.advanceTimersByTime(100))
    expect(result.current).toBe('hipot')
  })
})
