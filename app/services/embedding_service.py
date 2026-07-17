"""
embedding_service.py

Metni sayı dizisine (vektöre) dönüştürür.
ChromaDB'ye kaydetmeden önce ve sorgulama sırasında kullanılır.

Model: paraphrase-multilingual-MiniLM-L12-v2
  - Boyut: 384 sayı (all-MiniLM-L6-v2 ile ayni, ChromaDB uyumlu)
  - Dil: 50+ dil destegi, Turkce icin optimize
  - Boyut: ~470MB
  - Avantaj: Turkce'de anlam benzerligi cok daha iyi
  - Ornek: 'Bugun gundayiz?' ve 'Hangi gun?' ayni anlama geliyor
"""

from sentence_transformers import SentenceTransformer
from app.core.config import settings


class EmbeddingService:
    """
    sentence-transformers kütüphanesini kullanarak metin → vektör dönüşümü yapar.

    Singleton pattern kullandık: model bir kez yüklenir, her çağrıda tekrar yüklenmez.
    Neden? Model yükleme ~2-3 saniye sürer, her istekte bunu yapmak çok yavaş olurdu.
    """

    def __init__(self):
        # _model None başlar, ilk kullanımda yüklenir (lazy loading)
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        """
        Modeli lazy load eder.
        İlk çağrıda indirir/yükler, sonraki çağrılarda cache'den döner.
        """
        if self._model is None:
            print("[Embedding] Model yukleniyor: paraphrase-multilingual-MiniLM-L12-v2 ...")
            print("[Embedding] Ilk yuklemede ~470MB indirilecek, lutfen bekleyin...")
            # normalize_embeddings=True vektör uzunluğunu 1'e normalize eder
            # Bu, cosine similarity hesabını daha doğru yapar
            self._model = SentenceTransformer(
                "paraphrase-multilingual-MiniLM-L12-v2",
                device="cpu",
            )
            print("[Embedding] Model hazir. Turkce destegi aktif.")
        return self._model

    def embed_text(self, text: str) -> list[float]:
        """
        Tek bir metni vektöre çevirir.
        Kullanım: Soru geldiğinde soruyu embed etmek için.

        Örnek:
            embed_text("Numune nasıl teslim edilir?")
            → [0.23, -0.45, 0.78, ...] (384 sayı)
        """
        # encode() → numpy array döndürür, .tolist() ile Python list'e çevir
        vector = self.model.encode(
            text,
            normalize_embeddings=True,  # Uzunluğu normalize et
            show_progress_bar=False,
        )
        return vector.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Birden fazla metni aynı anda vektöre çevirir.
        Kullanım: Doküman yüklerken tüm chunk'ları toplu işlemek için.

        Neden batch? Tek tek göndermekten 5-10x daha hızlı.
        Model, birden fazla metni paralel işleyebilir.

        Örnek:
            embed_batch(["Metin 1", "Metin 2", "Metin 3"])
            → [[0.23, ...], [0.45, ...], [0.67, ...]]
        """
        vectors = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 10,  # 10'dan fazlaysa ilerleme göster
            batch_size=32,  # Bellekte aynı anda 32 metin işle
        )
        return vectors.tolist()


# ─────────────────────────────────────────────
# Global singleton instance
# ─────────────────────────────────────────────
# Bu nesne uygulama boyunca tek bir kez oluşturulur.
# Her modül bunu import edip kullanır.
embedding_service = EmbeddingService()
