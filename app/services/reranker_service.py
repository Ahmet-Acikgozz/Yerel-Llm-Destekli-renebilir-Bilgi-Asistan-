"""
reranker_service.py  (2. Hafta — Modül 1)

ChromaDB'den dönen ham arama sonuçlarını Cross-Encoder modeli ile yeniden sıralar.

Neden re-ranking?
  Embedding modeli "genel benzerlik" ölçer.
  Cross-Encoder ise soruyu ve belgeyi birlikte okuyarak
  "Bu belge gerçekten bu soruya cevap veriyor mu?" diye sorar.
  Bu sayede alakasız ama "benzer görünen" metinler elenmiş olur.

Model: cross-encoder/ms-marco-MiniLM-L-6-v2
  - Hızlı (küçük), CPU'da çalışır
  - Türkçe metinlerde yeterince iyi performans
  - Boyut: ~100MB
"""

from sentence_transformers import CrossEncoder


class RerankerService:
    """
    Cross-Encoder tabanlı yeniden sıralama servisi.

    Kullanım akışı:
      1. ChromaDB → ilk 10 sonuç (geniş ağ)
      2. RerankerService.rerank() → en iyi 3-4 sonuç (hassas eleme)
      3. LLM'e sadece bu 3-4 sonucu gönder
    """

    MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    # Re-ranking eşiği: bu skorun altındaki sonuçlar LLM'e gönderilmez
    RERANK_THRESHOLD = 0.0  # Cross-encoder -inf..+inf skor üretir, normalize edilecek

    def __init__(self):
        self._model: CrossEncoder | None = None

    @property
    def model(self) -> CrossEncoder:
        """Modeli lazy load eder — ilk çağrıda yükler."""
        if self._model is None:
            print(f"[Reranker] Model yukleniyor: {self.MODEL_NAME} ...")
            self._model = CrossEncoder(self.MODEL_NAME, max_length=512)
            print("[Reranker] Model hazir.")
        return self._model

    def rerank(
        self,
        query: str,
        candidates: list[dict],
        top_k: int = 4,
    ) -> list[dict]:
        """
        Aday chunk'ları Cross-Encoder ile yeniden sıralar.

        Parametreler:
          query      : Kullanıcının orijinal sorusu
          candidates : vector_store.search() çıktısı
                       [{"text": "...", "score": 0.82, "source": "..."}]
          top_k      : En iyi kaç sonuç döndürülsün

        Döndürür:
          Yeniden sıralanmış, normalize edilmiş skor ile zenginleştirilmiş liste.
          [{"text": "...", "score": 0.82, "rerank_score": 0.91, "source": "..."}]
        """
        if not candidates:
            return []

        # Cross-encoder için (soru, belge) çiftleri oluştur
        pairs = [(query, c["text"]) for c in candidates]

        # Skorları hesapla
        raw_scores = self.model.predict(pairs)

        # Normalize et: sigmoid ile 0-1 aralığına taşı
        import math
        def sigmoid(x):
            return 1.0 / (1.0 + math.exp(-x))

        normalized = [sigmoid(float(s)) for s in raw_scores]

        # Orijinal sonuçlara rerank_score ekle
        enriched = []
        for candidate, norm_score in zip(candidates, normalized):
            enriched.append({
                **candidate,
                "rerank_score": round(norm_score, 4),
            })

        # Yeniden sırala (yüksek rerank_score önce)
        enriched.sort(key=lambda x: x["rerank_score"], reverse=True)

        # Sadece top_k kadar döndür
        return enriched[:top_k]


# Global singleton
reranker_service = RerankerService()
