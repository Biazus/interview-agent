import { API_BASE_URL } from '../config/env.ts'
import { ApiError, type ApiErrorBody } from './types.ts'

export type ApiClientConfig = {
  getToken: () => string | null
  onUnauthorized: () => void
}

export type ApiClient = {
  request<T>(method: string, path: string, body?: unknown): Promise<T>
}

export function createApiClient(config: ApiClientConfig): ApiClient {
  async function request<T>(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }

    const token = config.getToken()
    if (token) {
      headers.Authorization = `Bearer ${token}`
    }

    const response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })

    if (!response.ok) {
      let detail = response.statusText
      let code = 'UNKNOWN'

      try {
        const parsed = (await response.json()) as Partial<ApiErrorBody>
        if (typeof parsed.detail === 'string') {
          detail = parsed.detail
        }
        if (typeof parsed.code === 'string') {
          code = parsed.code
        }
      } catch {
        // Response body is not JSON; use defaults above.
      }

      if (
        response.status === 401 &&
        (code === 'MISSING_TOKEN' || code === 'INVALID_TOKEN')
      ) {
        config.onUnauthorized()
      }

      throw new ApiError(response.status, detail, code)
    }

    if (response.status === 204) {
      return undefined as T
    }

    const text = await response.text()
    if (!text) {
      return undefined as T
    }

    return JSON.parse(text) as T
  }

  return { request }
}
