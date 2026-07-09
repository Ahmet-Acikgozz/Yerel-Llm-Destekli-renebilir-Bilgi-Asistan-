import uuid
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings
from app.services.embedding_service import embedding_service
from app.services.document_parser import DocumentChunk

class VectorStore:
    def __init__(self):

        self._client: chromadb.PersistentClient | None = None
        self._collection = None

    @property
    def collection(self):
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=settings.chroma_persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False),
            )

        if self._collection is None:

            self._collection = self._client.get_or_create_collection(
                name=settings.chroma_collection_name,
                metadata={"hnsw:space": "cosine"},
            )

        return self._collection

    def add_chunks(self, chunks: list[DocumentChunk]) -> int:
        if not chunks:
            return 0

        texts = [chunk.text for chunk in chunks]
        embeddings = embedding_service.embed_batch(texts)

        ids = [str(uuid.uuid4()) for _ in chunks]
        documents = texts
        metadatas = [chunk.metadata for chunk in chunks]

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        return len(chunks)

    def add_single_text(self, text: str, source: str, extra_metadata: dict = None) -> str:
        embedding = embedding_service.embed_text(text)
        record_id = str(uuid.uuid4())

        metadata = {"source": source, "chunk_index": 0}
        if extra_metadata:
            metadata.update(extra_metadata)

        self.collection.add(
            ids=[record_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
        )

        return record_id

    def search(
        self, query: str, n_results: int = 3
    ) -> list[dict]:

        if self.collection.count() == 0:
            return []

        query_embedding = embedding_service.embed_text(query)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, self.collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        output = []
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for doc, meta, dist in zip(documents, metadatas, distances):
            output.append({
                "text": doc,
                "source": meta.get("source", "bilinmiyor"),
                "distance": round(dist, 4),
                "score": round(max(0.0, 1.0 - dist), 4),
            })

        return output

    def count(self) -> int:
        return self.collection.count()

    def reset(self) -> None:
        self._client.delete_collection(settings.chroma_collection_name)
        self._collection = None

# Global singleton instance
vector_store = VectorStore()
