import { useCallback, useEffect, useState } from 'react'
import { Link, BrowserRouter, Route, Routes } from 'react-router-dom'
import { useApiClient } from './api/useApiClient.ts'
import { useAuthSync } from './auth/useAuthSync.ts'
import { GuestRoute } from './components/guards/GuestRoute.tsx'
import { RequireAuth } from './components/guards/RequireAuth.tsx'
import { AppShell } from './components/layout/AppShell.tsx'
import { Banner, Button, ErrorAlert, Select, Spinner } from './components/ui/index.ts'
import { useActiveInterview } from './hooks/useActiveInterview.ts'
import { InterviewStubPage } from './pages/InterviewStubPage.tsx'
import { LoginPage } from './pages/LoginPage.tsx'
import { RegisterPage } from './pages/RegisterPage.tsx'
import { ReportStubPage } from './pages/ReportStubPage.tsx'

function Home() {
  const client = useApiClient()
  const {
    active,
    isLoading: isLoadingActive,
    error: activeError,
    refetch: refetchActive,
  } = useActiveInterview()
  const [healthStatus, setHealthStatus] = useState<string | null>(null)
  const [isLoadingHealth, setIsLoadingHealth] = useState(true)
  const [domain, setDomain] = useState('')

  const isLoading = isLoadingHealth || isLoadingActive

  const fetchHealth = useCallback(() => {
    setIsLoadingHealth(true)
    setHealthStatus(null)
    client
      .request<{ status: string }>('GET', '/health')
      .then((data) => setHealthStatus(data.status))
      .catch(() => setHealthStatus('error'))
      .finally(() => setIsLoadingHealth(false))
  }, [client])

  useEffect(() => {
    fetchHealth()
  }, [fetchHealth])

  return (
    <div className="mx-auto w-full max-w-md space-y-6">
      <p className="text-center text-gray-600">Frontend MVP — Tailwind v4 ready</p>

      {active !== null && (
        <Banner message="Você tem uma entrevista em andamento.">
          <Link
            to={`/interview/${active.interview_id}`}
            className="font-medium text-blue-700 hover:text-blue-800"
          >
            Retomar entrevista
          </Link>
        </Banner>
      )}

      <Select
        id="home-domain"
        label="Domínio (preview)"
        value={domain}
        onChange={setDomain}
        placeholder="Selecione um domínio"
        options={[
          { value: 'backend', label: 'Backend' },
          { value: 'frontend', label: 'Frontend' },
        ]}
        disabled={isLoading}
      />

      {isLoading && (
        <div className="flex justify-center">
          <Spinner
            label={
              isLoadingActive ? 'Verificando entrevista ativa' : 'Verificando API'
            }
          />
        </div>
      )}

      {!isLoading && activeError !== null && (
        <div className="space-y-2">
          <ErrorAlert message="Não foi possível verificar a entrevista ativa." />
          <div className="flex justify-center">
            <Button variant="secondary" onClick={() => void refetchActive()}>
              Tentar novamente
            </Button>
          </div>
        </div>
      )}

      {!isLoading && healthStatus === 'error' && (
        <ErrorAlert message="Não foi possível verificar o status da API." />
      )}

      {!isLoading && healthStatus !== null && healthStatus !== 'error' && (
        <p className="text-center text-sm text-gray-500">API health: {healthStatus}</p>
      )}

      <div className="flex justify-center gap-3">
        <Button variant="secondary" onClick={fetchHealth} isLoading={isLoadingHealth}>
          Atualizar status
        </Button>
        <Button disabled={active !== null}>Iniciar (em breve)</Button>
      </div>
    </div>
  )
}

function AppRoutes() {
  useAuthSync()

  return (
    <Routes>
      <Route element={<GuestRoute />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Route>

      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route path="/" element={<Home />} />
          <Route path="/interview/:interviewId" element={<InterviewStubPage />} />
          <Route path="/report/:interviewId" element={<ReportStubPage />} />
        </Route>
      </Route>
    </Routes>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}

export default App
