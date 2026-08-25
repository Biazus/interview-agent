import type { ApiClient } from '../client.ts'
import type {
  LoginRequest,
  RegisterRequest,
  RegisterResponse,
  TokenResponse,
} from '../types.ts'

export function register(
  client: ApiClient,
  body: RegisterRequest,
): Promise<RegisterResponse> {
  return client.request<RegisterResponse>('POST', '/auth/register', body)
}

export function login(
  client: ApiClient,
  body: LoginRequest,
): Promise<TokenResponse> {
  return client.request<TokenResponse>('POST', '/auth/login', body)
}
