import { useNavigate } from 'react-router-dom'
import { authStorage } from '../../auth/authStorage.ts'

export function Header() {
  const navigate = useNavigate()

  function handleLogout() {
    authStorage.clear()
    navigate('/login', { replace: true })
  }

  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4 sm:px-6">
        <h1 className="text-xl font-semibold text-blue-600">Interview Agent</h1>
        <button
          type="button"
          onClick={handleLogout}
          className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
        >
          Sair
        </button>
      </div>
    </header>
  )
}
