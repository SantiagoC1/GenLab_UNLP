import { useMutation } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Alert } from '../../components/Alert'
import { Button } from '../../components/Button'
import { TextField } from '../../components/TextField'
import { login, toSession, verifyCode, type SessionResponse } from '../../lib/access'
import { initialScreen } from '../pantallas'
import { useRol } from '../rol-context'

/** Escenario 4 · M1-RF8 a RF10. Contraseña y, si el dispositivo es nuevo, un código. */
export default function IngresarPantalla() {
  const { startSession } = useRol()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [asksForCode, setAsksForCode] = useState(false)
  const [resent, setResent] = useState(false)
  const [challenge, setChallenge] = useState('')

  const enter = (response: SessionResponse) => {
    const session = toSession(response)
    startSession(session)
    const destination = session.mustChangePassword
      ? '/cambiar-contrasena'
      : `/${session.rol}/${initialScreen(session.rol)}`
    navigate(destination, { replace: true })
  }

  const credentials = useMutation({
    mutationFn: () => login(email.trim(), password),
    onSuccess: (response) => {
      if (response.state === 'authenticated' && response.session) return enter(response.session)
      setCode('')
      setChallenge(response.challenge ?? '')
      setResent(asksForCode)
      setAsksForCode(true)
    },
  })
  const verification = useMutation({
    mutationFn: () => verifyCode(email.trim(), code.trim(), challenge),
    onSuccess: enter,
  })

  const submitCredentials = (event: FormEvent) => {
    event.preventDefault()
    verification.reset()
    credentials.mutate()
  }
  const submitCode = (event: FormEvent) => {
    event.preventDefault()
    verification.mutate()
  }
  const resendCode = () => {
    verification.reset()
    credentials.mutate()
  }
  const goBack = () => {
    setAsksForCode(false)
    setResent(false)
    credentials.reset()
    verification.reset()
  }

  return (
    <section>
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">Ingresar al sistema</h1>

      {!asksForCode ? (
        <form onSubmit={submitCredentials} className="mt-6 space-y-4">
          {credentials.error && <Alert kind="error">{credentials.error.message}</Alert>}
          <TextField
            label="Mail"
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <TextField
            label="Contraseña"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <Button type="submit" loading={credentials.isPending}>
            Ingresar
          </Button>
          <p className="text-sm text-slate-600">
            ¿No tenés cuenta?{' '}
            <Link to="/registro" className="text-teal-700 underline">
              Registrate
            </Link>
          </p>
        </form>
      ) : (
        <form onSubmit={submitCode} className="mt-6 space-y-4">
          {/* 10 minutos: ajuste `code_expire_minutes` del backend */}
          <Alert>
            {resent
              ? `Te enviamos un código nuevo a ${email}. Vence a los 10 minutos.`
              : `Te enviamos un código de verificación a ${email}. Vence a los 10 minutos.`}
          </Alert>
          {verification.error && <Alert kind="error">{verification.error.message}</Alert>}
          {credentials.error && <Alert kind="error">{credentials.error.message}</Alert>}
          <TextField
            label="Código de verificación"
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
            required
            value={code}
            onChange={(e) => setCode(e.target.value)}
          />
          <div className="flex flex-wrap gap-2">
            <Button type="submit" loading={verification.isPending}>
              Verificar el código
            </Button>
            <Button variant="secondary" loading={credentials.isPending} onClick={resendCode}>
              Pedir un código nuevo
            </Button>
            <Button variant="secondary" onClick={goBack}>
              Volver
            </Button>
          </div>
        </form>
      )}
    </section>
  )
}
