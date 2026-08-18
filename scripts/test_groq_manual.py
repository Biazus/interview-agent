import asyncio

from app.core.llm.providers.groq_provider import GroqProvider
from app.core.llm.requests import GenerateRequest


async def main():
    provider = GroqProvider()
    response = await provider.generate(
        GenerateRequest.simple("Explique o que é uma DLQ em uma frase.")
    )
    print(f"Provider: {response.provider}")
    print(f"Model: {response.model}")
    print(f"Tokens: {response.tokens_used}")
    print(f"Texto: {response.text}")


if __name__ == "__main__":
    asyncio.run(main())
