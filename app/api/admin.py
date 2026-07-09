from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.models import PendingQuestion, QuestionStatus
from app.schemas.schemas import PendingQuestionOut, AnswerRequest, AnswerResponse
from app.services.vector_store import vector_store

router = APIRouter()

@router.get(
    "/pending-questions",
    response_model=list[PendingQuestionOut],
    summary="Bekleyen soruları listele",
)
async def list_pending_questions(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(PendingQuestion).order_by(PendingQuestion.asked_at.desc())
    if status == "Bekliyor":
        query = query.where(PendingQuestion.status == QuestionStatus.PENDING)
    elif status == "Cevaplandi":
        query = query.where(PendingQuestion.status == QuestionStatus.ANSWERED)

    result = await db.execute(query)
    return result.scalars().all()

@router.post(
    "/answer/{question_id}",
    response_model=AnswerResponse,
    summary="Bekleyen soruya cevap ver",
)
async def answer_question(
    question_id: int,
    body: AnswerRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PendingQuestion).where(PendingQuestion.id == question_id))
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(status_code=404, detail=f"ID={question_id} olan soru bulunamadi.")
    if question.status == QuestionStatus.ANSWERED:
        raise HTTPException(status_code=400, detail=f"Bu soru zaten cevaplandı (ID={question_id}).")

    knowledge_text = f"Soru: {question.question}\nCevap: {body.answer}"

    record_id = vector_store.add_single_text(
        text=knowledge_text,
        source="admin_cevap",
        extra_metadata={
            "question_id": question_id,
            "original_question": question.question,
            "answered_by": "admin",
        },
    )

    question.status = QuestionStatus.ANSWERED
    question.admin_answer = body.answer
    question.answered_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(question)

    return AnswerResponse(
        question_id=question_id,
        question=question.question,
        answer=body.answer,
        chunks_created=1,
        message="Cevap bilgi tabanina eklendi."
    )

@router.get("/stats", summary="Sistem istatistikleri")
async def get_stats(db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count(PendingQuestion.id)))).scalar()
    pending = (await db.execute(select(func.count(PendingQuestion.id)).where(PendingQuestion.status == QuestionStatus.PENDING))).scalar()
    answered = (await db.execute(select(func.count(PendingQuestion.id)).where(PendingQuestion.status == QuestionStatus.ANSWERED))).scalar()
    kb_count = vector_store.count()

    return {
        "bilgi_tabani": {"toplam_chunk": kb_count},
        "sorular": {"toplam": total, "bekleyen": pending, "cevaplanan": answered},
        "ozet": f"{kb_count} bilgi parcasi mevcut. {pending} soru bekliyor.",
    }

@router.delete("/reset-all", summary="TUM SISTEMI SIFIRLA")
async def reset_all_data(db: AsyncSession = Depends(get_db)):
    try:
        vector_store.reset()
        from sqlalchemy import delete
        await db.execute(delete(PendingQuestion))
        await db.commit()
        return {"message": "Sistem tamamen sifirlandi! ChromaDB ve bekleyen sorular silindi."}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Sifirlama hatasi: {str(e)}")

@router.get("/knowledge-base", summary="Bilgi tabanı kayitlarini goruntule")
async def browse_knowledge_base(limit: int = 50):
    count = vector_store.count()
    if count == 0:
        return {"toplam": 0, "kayitlar": [], "mesaj": "Bilgi tabani bos."}

    gercek_limit = min(limit, count)
    sonuclar = vector_store.collection.get(include=["documents", "metadatas"], limit=gercek_limit)

    kayitlar = []
    for rid, metin, meta in zip(sonuclar["ids"], sonuclar["documents"], sonuclar["metadatas"]):
        kayitlar.append({
            "id": rid[:8] + "...",
            "source": meta.get("source", "bilinmiyor"),
            "chunk_index": meta.get("chunk_index", 0),
            "preview": metin[:200] + ("..." if len(metin) > 200 else ""),
            "karakter_sayisi": len(metin),
        })

    return {"toplam_kayit": count, "gosterilen": gercek_limit, "kayitlar": kayitlar}
