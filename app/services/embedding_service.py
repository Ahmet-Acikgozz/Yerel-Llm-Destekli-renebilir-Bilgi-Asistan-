from sentence_transformers import SentenceTransformer
from app.core.config import settings

class EmbeddingService:
    def __init__(self):

        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            print("[Embedding] Model yukleniyor: paraphrase-multilingual-MiniLM-L12-v2 ...")
            print("[Embedding] Ilk yuklemede ~470MB indirilecek, lutfen bekleyin...")

            self._model = SentenceTransformer(
                "paraphrase-multilingual-MiniLM-L12-v2",
                device="cpu",
            )
            print("[Embedding] Model hazir. Turkce destegi aktif.")
        return self._model

    def embed_text(self, text: str) -> list[float]:

        vector = self.model.encode(
            text,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vector.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 10,
            batch_size=32,
        )
        return vectors.tolist()

embedding_service = EmbeddingService()
