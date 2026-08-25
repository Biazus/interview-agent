import { useCallback, useEffect, useRef, useState } from 'react'
import { getActiveInterview } from '../api/endpoints/interviews.ts'
import type { InterviewResponse } from '../api/types.ts'
import { useApiClient } from '../api/useApiClient.ts'

type UseActiveInterviewResult = {
  active: InterviewResponse | null
  isLoading: boolean
  error: Error | null
  refetch: () => Promise<void>
}

export function useActiveInterview(): UseActiveInterviewResult {
  const client = useApiClient()
  const [active, setActive] = useState<InterviewResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const fetchIdRef = useRef(0)
  const mountedRef = useRef(true)

  const fetchActive = useCallback(async () => {
    const fetchId = ++fetchIdRef.current
    setIsLoading(true)
    setError(null)

    try {
      const result = await getActiveInterview(client)
      if (!mountedRef.current || fetchId !== fetchIdRef.current) {
        return
      }
      setActive(result)
    } catch (err) {
      if (!mountedRef.current || fetchId !== fetchIdRef.current) {
        return
      }
      setError(err instanceof Error ? err : new Error(String(err)))
    } finally {
      if (mountedRef.current && fetchId === fetchIdRef.current) {
        setIsLoading(false)
      }
    }
  }, [client])

  useEffect(() => {
    mountedRef.current = true
    void fetchActive()

    return () => {
      mountedRef.current = false
      fetchIdRef.current += 1
    }
  }, [fetchActive])

  return {
    active,
    isLoading,
    error,
    refetch: fetchActive,
  }
}
