import asyncio

from app.core.rag.qdrant_receiver import QdrantRetriever
from app.domains.async_messaging.rag_ingestion import ingest_seed_documents


async def main():
    print("--- Ingestão ---")
    ingest_seed_documents()

    print("\n--- Busca de teste ---")
    retriever = QdrantRetriever("async_messaging")

    queries = [
        "Onde é possivel armazenar mensagens que não puderam ser processadas com sucesso",
        "Existe redirecionamento automático entre uma DLQ ea fila original?",
        # "quero enviar um evento para vários sistemas diferentes ao mesmo tempo",
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        chunks = await retriever.retrieve(query, top_k=2)
        for chunk in chunks:
            print(f"  [{chunk.score:.3f}] ({chunk.topic}) {chunk.text[:80]}...")


if __name__ == "__main__":
    asyncio.run(main())
