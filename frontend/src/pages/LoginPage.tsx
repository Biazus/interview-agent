import { type FormEvent, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { login } from '../api/endpoints/auth.ts'
import { ApiError } from '../api/types.ts'
import { useApiClient } from '../api/useApiClient.ts'
import { authStorage } from '../auth/authStorage.ts'

const MIN_PASSWORD_LENGTH = 8
const MAX_PASSWORD_LENGTH = 128

function validatePassword(password: string): string | null {
  if (password.length < MIN_PASSWORD_LENGTH || password.length > MAX_PASSWORD_LENGTH) {
    return `A senha deve ter entre ${MIN_PASSWORD_LENGTH} e ${MAX_PASSWORD_LENGTH} caracteres.`
  }
  return null
}

export function LoginPage() {
  const client = useApiClient()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const registered = searchParams.get('registered') === '1'
  const sessionExpired = searchParams.get('reason') === 'session_expired'

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)

    const passwordError = validatePassword(password)
    if (passwordError) {
      setError(passwordError)
      return
    }

    setIsSubmitting(true)
    try {
      const { access_token } = await login(client, { email, password })
      authStorage.setToken(access_token)
      navigate('/', { replace: true })
    } catch (err) {
      if (err instanceof ApiError && err.code === 'INVALID_CREDENTIALS') {
        setError('E-mail ou senha incorretos.')
      } else {
        setError('Não foi possível entrar. Tente novamente.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <h1 className="text-3xl font-semibold text-blue-600">Entrar</h1>
          <p className="mt-2 text-gray-600">Acesse sua conta para praticar entrevistas.</p>
        </div>

        {registered && (
          <p
            className="rounded-md border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800"
            role="status"
          >
            Conta criada. Faça login.
          </p>
        )}

        {sessionExpired && (
          <p
            className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800"
            role="status"
          >
            Sessão expirada. Faça login novamente.
          </p>
        )}

        <form className="space-y-4" onSubmit={handleSubmit} noValidate>
          <div>
            <label htmlFor="login-email" className="mb-1 block text-sm font-medium text-gray-700">
              E-mail
            </label>
            <input
              id="login-email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label htmlFor="login-password" className="mb-1 block text-sm font-medium text-gray-700">
              Senha
            </label>
            <input
              id="login-password"
              type="password"
              autoComplete="current-password"
              required
              minLength={MIN_PASSWORD_LENGTH}
              maxLength={MAX_PASSWORD_LENGTH}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {error && (
            <p className="text-sm text-red-600" role="alert">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-md bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? 'Entrando…' : 'Entrar'}
          </button>
        </form>

        <p className="text-center text-sm text-gray-600">
          Não tem conta?{' '}
          <Link to="/register" className="font-medium text-blue-600 hover:text-blue-700">
            Criar conta
          </Link>
        </p>
      </div>
    </main>
  )
}
