import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { authStorage } from './authStorage.ts'

const GUEST_PATHS = new Set(['/login', '/register'])

export function useAuthSync(): void {
  const navigate = useNavigate()

  useEffect(() => {
    return authStorage.onChange(() => {
      if (authStorage.getToken()) {
        return
      }

      if (GUEST_PATHS.has(window.location.pathname)) {
        return
      }

      navigate('/login?reason=session_expired', { replace: true })
    })
  }, [navigate])
}
