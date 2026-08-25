import { useContext } from 'react'
import type { ApiClient } from './client.ts'
import { ApiClientContext } from './apiClientContext.ts'

export function useApiClient(): ApiClient {
  const client = useContext(ApiClientContext)
  if (!client) {
    throw new Error('useApiClient must be used within ApiClientProvider')
  }
  return client
}
