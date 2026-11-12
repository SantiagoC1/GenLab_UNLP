
import { useEffect, useState } from 'react'

export type MockRole = 'medico_tratante' | 'paciente' | 'bioinformatico'

export const MOCK_ACTORS: Record<MockRole, { id: string; name: string }[]> = {
  medico_tratante: [
    { id: 'doctor-1', name: 'Médico tratante de prueba 1' },
    { id: 'doctor-2', name: 'Médico tratante de prueba 2' },
  ],
  paciente: [
    { id: 'patient-1', name: 'Paciente de prueba 1' },
    { id: 'patient-2', name: 'Paciente de prueba 2' },
  ],
  bioinformatico: [
    { id: 'analyst-1', name: 'Bioinformático de prueba 1' },
    { id: 'analyst-2', name: 'Bioinformático de prueba 2' },
  ],
}

const STORAGE_PREFIX = 'genlab.mock-actor.'
const IDENTITY_EVENT = 'genlab:mock-identity-changed'

export function isMockRole(role: string): role is MockRole {
  return Object.prototype.hasOwnProperty.call(MOCK_ACTORS, role)
}

export function getMockActor(role: MockRole): string {
  const saved = sessionStorage.getItem(`${STORAGE_PREFIX}${role}`)
  const actors = MOCK_ACTORS[role]

  if (saved && actors.some((actor) => actor.id === saved)) {
    return saved
  }

  return actors[0].id
}

export function setMockActor(role: MockRole, actorId: string): void {
  if (!MOCK_ACTORS[role].some((actor) => actor.id === actorId)) {
    throw new Error('Invalid mock actor')
  }

  sessionStorage.setItem(`${STORAGE_PREFIX}${role}`, actorId)
  window.dispatchEvent(new Event(IDENTITY_EVENT))
}

export function useMockActor(role: MockRole): [string, (id: string) => void] {
  const [actorId, setActorId] = useState(() => getMockActor(role))

  useEffect(() => {
    const synchronize = () => setActorId(getMockActor(role))

    synchronize()
    window.addEventListener(IDENTITY_EVENT, synchronize)

    return () => window.removeEventListener(IDENTITY_EVENT, synchronize)
  }, [role])

  return [
    actorId,
    (id: string) => {
      setMockActor(role, id)
      setActorId(id)
    },
  ]
}
