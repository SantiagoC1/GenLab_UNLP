
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../lib/api'
import {
  isMockRole,
  MOCK_ACTORS,
  useMockActor,
  type MockRole,
} from '../../lib/mockIdentity'
import { useRol } from '../rol-context'

type Notice = {
  id: string
  study_id: number
  title: string
  message: string
  created_at: string
  destination: string | null
  pending: boolean
  simulated: boolean
}

function MockNotices({ role }: { role: MockRole }) {
  const navigate = useNavigate()
  const [actorId, setActorId] = useMockActor(role)
  const [notices, setNotices] = useState<Notice[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true

    async function loadNotices() {
      setLoading(true)
      setError('')
      setNotices([])

      try {
        const params = new URLSearchParams({
          role,
          actor_id: actorId,
        })

        const data = await api<Notice[]>(
          `/notifications?${params.toString()}`,
        )

        if (active) setNotices(data)
      } catch (caught) {
        if (active) {
          setError(
            caught instanceof Error
              ? caught.message
              : 'No se pudieron cargar los avisos.',
          )
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    void loadNotices()

    return () => {
      active = false
    }
  }, [role, actorId])

  function openNotice(notice: Notice) {
    if (!notice.destination) return

    const params = new URLSearchParams({
      study_id: String(notice.study_id),
    })

    navigate(`${notice.destination}?${params.toString()}`)
  }

  const pendingCount = notices.filter((notice) => notice.pending).length

  return (
    <>
      <div className="max-w-md rounded-xl border bg-white p-4">
        <label
          htmlFor="notification-actor"
          className="block text-sm font-medium"
        >
          Usuario de prueba
        </label>

        <select
          id="notification-actor"
          value={actorId}
          onChange={(event) => setActorId(event.target.value)}
          className="mt-2 w-full rounded-lg border p-3"
        >
          {MOCK_ACTORS[role].map((actor) => (
            <option key={actor.id} value={actor.id}>
              {actor.name}
            </option>
          ))}
        </select>

        <p className="mt-2 text-xs text-slate-500">
          Identidad ficticia compartida con las demás pantallas del simulador.
        </p>
      </div>

      {error && (
        <p
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 p-3 text-red-800"
        >
          {error}
        </p>
      )}

      <div className="rounded-xl border bg-white p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold">Avisos pendientes</h2>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-sm">
            {loading ? 'Cargando...' : `${pendingCount} pendiente(s)`}
          </span>
        </div>

        {loading && <p>Cargando avisos...</p>}

        {!loading && !error && notices.length === 0 && (
          <p className="text-sm text-slate-600">
            No tenés avisos pendientes.
          </p>
        )}

        <div className="space-y-3">
          {notices.map((notice) => (
            <article
              key={notice.id}
              className="rounded-lg border border-slate-200 p-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold">{notice.title}</h3>
                  <p className="mt-1 text-sm text-slate-600">
                    {notice.message}
                  </p>
                  <p className="mt-2 text-xs text-slate-500">
                    {new Date(notice.created_at).toLocaleString('es-AR')}
                  </p>
                </div>

                {notice.destination && (
                  <button
                    type="button"
                    onClick={() => openNotice(notice)}
                    className="rounded-lg bg-teal-700 px-4 py-2 text-sm text-white hover:bg-teal-800"
                  >
                    Abrir estudio #{notice.study_id}
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      </div>
    </>
  )
}

export default function AvisosPantalla() {
  const { rol } = useRol()

  return (
    <section className="space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-semibold">Mis avisos</h1>
        <p className="mt-2 text-sm text-slate-600">
          Consultá las novedades relacionadas con tus estudios.
        </p>
      </header>

      {isMockRole(rol) ? (
        <MockNotices role={rol} />
      ) : (
        <p className="rounded-lg border bg-white p-4 text-sm text-slate-600">
          No hay avisos simulados configurados para este rol.
        </p>
      )}

      <p className="text-xs text-slate-500">
        Avisos ficticios para desarrollo. La lectura y eliminación de avisos
        siguen pendientes de definición.
      </p>
    </section>
  )
}
