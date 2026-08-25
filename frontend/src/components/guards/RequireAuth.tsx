import { Navigate, Outlet } from 'react-router-dom'
import { authStorage } from '../../auth/authStorage.ts'

export function RequireAuth() {
  if (!authStorage.getToken()) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
