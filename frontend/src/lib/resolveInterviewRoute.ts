import type { InterviewResponse } from '../api/types.ts'

export type ReportProbeStatus = 'idle' | 'loading' | 'success' | 'failure'

export type InterviewRouteOutcome =
  | { type: 'loading' }
  | { type: 'render' }
  | { type: 'redirect'; to: string }
  | { type: 'error' }

export type ResolveInterviewRouteInput = {
  isLoading: boolean
  active: InterviewResponse | null
  error: Error | null
  interviewId: string
  reportProbeStatus: ReportProbeStatus
}

export function resolveInterviewRoute(
  input: ResolveInterviewRouteInput,
): InterviewRouteOutcome {
  const { isLoading, active, error, interviewId, reportProbeStatus } = input

  if (isLoading) {
    return { type: 'loading' }
  }

  if (error) {
    return { type: 'error' }
  }

  if (active !== null) {
    if (active.interview_id === interviewId) {
      return { type: 'render' }
    }
    return { type: 'redirect', to: `/interview/${active.interview_id}` }
  }

  if (reportProbeStatus === 'idle' || reportProbeStatus === 'loading') {
    return { type: 'loading' }
  }

  if (reportProbeStatus === 'success') {
    return { type: 'redirect', to: `/report/${interviewId}` }
  }

  return { type: 'redirect', to: '/' }
}
