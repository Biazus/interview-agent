import { Navigate, Outlet } from 'react-router-dom'
import { authStorage } from '../../auth/authStorage.ts'

export function GuestRoute() {
  if (authStorage.getToken()) {
    return <Navigate to="/" replace />
  }

  return <Outlet />
}
