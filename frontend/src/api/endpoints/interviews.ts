import type { ApiClient } from '../client.ts'
import { ApiError } from '../types.ts'
import type {
  InterviewResponse,
  ReportResponse,
  StartInterviewRequest,
  SubmitAnswerRequest,
} from '../types.ts'

export function startInterview(
  client: ApiClient,
  body: StartInterviewRequest,
): Promise<InterviewResponse> {
  return client.request<InterviewResponse>('POST', '/interviews', body)
}

export async function getActiveInterview(
  client: ApiClient,
): Promise<InterviewResponse | null> {
  try {
    return await client.request<InterviewResponse>('GET', '/interviews/active')
  } catch (error) {
    if (
      error instanceof ApiError &&
      error.status === 404 &&
      error.code === 'NO_ACTIVE_INTERVIEW'
    ) {
      return null
    }
    throw error
  }
}

export function submitAnswer(
  client: ApiClient,
  interviewId: string,
  body: SubmitAnswerRequest,
): Promise<InterviewResponse> {
  return client.request<InterviewResponse>(
    'POST',
    `/interviews/${interviewId}/answers`,
    body,
  )
}

export function getReport(
  client: ApiClient,
  interviewId: string,
): Promise<ReportResponse> {
  return client.request<ReportResponse>(
    'GET',
    `/interviews/${interviewId}/report`,
  )
}
