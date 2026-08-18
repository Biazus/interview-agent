class LLMProviderError(Exception): ...


class TransientProviderError(LLMProviderError):
    """Falha transiente — a cadeia de fallback pode tentar o próximo provider."""


class PermanentProviderError(LLMProviderError):
    """Falha permanente — não faz sentido tentar outro provider com o mesmo request."""


class RateLimitError(TransientProviderError): ...


class ProviderUnavailableError(TransientProviderError): ...


class AuthenticationError(PermanentProviderError): ...


class InvalidRequestError(PermanentProviderError): ...


class StructuredOutputError(LLMProviderError):
    """Resposta do LLM não é JSON válido ou não conforma ao schema esperado."""
