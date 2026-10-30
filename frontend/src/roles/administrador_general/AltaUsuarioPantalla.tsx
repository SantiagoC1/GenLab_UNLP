import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Alert } from '../../components/Alert'
import { Button } from '../../components/Button'
import { PersonFields } from '../../components/PersonFields'
import { createUser, getCatalogs, listUsers, unblockUser } from '../../lib/access'
import {
  EMPTY_PERSON,
  toPayload,
  validatePerson,
  type Errors,
  type PersonData,
} from '../../lib/validation'
import { ETIQUETA_ROL, type Rol } from '../roles'

// M1-RF4: cualquier rol menos el paciente (lo da de alta el médico tratante, escenario 9).
const CREATABLE_ROLES: readonly Rol[] = [
  'medico_tratante',
  'administrativo_laboratorio',
  'bioinformatico',
  'transportista',
  'gerente_medico',
]

/** Scenario 2 · M1-RF4 to RF6. */
export default function AltaUsuarioPantalla() {
  const queryClient = useQueryClient()
  const [formOpen, setFormOpen] = useState(false)
  const [person, setPerson] = useState<PersonData>(EMPTY_PERSON)
  const [errors, setErrors] = useState<Errors>({})
  const [notice, setNotice] = useState('')

  const users = useQuery({ queryKey: ['users'], queryFn: listUsers })
  const catalogs = useQuery({ queryKey: ['catalogs'], queryFn: getCatalogs })
  const create = useMutation({
    mutationFn: () => createUser(toPayload(person)),
    onSuccess: (user) => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setNotice(`Alta guardada. Enviamos las credenciales de acceso a ${user.email}.`)
      setPerson(EMPTY_PERSON)
      setFormOpen(false)
    },
  })

  const unblock = useMutation({
    mutationFn: (id: string) => unblockUser(id),
    onSuccess: (user) => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setNotice(`Desbloqueamos la cuenta de ${user.email}.`)
    },
  })

  const change = <K extends keyof PersonData>(field: K, value: PersonData[K]) =>
    setPerson((current) => ({ ...current, [field]: value }))

  const submit = (event: FormEvent) => {
    event.preventDefault()
    setNotice('')
    const found = validatePerson(person)
    setErrors(found)
    if (Object.keys(found).length === 0) create.mutate()
  }

  return (
    <section>
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">Dar de alta a un usuario</h1>
      <p className="mt-1 text-sm text-slate-500">Escenario 2 · M1-RF4 a RF6</p>

      <div className="mt-6 space-y-4">
        {notice && <Alert kind="success">{notice}</Alert>}
        {unblock.error && <Alert kind="error">{unblock.error.message}</Alert>}

        {formOpen ? (
          <form onSubmit={submit} noValidate className="max-w-md space-y-4">
            {create.error && <Alert kind="error">{create.error.message}</Alert>}
            <PersonFields
              values={person}
              errors={errors}
              roles={CREATABLE_ROLES}
              catalogs={catalogs.data}
              onChange={change}
            />
            <div className="flex gap-2">
              <Button type="submit" loading={create.isPending}>
                Guardar el alta
              </Button>
              <Button
                variant="secondary"
                onClick={() => {
                  create.reset()
                  setFormOpen(false)
                }}
              >
                Cancelar
              </Button>
            </div>
          </form>
        ) : (
          <Button
            onClick={() => {
              setNotice('')
              setFormOpen(true)
            }}
          >
            Nuevo usuario
          </Button>
        )}

        <h2 className="pt-2 text-lg font-semibold text-slate-900">Usuarios</h2>
        {users.isPending && <p className="text-sm text-slate-500">Cargando…</p>}
        {users.isError && <Alert kind="error">{users.error.message}</Alert>}
        {users.data && (
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-100 text-slate-700">
                <tr>
                  <th className="px-3 py-2 font-medium">Nombre</th>
                  <th className="px-3 py-2 font-medium">Mail</th>
                  <th className="px-3 py-2 font-medium">Rol</th>
                  <th className="px-3 py-2 font-medium">Provincia</th>
                  <th className="px-3 py-2 font-medium">Estado</th>
                  <th className="px-3 py-2 font-medium">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {users.data.map((u) => (
                  <tr key={u.id} className="border-t border-slate-200">
                    <td className="px-3 py-2">
                      {u.last_name}, {u.first_name}
                    </td>
                    <td className="px-3 py-2">{u.email}</td>
                    <td className="px-3 py-2">{ETIQUETA_ROL[u.role]}</td>
                    <td className="px-3 py-2">{u.province ?? '—'}</td>
                    <td className="px-3 py-2">{u.blocked ? 'Bloqueado' : 'Activo'}</td>
                    <td className="px-3 py-2">
                      {u.blocked && (
                        <Button
                          variant="secondary"
                          loading={unblock.isPending && unblock.variables === u.id}
                          onClick={() => {
                            setNotice('')
                            unblock.mutate(u.id)
                          }}
                        >
                          Desbloquear
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  )
}
