class LLMProviderError(Exception): ...


class RateLimitError(LLMProviderError): ...


class ProviderUnavailableError(LLMProviderError): ...


class StructuredOutputError(LLMProviderError):
    """Resposta do LLM não é JSON válido ou não conforma ao schema esperado."""
