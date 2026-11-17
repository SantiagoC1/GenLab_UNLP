import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Alert } from '../../components/Alert'
import { Button } from '../../components/Button'
import { SelectField } from '../../components/SelectField'
import { api, json } from '../../lib/api'
import type { Cupon } from '../../lib/cupones'

interface Paciente {
  contacto: string
  nombre: string
}

interface MisCupones {
  cantidad: number
  cupones: Cupon[]
}

interface Asignacion {
  paciente: Paciente
  cupon: Cupon
  disponibles: number
  paciente_avisado: boolean
}

const MIS_CUPONES_KEY = ['cupones', 'mis-cupones']

export default function AsignarCuponPantalla() {
  const queryClient = useQueryClient()
  const [contacto, setContacto] = useState('')
  const [codigo, setCodigo] = useState('')

  const misCupones = useQuery({
    queryKey: MIS_CUPONES_KEY,
    queryFn: () => api<MisCupones>('/cupones/mis-cupones'),
  })
  const pacientes = useQuery({
    queryKey: ['cupones', 'mis-pacientes'],
    queryFn: () => api<Paciente[]>('/cupones/mis-pacientes'),
  })

  const asignar = useMutation({
    mutationFn: () =>
      api<Asignacion>('/cupones/asignar-a-paciente', {
        method: 'POST',
        ...json({ contacto_paciente: contacto, codigo }),
      }),
    onSuccess: () => {
      setCodigo('')
      return queryClient.invalidateQueries({ queryKey: MIS_CUPONES_KEY })
    },
  })

  const disponibles = misCupones.data?.cupones ?? []
  // M5-RF4: without coupons the assignment is disabled.
  const sinCupones = misCupones.data !== undefined && misCupones.data.cantidad === 0

  return (
    <section>
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">
        Asignar un cupón de descuento al paciente
      </h1>
      <p className="mt-1 text-sm text-slate-500">Escenario 17 · M5-RF3, RF4</p>

      <div className="mt-4 space-y-3">
        {misCupones.isError && <Alert kind="error">{misCupones.error.message}</Alert>}
        {pacientes.isError && <Alert kind="error">{pacientes.error.message}</Alert>}
        {asignar.isError && <Alert kind="error">{asignar.error.message}</Alert>}
        {asignar.isSuccess && (
          <Alert kind="success">
            El cupón {asignar.data.cupon.codigo} ya figura en la vista de{' '}
            {asignar.data.paciente.nombre}. Te quedan {asignar.data.disponibles} cupones
            disponibles.
          </Alert>
        )}
      </div>

      <p className="mt-4 text-sm text-slate-700">
        Cupones disponibles: <strong>{misCupones.data?.cantidad ?? '…'}</strong>
      </p>
      {sinCupones && (
        <p className="mt-1 text-sm text-slate-500">
          No tenés cupones disponibles. El gerente médico te puede asignar más.
        </p>
      )}

      <form
        className="mt-6 max-w-md space-y-4"
        onSubmit={(event) => {
          event.preventDefault()
          if (contacto && codigo) asignar.mutate()
        }}
      >
        <SelectField
          label="Paciente"
          value={contacto}
          disabled={sinCupones}
          onChange={(e) => {
            asignar.reset()
            setContacto(e.target.value)
          }}
        >
          <option value="">Elegí un paciente</option>
          {pacientes.data?.map((p) => (
            <option key={p.contacto} value={p.contacto}>
              {p.nombre}
            </option>
          ))}
        </SelectField>
        <SelectField
          label="Cupón"
          value={codigo}
          disabled={sinCupones}
          onChange={(e) => {
            asignar.reset()
            setCodigo(e.target.value)
          }}
        >
          <option value="">Elegí un cupón</option>
          {disponibles.map((c) => (
            <option key={c.codigo} value={c.codigo}>
              {c.codigo} · {c.descuento}%
            </option>
          ))}
        </SelectField>
        <Button
          type="submit"
          loading={asignar.isPending}
          disabled={sinCupones || !contacto || !codigo}
        >
          Asignar el cupón
        </Button>
      </form>
    </section>
  )
}
