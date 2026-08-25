export type RegisterRequest = {
  email: string
  password: string
}

export type LoginRequest = {
  email: string
  password: string
}

export type RegisterResponse = {
  id: string
  email: string
}

export type TokenResponse = {
  access_token: string
  token_type: string
  expires_in: number
}

export type StartInterviewRequest = {
  domain: string
  topic: string
  difficulty?: number
}

export type SubmitAnswerRequest = {
  answer: string
}

export type CurrentQuestionResponse = {
  id: string
  topic: string
  difficulty: number
  prompt: string
}

export type InterviewResponse = {
  interview_id: string
  domain: string
  topic: string
  difficulty: number
  finished: boolean
  questions_answered: number
  current_question: CurrentQuestionResponse | null
}

export type ReportResponse = {
  interview_id: string
  overall_summary: string
  strengths: string[]
  weaknesses: string[]
  suggestions: string[]
  total_questions: number
}

export type ApiErrorBody = {
  detail: string
  code: string
}

export class ApiError extends Error {
  readonly status: number
  readonly detail: string
  readonly code: string

  constructor(status: number, detail: string, code: string) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
    this.code = code
  }
}
