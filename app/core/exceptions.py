class AppError(Exception):
    """Erro de aplicação independente de HTTP."""

    code: str
    message: str

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)


class ActiveInterviewExists(AppError):
    code = "ACTIVE_INTERVIEW_EXISTS"
    message = "Já existe uma entrevista ativa para este candidato."


class InterviewNotFound(AppError):
    code = "INTERVIEW_NOT_FOUND"
    message = "Entrevista não encontrada."


class NoActiveInterview(AppError):
    code = "NO_ACTIVE_INTERVIEW"
    message = "Nenhuma entrevista ativa encontrada."


class InterviewAlreadyFinished(AppError):
    code = "INTERVIEW_ALREADY_FINISHED"
    message = "A entrevista já foi finalizada."


class InterviewNotFinished(AppError):
    code = "INTERVIEW_NOT_FINISHED"
    message = "A entrevista ainda está em andamento."


class InvalidDomain(AppError):
    code = "INVALID_DOMAIN"
    message = "Domínio inválido."


class DomainRequired(InvalidDomain):
    message = "Parâmetro domain é obrigatório."


class InvalidTopic(AppError):
    code = "INVALID_TOPIC"
    message = "Tópico inválido para o domínio informado."


class EmptyAnswer(AppError):
    code = "EMPTY_ANSWER"
    message = "A resposta não pode ser vazia."


class DuplicateTurn(AppError):
    code = "DUPLICATE_TURN"
    message = "Turno duplicado para esta entrevista."


class LLMUnavailable(AppError):
    code = "LLM_UNAVAILABLE"
    message = "Serviço de avaliação temporariamente indisponível."


class RagNotReady(AppError):
    code = "RAG_NOT_READY"
    message = "Base de conhecimento RAG indisponível. Execute o seed antes de iniciar entrevistas."


class EmailAlreadyRegistered(AppError):
    code = "EMAIL_ALREADY_REGISTERED"
    message = "E-mail já cadastrado."


class InvalidCredentials(AppError):
    code = "INVALID_CREDENTIALS"
    message = "Credenciais inválidas."


class MissingToken(AppError):
    code = "MISSING_TOKEN"
    message = "Token de autenticação ausente."


class InvalidToken(AppError):
    code = "INVALID_TOKEN"
    message = "Token de autenticação inválido."
