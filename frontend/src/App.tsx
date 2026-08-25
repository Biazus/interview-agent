import { useEffect, useState } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { useApiClient } from './api/useApiClient.ts'

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
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-3xl font-semibold text-blue-600">
        Interview Agent
      </h1>
      <p className="text-gray-600">Frontend MVP — Tailwind v4 ready</p>
      {healthStatus !== null && (
        <p className="text-sm text-gray-500">API health: {healthStatus}</p>
      )}
    </main>
  )
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
