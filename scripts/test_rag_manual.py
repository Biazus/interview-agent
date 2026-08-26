import asyncio

import app.bootstrap  # noqa: F401 — registers domains on import

from app.core.domain.registry import DomainEnum, get_domain_rag_config
from app.core.rag.factory import get_qdrant_retriever
from app.core.rag.seed_ingestion import ingest_domain_seed


async def main():
    config = get_domain_rag_config(DomainEnum.ASYNC_MESSAGING)

    print("--- Ingestão ---")
    ingest_domain_seed(config)

    print("\n--- Busca de teste ---")
    retriever = get_qdrant_retriever(config.collection_name)

    queries = [
        "Uma Dead Letter Queue (DLQ) no Amazon SQS é uma fila usada por outras filas (as filas de origem) para armazenar mensagens que não puderam ser processadas com sucesso",
        "Existe redirecionamento automático entre uma DLQ ea fila original?",
        # "quero enviar um evento para vários sistemas diferentes ao mesmo tempo",
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        chunks = retriever.retrieve(query, top_k=2)
        for chunk in chunks:
            print(f"  [{chunk.score:.3f}] ({chunk.topic}) {chunk.text}...")


if __name__ == "__main__":
    asyncio.run(main())
