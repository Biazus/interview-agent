import { Link, useParams } from 'react-router-dom'

export function ReportStubPage() {
  const { interviewId } = useParams<{ interviewId: string }>()

  return (
    <div className="mx-auto w-full max-w-md space-y-6 text-center">
      <h1 className="text-2xl font-semibold text-gray-900">Relatório em construção</h1>
      {interviewId && (
        <p className="text-sm text-gray-500">
          ID da entrevista: <span className="font-mono">{interviewId}</span>
        </p>
      )}
      <p className="text-gray-600">Esta página será implementada em breve.</p>
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
