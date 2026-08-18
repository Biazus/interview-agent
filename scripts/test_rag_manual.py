import asyncio

from app.core.rag.factory import get_qdrant_retriever
from app.domains.async_messaging.rag_ingestion import ingest_seed_documents


async def main():
    print("--- Ingestão ---")
    ingest_seed_documents()

    print("\n--- Busca de teste ---")
    retriever = get_qdrant_retriever("async_messaging")

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
