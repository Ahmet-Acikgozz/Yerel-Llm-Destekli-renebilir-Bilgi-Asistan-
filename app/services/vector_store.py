"""
vector_store.py

ChromaDB ile etkileşimi yönetir.

İki temel işlem:
  1. add()    → Chunk'ları + embedding'leri ChromaDB'ye kaydet
  2. search() → Soruya en benzer chunk'ları bul

ChromaDB hakkında:
  - Dosya tabanlı çalışır (persist_dir klasörüne kaydeder)
  - Her kayıt: id + embedding (vektör) + document (metin) + metadata
  - Benzerlik ölçütü: cosine distance (0=aynı, 2=tamamen farklı)
"""

import uuid
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings
from app.services.embedding_service import embedding_service
from app.services.document_parser import DocumentChunk


class VectorStore:
    """
    ChromaDB işlemlerini saran yardımcı sınıf.
    """

    def __init__(self):
        # _client None başlar, ilk kullanımda oluşturulur
        self._client: chromadb.PersistentClient | None = None
        self._collection = None

    @property
    def collection(self):
        """
        ChromaDB client ve collection'ı lazy load eder.
        PersistentClient → verileri disk'e yazar, restart'ta kaybolmaz.
        """
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=settings.chroma_persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False),  # Veri gönderme
            )

        if self._collection is None:
            # get_or_create: collection yoksa oluştur, varsa getir
            self._collection = self._client.get_or_create_collection(
                name=settings.chroma_collection_name,
                # cosine: iki vektör arasındaki açı benzerliği
                # (normalize edilmiş vektörler için en iyi seçenek)
                metadata={"hnsw:space": "cosine"},
            )

        return self._collection

    # ─────────────────────────────────────────────
    # EKLEME
    # ─────────────────────────────────────────────

    def add_chunks(self, chunks: list[DocumentChunk]) -> int:
        """
        Chunk listesini embedding'e çevirip ChromaDB'ye ekler.

        Her kayıt için ChromaDB'ye şunlar gönderilir:
          - id        : Benzersiz kimlik (UUID)
          - embedding : Vektör (384 sayı)
          - document  : Ham metin (arama sonucunda gösterilir)
          - metadata  : Kaynak dosya, chunk index vs.

        Döndürür: Eklenen chunk sayısı
        """
        if not chunks:
            return 0

        # Tüm chunk metinlerini toplu embedding'e çevir (batch — daha hızlı)
        texts = [chunk.text for chunk in chunks]
        embeddings = embedding_service.embed_batch(texts)

        # ChromaDB için listeler hazırla
        ids = [str(uuid.uuid4()) for _ in chunks]          # Her chunk için benzersiz ID
        documents = texts                                    # Ham metinler
        metadatas = [chunk.metadata for chunk in chunks]   # Kaynak bilgileri

        # ChromaDB'ye toplu ekle
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        return len(chunks)

    def add_single_text(self, text: str, source: str, extra_metadata: dict = None) -> str:
        """
        Tek bir metin parçasını (yönetici cevabı gibi) ChromaDB'ye ekler.
        Gün 4'te admin cevap eklerken kullanacağız.

        Döndürür: Eklenen kaydın ID'si
        """
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

    # ─────────────────────────────────────────────
    # ARAMA
    # ─────────────────────────────────────────────

    def search(
        self,
        query: str,
        n_results: int = 10,
        source_filter: str | None = None,
    ) -> list[dict]:
        """
        Soruya en benzer chunk'ları bulur.

        2. Hafta değişikliği:
          - n_results default 10 (re-ranker geniş ağ kullanır)
          - source_filter: sadece belirtilen dokümanda ara
            ör: source_filter='ik_rehberi.pdf'

        Döndürür:
          - text      : Bulunan chunk'ın metni
          - source    : Kaynak dosya adı
          - metadata  : Tüm metadata (category, upload_date vs.)
          - score     : Benzerlik skoru (0-1)
        """
        if self.collection.count() == 0:
            return []

        query_embedding = embedding_service.embed_text(query)

        # Metadata filtresi (isteğe bağlı)
        where_filter = None
        if source_filter:
            where_filter = {"source": {"$eq": source_filter}}

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, self.collection.count()),
            include=["documents", "metadatas", "distances"],
            where=where_filter,
        )

        output = []
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for doc, meta, dist in zip(documents, metadatas, distances):
            output.append({
                "text": doc,
                "source": meta.get("source", "bilinmiyor"),
                "metadata": meta,
                "distance": round(dist, 4),
                "score": round(max(0.0, 1.0 - dist), 4),
            })

        return output

    def list_sources(self) -> list[dict]:
        """
        ChromaDB'deki tüm kaynak dokümanları ve istatistiklerini listeler.
        Metadata filtre için hangi kaynak adları kullanılabileceğini gösterir.
        """
        if self.collection.count() == 0:
            return []

        all_data = self.collection.get(include=["metadatas"])
        source_stats: dict[str, dict] = {}

        for meta in all_data["metadatas"]:
            src = meta.get("source", "bilinmiyor")
            if src not in source_stats:
                source_stats[src] = {
                    "source": src,
                    "chunk_count": 0,
                    "category": meta.get("category", "genel"),
                    "upload_date": meta.get("upload_date", "-"),
                }
            source_stats[src]["chunk_count"] += 1

        return list(source_stats.values())

    # ─────────────────────────────────────────────
    # BİLGİ
    # ─────────────────────────────────────────────

    def count(self) -> int:
        """ChromaDB'deki toplam kayıt sayısını döndürür."""
        return self.collection.count()

    def reset(self) -> None:
        """
        Tüm ChromaDB verilerini siler. SADECE GELİŞTİRME AŞAMASINDA KULLAN!
        Production'da çok dikkatli ol.
        """
        self._client.delete_collection(settings.chroma_collection_name)
        self._collection = None


# ─────────────────────────────────────────────
# Global singleton instance
# ─────────────────────────────────────────────
vector_store = VectorStore()
