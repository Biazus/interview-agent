import asyncio

from app.core.llm.providers.openrouter_provider import OpenRouterProvider


async def main():
    provider = OpenRouterProvider()
    response = await provider.generate(
        "Explique o que é uma Kafka partition em uma frase."
    )
    print(f"Provider: {response.provider}")
    print(f"Model: {response.model}")
    print(f"Tokens: {response.tokens_used}")
    print(f"Texto: {response.text}")


if __name__ == "__main__":
    asyncio.run(main())
