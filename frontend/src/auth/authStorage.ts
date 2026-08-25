const STORAGE_KEY = 'interview-agent:access_token'

export const authStorage = {
  getToken(): string | null {
    return localStorage.getItem(STORAGE_KEY)
  },

  setToken(token: string): void {
    localStorage.setItem(STORAGE_KEY, token)
  },

  clear(): void {
    localStorage.removeItem(STORAGE_KEY)
  },
}
