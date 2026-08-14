import asyncio

from app.core.llm.providers.groq_provider import GroqProvider


async def main():
    provider = GroqProvider()
    response = await provider.generate("Explique o que é uma DLQ em uma frase.")
    print(f"Provider: {response.provider}")
    print(f"Model: {response.model}")
    print(f"Tokens: {response.tokens_used}")
    print(f"Texto: {response.text}")


if __name__ == "__main__":
    asyncio.run(main())