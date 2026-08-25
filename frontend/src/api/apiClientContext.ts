import { createContext } from 'react'
import { authStorage } from '../auth/authStorage.ts'
import { createApiClient, type ApiClient } from './client.ts'

export const apiClient = createApiClient({
  getToken: () => authStorage.getToken(),
  onUnauthorized: () => {
    authStorage.clear()
    window.location.href = '/login'
  },
})

export const ApiClientContext = createContext<ApiClient | null>(null)
