import { useEffect, useState } from 'react'
import { BrowserRouter, Route, Routes, useNavigate } from 'react-router-dom'
import { useApiClient } from './api/useApiClient.ts'
import { authStorage } from './auth/authStorage.ts'
import { useAuthSync } from './auth/useAuthSync.ts'
import { GuestRoute } from './components/guards/GuestRoute.tsx'
import { RequireAuth } from './components/guards/RequireAuth.tsx'
import { LoginPage } from './pages/LoginPage.tsx'
import { RegisterPage } from './pages/RegisterPage.tsx'

function Home() {
  const client = useApiClient()
  const navigate = useNavigate()
  const [healthStatus, setHealthStatus] = useState<string | null>(null)

  useEffect(() => {
    client
      .request<{ status: string }>('GET', '/health')
      .then((data) => setHealthStatus(data.status))
      .catch(() => setHealthStatus('error'))
  }, [client])

  function handleLogout() {
    navigate('/login', { replace: true })
    authStorage.clear()
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-3xl font-semibold text-blue-600">Interview Agent</h1>
      <p className="text-gray-600">Frontend MVP — Tailwind v4 ready</p>
      {healthStatus !== null && (
        <p className="text-sm text-gray-500">API health: {healthStatus}</p>
      )}
      <button
        type="button"
        onClick={handleLogout}
        className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
      >
        Sair
      </button>
    </main>
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
        <Route path="/" element={<Home />} />
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
