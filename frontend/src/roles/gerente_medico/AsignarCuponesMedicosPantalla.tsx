import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Alert } from '../../components/Alert'
import { Button } from '../../components/Button'
import { TextField } from '../../components/TextField'
import { api, json } from '../../lib/api'
import { CUPONES_KEY, type Cupon } from '../../lib/cupones'

interface Medico {
  contacto: string
  nombre: string
  matricula: string
}

interface Asignacion {
  medico: Medico
  codigos: string[]
  medico_avisado: boolean
}

export default function AsignarCuponesMedicosPantalla() {
  const queryClient = useQueryClient()
  const [texto, setTexto] = useState('')
  const [buscado, setBuscado] = useState('')
  const [medico, setMedico] = useState<Medico | null>(null)
  const [elegidos, setElegidos] = useState<string[]>([])

  const medicos = useQuery({
    queryKey: ['cupones', 'medicos', buscado],
    queryFn: () => api<Medico[]>(`/cupones/medicos?q=${encodeURIComponent(buscado)}`),
    enabled: buscado !== '',
  })
  const cupones = useQuery({
    queryKey: CUPONES_KEY,
    queryFn: () => api<Cupon[]>('/cupones'),
  })

  const asignar = useMutation({
    mutationFn: (datos: { contacto_medico: string; codigos: string[] }) =>
      api<Asignacion>('/cupones/asignar-a-medico', { method: 'POST', ...json(datos) }),
    onSuccess: () => {
      setElegidos([])
      return queryClient.invalidateQueries({ queryKey: CUPONES_KEY })
    },
  })

  // Only Vigente coupons that nobody holds yet can be handed out.
  const sinAsignar = (cupones.data ?? []).filter(
    (c) => c.estado === 'Vigente' && !c.medico && !c.paciente,
  )

  function alternar(codigo: string) {
    asignar.reset()
    setElegidos((actuales) =>
      actuales.includes(codigo) ? actuales.filter((c) => c !== codigo) : [...actuales, codigo],
    )
  }

  return (
    <section>
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">
        Asignar cupones al médico tratante
      </h1>
      <p className="mt-1 text-sm text-slate-500">Escenario 16 · M5-RF2</p>

      <form
        className="mt-6 flex max-w-xl items-end gap-3"
        onSubmit={(event) => {
          event.preventDefault()
          setMedico(null)
          setBuscado(texto.trim())
        }}
      >
        <div className="flex-1">
          <TextField
            label="Buscar médico por nombre o matrícula"
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
          />
        </div>
        <Button type="submit" variant="secondary" disabled={texto.trim() === ''}>
          Buscar
        </Button>
      </form>

      {medicos.isError && <Alert kind="error">{medicos.error.message}</Alert>}
      {medicos.data?.length === 0 && (
        <p className="mt-3 text-sm text-slate-500">No se encontró ningún médico.</p>
      )}
      <ul className="mt-3 max-w-xl divide-y divide-slate-200 rounded-lg border border-slate-200 empty:hidden">
        {medicos.data?.map((m) => (
          <li key={m.contacto}>
            <button
              type="button"
              aria-pressed={medico?.contacto === m.contacto}
              onClick={() => {
                asignar.reset()
                setMedico(m)
              }}
              className="flex w-full justify-between p-3 text-left text-sm hover:bg-slate-50 aria-pressed:bg-slate-100"
            >
              <span>{m.nombre}</span>
              <span className="text-slate-500">{m.matricula}</span>
            </button>
          </li>
        ))}
      </ul>

      {medico && (
        <div className="mt-6">
          <h2 className="font-medium text-slate-900">Cupones Vigentes para {medico.nombre}</h2>
          {cupones.isError && <Alert kind="error">{cupones.error.message}</Alert>}
          {sinAsignar.length === 0 && (
            <p className="mt-2 text-sm text-slate-500">No hay cupones Vigentes sin asignar.</p>
          )}
          <ul className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {sinAsignar.map((c) => (
              <li key={c.codigo}>
                <label className="flex items-center gap-2 rounded-lg border border-slate-200 p-3 text-sm">
                  <input
                    type="checkbox"
                    checked={elegidos.includes(c.codigo)}
                    onChange={() => alternar(c.codigo)}
                  />
                  <span>
                    {c.codigo} · {c.descuento}%
                  </span>
                </label>
              </li>
            ))}
          </ul>
          <div className="mt-4 space-y-3">
            {asignar.isError && <Alert kind="error">{asignar.error.message}</Alert>}
            {asignar.isSuccess && (
              <Alert kind="success">
                Se asignaron {asignar.data.codigos.length} cupones a {asignar.data.medico.nombre}.
                {asignar.data.medico_avisado
                  ? ' El médico recibió un aviso.'
                  : ' No se pudo avisar al médico.'}
              </Alert>
            )}
            <Button
              loading={asignar.isPending}
              disabled={elegidos.length === 0}
              onClick={() =>
                asignar.mutate({ contacto_medico: medico.contacto, codigos: elegidos })
              }
            >
              Asignar {elegidos.length > 0 ? elegidos.length : ''} cupones
            </Button>
          </div>
        </div>
      )}
    </section>
  )
}
