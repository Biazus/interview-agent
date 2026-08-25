import { type FormEvent, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { submitAnswer } from '../api/endpoints/interviews.ts'
import { useApiClient } from '../api/useApiClient.ts'
import { Button, ErrorAlert, Textarea } from '../components/ui/index.ts'
import { MAX_ANSWER_LENGTH, TOTAL_QUESTIONS } from '../constants.ts'
import { useActiveInterview } from '../hooks/useActiveInterview.ts'

export function InterviewPage() {
  const { interviewId } = useParams<{ interviewId: string }>()
  const client = useApiClient()
  const navigate = useNavigate()
  const { active, refetch } = useActiveInterview()
  const [answer, setAnswer] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  if (!active?.current_question) {
    return (
      <div className="mx-auto w-full max-w-2xl">
        <ErrorAlert message="Não há pergunta disponível no momento." />
      </div>
    )
  }

  const { current_question, questions_answered } = active
  const canSubmit = answer.trim().length > 0 && !isSubmitting

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const trimmedAnswer = answer.trim()
    if (!trimmedAnswer) {
      setSubmitError('Digite uma resposta antes de enviar.')
      return
    }

    if (!interviewId) {
      return
    }

    setSubmitError(null)
    setIsSubmitting(true)

    try {
      const response = await submitAnswer(client, interviewId, {
        answer: trimmedAnswer,
      })

      if (response.finished) {
        navigate(`/report/${interviewId}`, { replace: true })
        return
      }

      await refetch()
      setAnswer('')
    } catch {
      setSubmitError('Não foi possível enviar a resposta. Tente novamente.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="mx-auto w-full max-w-2xl space-y-6">
      <div>
        <p className="text-sm text-gray-600">
          Progresso: {questions_answered}/{TOTAL_QUESTIONS} perguntas respondidas
        </p>
        <h1 className="mt-2 text-2xl font-semibold text-gray-900">Entrevista técnica</h1>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <p className="text-base leading-relaxed text-gray-900">{current_question.prompt}</p>
      </div>

      <form className="space-y-4" onSubmit={(event) => void handleSubmit(event)} noValidate>
        <Textarea
          id="interview-answer"
          label="Sua resposta"
          value={answer}
          onChange={setAnswer}
          maxLength={MAX_ANSWER_LENGTH}
          disabled={isSubmitting}
        />

        <div className="flex items-center justify-between text-sm text-gray-600">
          <span>
            {answer.length}/{MAX_ANSWER_LENGTH} caracteres
          </span>
        </div>

        {submitError !== null && <ErrorAlert message={submitError} />}

        <div className="flex justify-end">
          <Button type="submit" disabled={!canSubmit} isLoading={isSubmitting}>
            Enviar
          </Button>
        </div>
      </form>
    </div>
  )
}
