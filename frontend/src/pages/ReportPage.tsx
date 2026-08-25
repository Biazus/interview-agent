import { useNavigate, useOutletContext } from 'react-router-dom'
import type { ReportResponse } from '../api/types.ts'
import { Button } from '../components/ui/index.ts'

function ReportList({ items }: { items: string[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-gray-500">Nenhum item listado.</p>
  }

  return (
    <ul className="list-disc space-y-2 pl-5 text-gray-700">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  )
}

export function ReportPage() {
  const { report } = useOutletContext<{ report: ReportResponse }>()
  const navigate = useNavigate()

  return (
    <div className="mx-auto w-full max-w-2xl space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Relatório da entrevista</h1>
        <p className="mt-2 text-sm text-gray-600">
          {report.total_questions} perguntas respondidas
        </p>
      </div>

      <section className="space-y-3">
        <h2 className="text-lg font-medium text-gray-900">Resumo</h2>
        <p className="leading-relaxed text-gray-700">{report.overall_summary}</p>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-medium text-gray-900">Pontos fortes</h2>
        <ReportList items={report.strengths} />
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-medium text-gray-900">Pontos a melhorar</h2>
        <ReportList items={report.weaknesses} />
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-medium text-gray-900">Sugestões</h2>
        <ReportList items={report.suggestions} />
      </section>

      <div className="pt-2">
        <Button onClick={() => navigate('/')}>Nova entrevista</Button>
      </div>
    </div>
  )
}
