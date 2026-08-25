import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { useAuthSync } from './auth/useAuthSync.ts'
import { GuestRoute } from './components/guards/GuestRoute.tsx'
import { RequireAuth } from './components/guards/RequireAuth.tsx'
import { AppShell } from './components/layout/AppShell.tsx'
import { InterviewStubPage } from './pages/InterviewStubPage.tsx'
import { LoginPage } from './pages/LoginPage.tsx'
import { RegisterPage } from './pages/RegisterPage.tsx'
import { ReportStubPage } from './pages/ReportStubPage.tsx'
import { SetupPage } from './pages/SetupPage.tsx'

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
          <Route path="/" element={<SetupPage />} />
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
