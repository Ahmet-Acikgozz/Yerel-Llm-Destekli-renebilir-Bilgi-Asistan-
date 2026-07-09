from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.models import PendingQuestion, QuestionStatus
from app.services.vector_store import vector_store
from app.services.llm_service import llm_service

class RAGService:
    async def answer(
        self,
        question: str,
        user: str,
        db: AsyncSession,
        n_results: int = 3,
    ) -> dict:
        search_results = vector_store.search(question, n_results=n_results)

        best_score = search_results[0]["score"] if search_results else 0.0

        if best_score < settings.confidence_threshold:

            await self._save_pending_question(question, user, db)
            return {
                "question": question,
                "answer": "Bu konu hakkinda bilgi tabaninda yeterli bilgi bulunamadi. "
                          "Sorunuz yonetici incelemesine alindi.",
                "confidence_score": round(best_score, 4),
                "sources": [],
                "answered": False,
            }

        good_chunks = [
            r["text"]
            for r in search_results
            if r["score"] >= settings.confidence_threshold
        ]
        

        source_texts = [
            r["text"][:200] + "..."
            for r in search_results
            if r["score"] >= settings.confidence_threshold
        ]

        llm_result = await llm_service.generate(
            question=question,
            context_chunks=good_chunks,
        )

        if not llm_result["found"]:
            await self._save_pending_question(question, user, db)
            return {
                "question": question,
                "answer": "Bu konu hakkinda bilgi tabaninda yeterli bilgi bulunamadi. "
                          "Sorunuz yonetici incelemesine alindi.",
                "confidence_score": round(best_score, 4),
                "sources": [],
                "answered": False,
            }

        return {
            "question": question,
            "answer": llm_result["answer"],
            "confidence_score": round(best_score, 4),
            "sources": source_texts,
            "answered": True,
        }

    async def _save_pending_question(
        self, question: str, user: str, db: AsyncSession
    ) -> None:

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
        print(f"[RAG] Bekleyen soru kaydedildi: '{question[:60]}...'")

# Global singleton instance
rag_service = RAGService()
