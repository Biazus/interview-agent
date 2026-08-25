const STORAGE_KEY = 'interview-agent:access_token'

type Listener = () => void

const listeners = new Set<Listener>()

function notifyListeners(): void {
  for (const listener of listeners) {
    listener()
  }
}

function handleStorageEvent(event: StorageEvent): void {
  if (event.key === STORAGE_KEY || event.key === null) {
    notifyListeners()
  }
}

if (typeof window !== 'undefined') {
  window.addEventListener('storage', handleStorageEvent)
}

export const authStorage = {
  getToken(): string | null {
    return localStorage.getItem(STORAGE_KEY)
  },

  setToken(token: string): void {
    localStorage.setItem(STORAGE_KEY, token)
    notifyListeners()
  },

  clear(): void {
    localStorage.removeItem(STORAGE_KEY)
    notifyListeners()
  },

  onChange(callback: Listener): () => void {
    listeners.add(callback)
    return () => {
      listeners.delete(callback)
    }
  },
}
