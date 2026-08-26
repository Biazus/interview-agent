import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getDomains, getTopics } from '../api/endpoints/discovery.ts'
import { getActiveInterview, startInterview } from '../api/endpoints/interviews.ts'
import { ApiError } from '../api/types.ts'
import { useApiClient } from '../api/useApiClient.ts'
import { Banner, Button, ErrorAlert, Select, Spinner } from '../components/ui/index.ts'
import { useActiveInterview } from '../hooks/useActiveInterview.ts'

const DIFFICULTY_OPTIONS = [1, 2, 3, 4, 5].map((level) => ({
  value: String(level),
  label: `Nível ${level}`,
}))

const RAG_SEED_HINT =
  'Execute: docker compose --profile seed run --rm seed — ou: uv run python scripts/run_seed.py'

type SubmitError = {
  detail: string
  hint?: string
}

export function SetupPage() {
  const client = useApiClient()
  const navigate = useNavigate()
  const {
    active,
    isLoading: isLoadingActive,
    error: activeError,
    refetch: refetchActive,
  } = useActiveInterview()

  const [domains, setDomains] = useState<string[]>([])
  const [topics, setTopics] = useState<string[]>([])
  const [selectedDomain, setSelectedDomain] = useState('')
  const [selectedTopic, setSelectedTopic] = useState('')
  const [difficulty, setDifficulty] = useState('1')
  const [isLoadingDomains, setIsLoadingDomains] = useState(true)
  const [isLoadingTopics, setIsLoadingTopics] = useState(false)
  const [domainsError, setDomainsError] = useState<Error | null>(null)
  const [topicsError, setTopicsError] = useState<Error | null>(null)
  const [submitError, setSubmitError] = useState<SubmitError | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const topicsFetchIdRef = useRef(0)

  const isInitialLoading = isLoadingDomains || isLoadingActive

  const fetchTopics = useCallback(
    (domain: string) => {
      const fetchId = ++topicsFetchIdRef.current
      setSelectedTopic('')
      setIsLoadingTopics(true)
      setTopicsError(null)

      getTopics(client, domain)
        .then((list) => {
          if (fetchId !== topicsFetchIdRef.current) {
            return
          }
          setTopics(list)
          if (list.length > 0) {
            setSelectedTopic(list[0])
          }
        })
        .catch((err) => {
          if (fetchId !== topicsFetchIdRef.current) {
            return
          }
          setTopicsError(err instanceof Error ? err : new Error(String(err)))
          setTopics([])
        })
        .finally(() => {
          if (fetchId === topicsFetchIdRef.current) {
            setIsLoadingTopics(false)
          }
        })
    },
    [client],
  )

  const fetchDomains = useCallback(() => {
    setIsLoadingDomains(true)
    setDomainsError(null)

    getDomains(client)
      .then((list) => {
        setDomains(list)
        if (list.length > 0) {
          setSelectedDomain(list[0])
        } else {
          setSelectedDomain('')
        }
      })
      .catch((err) => {
        setDomainsError(err instanceof Error ? err : new Error(String(err)))
        setDomains([])
        setSelectedDomain('')
      })
      .finally(() => {
        setIsLoadingDomains(false)
      })
  }, [client])

  useEffect(() => {
    fetchDomains()
  }, [fetchDomains])

  useEffect(() => {
    if (!selectedDomain) {
      setTopics([])
      setSelectedTopic('')
      setIsLoadingTopics(false)
      setTopicsError(null)
      return
    }

    fetchTopics(selectedDomain)
  }, [fetchTopics, selectedDomain])

  const canStart =
    !isInitialLoading &&
    !isSubmitting &&
    active === null &&
    domains.length > 0 &&
    selectedDomain !== '' &&
    topics.length > 0 &&
    selectedTopic !== '' &&
    !isLoadingTopics

  async function handleStart() {
    setSubmitError(null)
    setIsSubmitting(true)

    try {
      const response = await startInterview(client, {
        domain: selectedDomain,
        topic: selectedTopic,
        difficulty: Number(difficulty),
      })
      navigate(`/interview/${response.interview_id}`, { replace: true })
    } catch (err) {
      if (err instanceof ApiError && err.code === 'ACTIVE_INTERVIEW_EXISTS') {
        try {
          const recovered = await getActiveInterview(client)
          await refetchActive()
          if (recovered === null) {
            setSubmitError({
              detail:
                'Já existe uma entrevista ativa, mas não foi possível recuperá-la. Tente novamente.',
            })
          }
        } catch {
          setSubmitError({
            detail:
              'Já existe uma entrevista ativa, mas não foi possível recuperá-la. Tente novamente.',
          })
        }
      } else if (err instanceof ApiError && err.code === 'RAG_NOT_READY') {
        setSubmitError({ detail: err.detail, hint: RAG_SEED_HINT })
      } else {
        setSubmitError({
          detail: 'Não foi possível iniciar a entrevista. Tente novamente.',
        })
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  if (isInitialLoading) {
    return (
      <div className="mx-auto flex w-full max-w-md justify-center py-12">
        <Spinner label="Carregando configuração" />
      </div>
    )
  }

  return (
    <div className="mx-auto w-full max-w-md space-y-6">
      <div className="text-center">
        <h1 className="text-2xl font-semibold text-gray-900">Configurar entrevista</h1>
        <p className="mt-2 text-sm text-gray-600">
          Escolha domínio, tópico e dificuldade para começar.
        </p>
      </div>

      {active !== null && (
        <Banner message="Você tem uma entrevista em andamento.">
          <Link
            to={`/interview/${active.interview_id}`}
            className="font-medium text-blue-700 hover:text-blue-800"
          >
            Retomar entrevista
          </Link>
        </Banner>
      )}

      {domainsError !== null && (
        <div className="space-y-2">
          <ErrorAlert message="Não foi possível carregar os domínios." />
          <div className="flex justify-center">
            <Button variant="secondary" onClick={fetchDomains}>
              Tentar novamente
            </Button>
          </div>
        </div>
      )}

      {activeError !== null && (
        <div className="space-y-2">
          <ErrorAlert message="Não foi possível verificar a entrevista ativa." />
          <div className="flex justify-center">
            <Button variant="secondary" onClick={() => void refetchActive()}>
              Tentar novamente
            </Button>
          </div>
        </div>
      )}

      {domains.length === 0 && domainsError === null && (
        <p className="text-center text-sm text-gray-600">
          Nenhum domínio disponível no momento.
        </p>
      )}

      {domains.length > 0 && (
        <Select
          id="setup-domain"
          label="Domínio"
          value={selectedDomain}
          onChange={setSelectedDomain}
          options={domains.map((domain) => ({ value: domain, label: domain }))}
          disabled={isSubmitting}
        />
      )}

      {topicsError !== null && (
        <div className="space-y-2">
          <ErrorAlert message="Não foi possível carregar os tópicos." />
          <div className="flex justify-center">
            <Button
              variant="secondary"
              onClick={() => fetchTopics(selectedDomain)}
            >
              Tentar novamente
            </Button>
          </div>
        </div>
      )}

      {selectedDomain !== '' &&
        !isLoadingTopics &&
        topics.length === 0 &&
        topicsError === null && (
          <p className="text-center text-sm text-gray-600">
            Nenhum tópico disponível para este domínio.
          </p>
        )}

      {selectedDomain !== '' && (
        <Select
          id="setup-topic"
          label="Tópico"
          value={selectedTopic}
          onChange={setSelectedTopic}
          options={topics.map((topic) => ({ value: topic, label: topic }))}
          disabled={isSubmitting || isLoadingTopics || topics.length === 0}
          placeholder={isLoadingTopics ? 'Carregando tópicos…' : 'Selecione um tópico'}
        />
      )}

      <Select
        id="setup-difficulty"
        label="Dificuldade"
        value={difficulty}
        onChange={setDifficulty}
        options={DIFFICULTY_OPTIONS}
        disabled={isSubmitting}
      />

      {submitError !== null && (
        <div className="space-y-1">
          <ErrorAlert message={submitError.detail} />
          {submitError.hint !== undefined && (
            <p className="text-sm text-gray-600">{submitError.hint}</p>
          )}
        </div>
      )}

      <div className="flex justify-center">
        <Button onClick={() => void handleStart()} disabled={!canStart} isLoading={isSubmitting}>
          Iniciar
        </Button>
      </div>
    </div>
  )
}
