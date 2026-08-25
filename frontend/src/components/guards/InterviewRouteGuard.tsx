import { useEffect, useState } from 'react'
import { Link, Navigate, Outlet, useParams } from 'react-router-dom'
import { getReport } from '../../api/endpoints/interviews.ts'
import { useApiClient } from '../../api/useApiClient.ts'
import { useActiveInterview } from '../../hooks/useActiveInterview.ts'
import {
  resolveInterviewRoute,
  type ReportProbeStatus,
} from '../../lib/resolveInterviewRoute.ts'
import { ErrorAlert, Spinner } from '../ui/index.ts'

export function InterviewRouteGuard() {
  const { interviewId } = useParams<{ interviewId: string }>()
  const client = useApiClient()
  const { active, isLoading, error } = useActiveInterview()
  const [reportProbeStatus, setReportProbeStatus] = useState<ReportProbeStatus>('idle')
  const [reportProbeDone, setReportProbeDone] = useState(false)

  useEffect(() => {
    if (
      !interviewId ||
      isLoading ||
      error !== null ||
      active !== null ||
      reportProbeDone
    ) {
      return
    }

    setReportProbeDone(true)
    setReportProbeStatus('loading')

    getReport(client, interviewId)
      .then(() => {
        setReportProbeStatus('success')
      })
      .catch(() => {
        setReportProbeStatus('failure')
      })
  }, [active, client, error, interviewId, isLoading, reportProbeDone])

  const outcome = resolveInterviewRoute({
    isLoading,
    active,
    error,
    interviewId: interviewId ?? '',
    reportProbeStatus,
  })

  if (outcome.type === 'loading') {
    return (
      <div className="mx-auto flex w-full max-w-2xl justify-center py-12">
        <Spinner label="Carregando entrevista" />
      </div>
    )
  }

  if (outcome.type === 'redirect') {
    return <Navigate to={outcome.to} replace />
  }

  if (outcome.type === 'error') {
    return (
      <div className="mx-auto w-full max-w-2xl space-y-4 text-center">
        <ErrorAlert message="Não foi possível carregar a entrevista." />
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

  return <Outlet />
}
