import type { ReportResponse } from '../api/types.ts'
import { ApiError } from '../api/types.ts'

export type ReportLoadState =
  | { phase: 'loading' }
  | { phase: 'success'; report: ReportResponse }
  | { phase: 'error'; error: ApiError | null }

export type ReportRouteOutcome =
  | { type: 'loading' }
  | { type: 'render'; report: ReportResponse }
  | { type: 'redirect'; to: string }
  | { type: 'llm_unavailable'; message: string }
  | { type: 'error' }

export function resolveReportRoute(
  interviewId: string,
  state: ReportLoadState,
): ReportRouteOutcome {
  if (state.phase === 'loading') {
    return { type: 'loading' }
  }

  if (state.phase === 'success') {
    return { type: 'render', report: state.report }
  }

  const error = state.error
  if (error?.status === 404 && error.code === 'INTERVIEW_NOT_FOUND') {
    return { type: 'redirect', to: '/' }
  }

  if (error?.status === 409 && error.code === 'INTERVIEW_NOT_FINISHED') {
    return { type: 'redirect', to: `/interview/${interviewId}` }
  }

  if (error?.status === 503 && error.code === 'LLM_UNAVAILABLE') {
    return {
      type: 'llm_unavailable',
      message: error.detail || 'Serviço temporariamente indisponível. Tente novamente.',
    }
  }

  return { type: 'error' }
}
