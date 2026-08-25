import { Route, Routes } from 'react-router-dom'
import { useAuthSync } from './auth/useAuthSync.ts'
import { GuestRoute } from './components/guards/GuestRoute.tsx'
import { InterviewRouteGuard } from './components/guards/InterviewRouteGuard.tsx'
import { ReportRouteGuard } from './components/guards/ReportRouteGuard.tsx'
import { RequireAuth } from './components/guards/RequireAuth.tsx'
import { AppShell } from './components/layout/AppShell.tsx'
import { InterviewPage } from './pages/InterviewPage.tsx'
import { LoginPage } from './pages/LoginPage.tsx'
import { RegisterPage } from './pages/RegisterPage.tsx'
import { ReportPage } from './pages/ReportPage.tsx'
import { SetupPage } from './pages/SetupPage.tsx'

export function AppRoutes() {
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
          <Route path="/interview/:interviewId" element={<InterviewRouteGuard />}>
            <Route index element={<InterviewPage />} />
          </Route>
          <Route path="/report/:interviewId" element={<ReportRouteGuard />}>
            <Route index element={<ReportPage />} />
          </Route>
        </Route>
      </Route>
    </Routes>
  )
}
