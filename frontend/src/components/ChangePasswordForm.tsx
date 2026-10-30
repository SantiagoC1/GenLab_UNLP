import { useMutation } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { changePassword } from '../lib/access'
import { validateNewPassword } from '../lib/validation'
import { initialScreen } from '../roles/pantallas'
import { useRol } from '../roles/rol-context'
import { Alert } from './Alert'
import { Button } from './Button'
import { TextField } from './TextField'

export function ChangePasswordForm() {
  const { session, startSession } = useRol()
  const navigate = useNavigate()
  const [current, setCurrent] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})

  const change = useMutation({
    mutationFn: () => changePassword(current, newPassword, confirmation),
    onSuccess: () => {
      if (session) startSession({ ...session, mustChangePassword: false })
      const rol = session?.rol ?? 'paciente'
      navigate(`/${rol}/${initialScreen(rol)}`, { replace: true })
    },
  })

  const submit = (event: FormEvent) => {
    event.preventDefault()
    const found: Record<string, string> = {}
    if (!current) found.current = 'Completá la contraseña actual.'
    const newPasswordError = validateNewPassword(newPassword)
    if (newPasswordError) found.newPassword = newPasswordError
    // Si no coinciden, no se guarda nada y se vuelven a pedir las dos (escenario 3).
    else if (newPassword !== confirmation) {
      found.confirmation = 'Las contraseñas no coinciden.'
      setNewPassword('')
      setConfirmation('')
    }
    setErrors(found)
    if (Object.keys(found).length === 0) change.mutate()
  }

  return (
    <form onSubmit={submit} noValidate className="mt-6 space-y-4">
      {change.error && <Alert kind="error">{change.error.message}</Alert>}
      <TextField
        label="Contraseña actual"
        type="password"
        autoComplete="current-password"
        value={current}
        error={errors.current}
        onChange={(e) => setCurrent(e.target.value)}
      />
      <TextField
        label="Contraseña nueva"
        type="password"
        autoComplete="new-password"
        value={newPassword}
        error={errors.newPassword}
        onChange={(e) => setNewPassword(e.target.value)}
      />
      <TextField
        label="Repetí la contraseña nueva"
        type="password"
        autoComplete="new-password"
        value={confirmation}
        error={errors.confirmation}
        onChange={(e) => setConfirmation(e.target.value)}
      />
      <Button type="submit" loading={change.isPending}>
        Guardar la contraseña
      </Button>
    </form>
  )
}
