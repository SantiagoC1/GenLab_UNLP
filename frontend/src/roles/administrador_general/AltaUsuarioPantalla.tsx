import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useRef, useState, type FormEvent } from 'react'
import { Alert } from '../../components/Alert'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { PageContainer } from '../../components/PageContainer'
import { PageHeader } from '../../components/PageHeader'
import { LoadingBlock } from '../../components/Skeleton'
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

/** Roles que puede dar de alta el administrador: todos menos el paciente, que lo da de alta el médico. */
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
  const form = useRef<HTMLFormElement>(null)

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
    // Move focus to the first field with an error so keyboard and screen reader users land on it.
    else
      setTimeout(() => form.current?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus())
  }

  const columns = ['Nombre', 'Mail', 'Rol', 'Provincia', 'Estado', 'Acciones']

  return (
    <PageContainer wide>
      <PageHeader title="Dar de alta a un usuario" />

      <div className="space-y-4">
        {notice && <Alert kind="success">{notice}</Alert>}
        {unblock.error && <Alert kind="error">{unblock.error.message}</Alert>}

        {formOpen ? (
          <Card className="max-w-xl">
            <form ref={form} onSubmit={submit} noValidate className="space-y-4">
              {create.error && <Alert kind="error">{create.error.message}</Alert>}
              <PersonFields
                values={person}
                errors={errors}
                roles={CREATABLE_ROLES}
                catalogs={catalogs.data}
                onChange={change}
              />
              <div className="flex flex-col-reverse gap-2 sm:flex-row">
                <Button
                  variant="secondary"
                  className="w-full sm:w-auto"
                  onClick={() => {
                    create.reset()
                    setFormOpen(false)
                  }}
                >
                  Cancelar
                </Button>
                <Button type="submit" loading={create.isPending} className="w-full sm:w-auto">
                  Guardar el alta
                </Button>
              </div>
            </form>
          </Card>
        ) : (
          <Button
            className="w-full sm:w-auto"
            onClick={() => {
              setNotice('')
              setFormOpen(true)
            }}
          >
            Nuevo usuario
          </Button>
        )}

        <h2 className="pt-2 text-subtitle font-semibold text-ink">Usuarios</h2>
        {users.isPending && <LoadingBlock />}
        {users.isError && <Alert kind="error">{users.error.message}</Alert>}
        {users.data && (
          // Below 768px each row becomes a stacked card (label and value); the roles keep the
          // table semantics for screen readers.
          <div
            role="table"
            aria-label="Usuarios"
            className="lg:overflow-hidden lg:rounded-card lg:border lg:border-line-soft lg:bg-surface"
          >
            <div role="rowgroup" className="sr-only lg:not-sr-only">
              <div
                role="row"
                className="hidden bg-page text-sm text-ink-soft lg:grid lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1.8fr)_minmax(0,1.2fr)_minmax(0,1fr)_minmax(0,0.8fr)_minmax(0,1fr)]"
              >
                {columns.map((c) => (
                  <div key={c} role="columnheader" className="px-3 py-2 font-medium">
                    {c}
                  </div>
                ))}
              </div>
            </div>
            <div role="rowgroup">
              {users.data.map((u) => {
                const cells = [
                  `${u.last_name}, ${u.first_name}`,
                  u.email,
                  ETIQUETA_ROL[u.role],
                  u.province ?? '—',
                  u.blocked ? 'Bloqueado' : 'Activo',
                ]
                return (
                  <div
                    key={u.id}
                    role="row"
                    className="mb-3 rounded-card border border-line-soft bg-surface p-3 text-sm shadow-card lg:mb-0 lg:grid lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1.8fr)_minmax(0,1.2fr)_minmax(0,1fr)_minmax(0,0.8fr)_minmax(0,1fr)] lg:items-center lg:rounded-none lg:border-0 lg:border-t lg:p-0 lg:shadow-none"
                  >
                    {cells.map((value, i) => (
                      <div
                        key={columns[i]}
                        role="cell"
                        data-label={columns[i]}
                        className="flex justify-between gap-4 py-1 break-words before:font-medium before:text-muted before:content-[attr(data-label)] lg:block lg:px-3 lg:py-2 lg:before:hidden"
                      >
                        <span className="min-w-0 text-right lg:text-left">{value}</span>
                      </div>
                    ))}
                    <div role="cell" className="pt-2 lg:px-3 lg:py-2">
                      {u.blocked && (
                        <Button
                          variant="secondary"
                          className="w-full lg:w-auto"
                          loading={unblock.isPending && unblock.variables === u.id}
                          onClick={() => {
                            setNotice('')
                            unblock.mutate(u.id)
                          }}
                        >
                          Desbloquear
                        </Button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </PageContainer>
  )
}
