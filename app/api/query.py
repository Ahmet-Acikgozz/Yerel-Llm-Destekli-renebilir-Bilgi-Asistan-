"""
query.py — Soru-Cevap API  (2. Hafta)

POST /query/      → RAG + Re-ranking pipeline
GET  /query/sources → Bilgi tabanındaki doküman listesi (filtre için)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.schemas import QueryRequest, QueryResponse
from app.services.rag_service import rag_service
from app.services.vector_store import vector_store

router = APIRouter()


@router.post(
    "/",
    response_model=QueryResponse,
    summary="Soru sor (RAG + Re-ranking)",
    description="""
Bilgi tabanında arama yaparak soruyu cevaplar.

**2. Hafta Güncellemesi — İki Aşamalı Arama:**
1. Soru vektöre dönüştürülür
2. ChromaDB'de en benzer **10** içerik aranır (geniş ağ)
3. Cross-Encoder Re-ranker ile **yeniden sıralanır**
4. En iyi 4 sonuç LLM'e gönderilir
5. Re-rank skoru < 0.30 → LLM'e gitmeden "Bulunamadı" döner

**`source_filter` (opsiyonel):**
- Sadece belirli bir dokümanda arama yapar
- Önce `/query/sources` ile mevcut doküman adlarını öğren
- Örnek: `"source_filter": "ik_rehberi.pdf"`
    """,
)
async def query_knowledge(
    body: QueryRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await rag_service.answer(
        question=body.question,
        user=body.user,
        db=db,
        source_filter=body.source_filter,
    )
    return QueryResponse(**result)


@router.get(
    "/sources",
    summary="Bilgi tabanındaki dokümanları listele",
    description="""
ChromaDB'ye yüklenmiş tüm dokümanları ve istatistiklerini listeler.

`source_filter` parametresi için kullanılabilecek doküman adlarını gösterir.
    """,
)
async def list_sources():
    """Mevcut kaynak dokümanların listesi."""
    sources = vector_store.list_sources()
    return {
        "toplam_kaynak": len(sources),
        "kaynaklar": sources,
    }
