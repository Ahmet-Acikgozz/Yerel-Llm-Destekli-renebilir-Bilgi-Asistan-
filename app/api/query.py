"""
query.py — Soru-Cevap API

POST /query/
  - Kullanıcının sorusunu alır
  - RAG pipeline'ından geçirir
  - Cevabı (veya "bilgi bulunamadı") döndürür
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.schemas import QueryRequest, QueryResponse
from app.services.rag_service import rag_service

router = APIRouter()


@router.post(
    "/",
    response_model=QueryResponse,
    summary="Soru sor",
    description="""
Bilgi tabanında arama yaparak soruyu cevaplar.

**Çalışma mantığı:**
1. Soru vektöre dönüştürülür
2. ChromaDB'de en benzer içerikler aranır
3. Güven skoru hesaplanır (0.0 - 1.0)
4. Güven skoru ≥ 0.5 → LLM cevap üretir
5. Güven skoru < 0.5 → "Bilgi bulunamadı" + soruyu yöneticiye ilet

**`answered` alanı:**
- `true` → Cevap bulundu
- `false` → Bilgi tabanında yeterli bilgi yok, soru yöneticiye iletildi
    """,
)
async def query_knowledge(
    body: QueryRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Ana soru-cevap endpoint'i.

    Depends(get_db) nedir?
      FastAPI'nin dependency injection sistemi.
      Her istekte otomatik olarak DB session oluşturur,
      istek bitince kapatır. Biz elle yönetmek zorunda kalmayız.
    """
    result = await rag_service.answer(
        question=body.question,
        user=body.user,
        db=db,
    )

    return QueryResponse(**result)
