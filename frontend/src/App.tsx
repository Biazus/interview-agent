import { useEffect, useState } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { useApiClient } from './api/useApiClient.ts'
import { useAuthSync } from './auth/useAuthSync.ts'
import { GuestRoute } from './components/guards/GuestRoute.tsx'
import { RequireAuth } from './components/guards/RequireAuth.tsx'
import { AppShell } from './components/layout/AppShell.tsx'
import { LoginPage } from './pages/LoginPage.tsx'
import { RegisterPage } from './pages/RegisterPage.tsx'

function Home() {
  const client = useApiClient()
  const [healthStatus, setHealthStatus] = useState<string | null>(null)

  useEffect(() => {
    client
      .request<{ status: string }>('GET', '/health')
      .then((data) => setHealthStatus(data.status))
      .catch(() => setHealthStatus('error'))
  }, [client])

  return (
    <div className="flex flex-col items-center gap-4 text-center">
      <p className="text-gray-600">Frontend MVP — Tailwind v4 ready</p>
      {healthStatus !== null && (
        <p className="text-sm text-gray-500">API health: {healthStatus}</p>
      )}
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
