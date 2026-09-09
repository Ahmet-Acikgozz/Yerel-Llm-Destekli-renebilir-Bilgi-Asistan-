"""
rag_service.py  (2. Hafta — Modül 1)

1. Hafta: ChromaDB → top-3 → LLM
2. Hafta: ChromaDB → top-10 → Re-ranker → top-4 → LLM
           Threshold: rerank_score < 0.30 → direkt "Bulunamadı"
           Metadata filtre: sadece belirli dokümanda arama

Adımlar:
  1. Soruyu embedding'e çevir
  2. ChromaDB'de n_results=10 ile geniş arama yap (metadata filtreli)
  3. Re-ranker ile yeniden sırala → top 4
  4. En iyi rerank_score < RERANK_THRESHOLD → LLM'e gitme, "Bulunamadı"
  5. LLM'e sadece top-4 chunk'ı gönder
  6. LLM "found: false" dönerse → pending'e kaydet
"""

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.models import PendingQuestion, QuestionStatus
from app.services.vector_store import vector_store
from app.services.llm_service import llm_service
from app.services.reranker_service import reranker_service


class RAGService:
    """
    2. Hafta RAG Pipeline:
      Embedding arama + Cross-Encoder re-ranking + LLM
    """

    # Re-ranking sonrası bu eşiğin altındaki sonuçlar LLM'e gönderilmez
    # Not: Admin cevapları Q&A formatında saklandığından Cross-Encoder düşük skor
    # verebilir. 0.10 hem kalite kontrolünü korur hem de admin cevaplarını geçirir.
    RERANK_THRESHOLD: float = 0.10

    async def answer(
        self,
        question: str,
        user: str,
        db: AsyncSession,
        n_results: int = 10,
        source_filter: str | None = None,
    ) -> dict:
        """
        Soruyu tam RAG+ReRank pipeline'ından geçirir.

        Parametreler:
          question      : Kullanıcının sorusu
          user          : Soruyu soran kullanıcı adı
          db            : SQLAlchemy async session
          n_results     : ChromaDB'den kaç sonuç çekilsin (geniş ağ: 10)
          source_filter : Sadece bu dokümanda ara (ör: "ik_rehberi.pdf")
        """

        # ── ADIM 1: ChromaDB'de geniş arama ──
        search_results = vector_store.search(
            query=question,
            n_results=n_results,
            source_filter=source_filter,
        )

        if not search_results:
            await self._save_pending_question(question, user, db)
            return self._not_found_response(question, 0.0)

        # ── ADIM 2: Re-ranking ile yeniden sırala ──
        reranked = reranker_service.rerank(
            query=question,
            candidates=search_results,
            top_k=4,
        )

        best_rerank_score = reranked[0]["rerank_score"] if reranked else 0.0
        best_embed_score = reranked[0]["score"] if reranked else 0.0

        # ── ADIM 3: Re-rank eşiği kontrolü ──
        if best_rerank_score < self.RERANK_THRESHOLD:
            await self._save_pending_question(question, user, db)
            return self._not_found_response(question, best_embed_score)

        # ── ADIM 4: LLM için bağlamı hazırla ──
        good_chunks = [r["text"] for r in reranked]
        source_texts = [
            f"[{r['source']}] {r['text'][:200]}..."
            for r in reranked
        ]

        # ── ADIM 5: LLM'den cevap al ──
        llm_result = await llm_service.generate(
            question=question,
            context_chunks=good_chunks,
        )

        # ── ADIM 6: LLM cevap bulamadıysa kaydet ──
        if not llm_result["found"]:
            await self._save_pending_question(question, user, db)
            return self._not_found_response(question, best_embed_score)

        # ── ADIM 7: Eğer bu soru daha önce bekleyen sorular listesindeyse, otomatik cevaplandı yap ──
        await self._resolve_pending_question(question, llm_result["answer"], db)

        # ── ADIM 8: Başarılı cevap döndür ──
        return {
            "question": question,
            "answer": llm_result["answer"],
            "confidence_score": round(best_embed_score, 4),
            "rerank_score": round(best_rerank_score, 4),
            "sources": source_texts,
            "answered": True,
        }

    def _not_found_response(self, question: str, score: float) -> dict:
        return {
            "question": question,
            "answer": (
                "Bu konu hakkinda bilgi tabaninda yeterli bilgi bulunamadi. "
                "Sorunuz yonetici incelemesine alindi."
            ),
            "confidence_score": round(score, 4),
            "rerank_score": 0.0,
            "sources": [],
            "answered": False,
        }

    async def _resolve_pending_question(
        self, question: str, answer: str, db: AsyncSession
    ) -> None:
        """Eğer bu soru önceden PENDING olarak kayıtlıysa, otomatik olarak ANSWERED yapar."""
        from sqlalchemy import select, update
        stmt = (
            update(PendingQuestion)
            .where(
                PendingQuestion.question == question,
                PendingQuestion.status == QuestionStatus.PENDING,
            )
            .values(
                status=QuestionStatus.ANSWERED,
                admin_answer=f"[Doküman/RAG]: {answer[:200]}",
                answered_at=datetime.now(timezone.utc),
            )
        )
        res = await db.execute(stmt)
        if res.rowcount > 0:
            await db.commit()
            print(f"[RAG] Bekleyen soru dokuman/otomatik ile cevaplandi olarak isaretlendi: '{question[:60]}'")

    async def _save_pending_question(
        self, question: str, user: str, db: AsyncSession
    ) -> None:
        """Cevaplanamayan soruyu SQLite'a kaydeder."""
        from sqlalchemy import select
        existing = await db.execute(
            select(PendingQuestion).where(
                PendingQuestion.question == question,
                PendingQuestion.status == QuestionStatus.PENDING,
            )
        )
        if existing.scalar_one_or_none():
            return

        pending = PendingQuestion(
            question=question,
            asked_by=user,
            asked_at=datetime.now(timezone.utc),
            status=QuestionStatus.PENDING,
        )
        db.add(pending)
        await db.commit()
        print(f"[RAG] Bekleyen soru kaydedildi: '{question[:60]}'")


rag_service = RAGService()
