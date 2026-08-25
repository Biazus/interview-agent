import { useCallback, useEffect, useState } from 'react'
import { Link, Navigate, Outlet, useParams } from 'react-router-dom'
import { getReport } from '../../api/endpoints/interviews.ts'
import { useApiClient } from '../../api/useApiClient.ts'
import { ApiError } from '../../api/types.ts'
import type { ReportResponse } from '../../api/types.ts'
import {
  resolveReportRoute,
  type ReportLoadState,
} from '../../lib/resolveReportRoute.ts'
import { Button, ErrorAlert, Spinner } from '../ui/index.ts'

export function ReportRouteGuard() {
  const { interviewId } = useParams<{ interviewId: string }>()
  const client = useApiClient()
  const [loadState, setLoadState] = useState<ReportLoadState>({ phase: 'loading' })
  const [retryCount, setRetryCount] = useState(0)

  const fetchReport = useCallback(() => {
    if (!interviewId) {
      return
    }

    setLoadState({ phase: 'loading' })

    getReport(client, interviewId)
      .then((report: ReportResponse) => {
        setLoadState({ phase: 'success', report })
      })
      .catch((error: unknown) => {
        const apiError = error instanceof ApiError ? error : null
        setLoadState({ phase: 'error', error: apiError })
      })
  }, [client, interviewId])

  useEffect(() => {
    fetchReport()
  }, [fetchReport, retryCount])

  if (!interviewId) {
    return <Navigate to="/" replace />
  }

  const outcome = resolveReportRoute(interviewId, loadState)

  if (outcome.type === 'loading') {
    return (
      <div className="mx-auto flex w-full max-w-2xl justify-center py-12">
        <Spinner label="Carregando relatório" />
      </div>
    )
  }

  if (outcome.type === 'redirect') {
    return <Navigate to={outcome.to} replace />
  }

  if (outcome.type === 'llm_unavailable') {
    return (
      <div className="mx-auto w-full max-w-2xl space-y-4 text-center">
        <ErrorAlert message={outcome.message} />
        <div className="flex justify-center">
          <Button onClick={() => setRetryCount((count) => count + 1)}>
            Tentar novamente
          </Button>
        </div>
      </div>
    )
  }

  if (outcome.type === 'error') {
    return (
      <div className="mx-auto w-full max-w-2xl space-y-4 text-center">
        <ErrorAlert message="Não foi possível carregar o relatório." />
        <div className="flex justify-center">
          <Link
            to="/"
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          >
            Voltar ao início
          </Link>
        </div>
      </div>
    )
  }

  return <Outlet context={{ report: outcome.report }} />
}
