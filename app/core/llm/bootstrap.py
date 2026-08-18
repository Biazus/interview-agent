from app.core.llm.fallback import FallbackLLMProvider


def build_default_llm_chain() -> FallbackLLMProvider:
    from app.core.llm.providers.groq_provider import GroqProvider
    from app.core.llm.providers.openrouter_provider import OpenRouterProvider

    return FallbackLLMProvider(
        [
            GroqProvider(),
            OpenRouterProvider(),
        ]
    )
