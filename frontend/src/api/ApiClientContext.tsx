import type { ReactNode } from 'react'
import { ApiClientContext, apiClient } from './apiClientContext.ts'

export function ApiClientProvider({ children }: { children: ReactNode }) {
  return (
    <ApiClientContext.Provider value={apiClient}>
      {children}
    </ApiClientContext.Provider>
  )
}
