from fastapi import APIRouter, HTTPException
from app.schemas.schemas import KnowledgeAddRequest, KnowledgeAddResponse
from app.services.document_parser import DocumentParser
from app.services.vector_store import vector_store

router = APIRouter()

@router.post(
    "/add",
    response_model=KnowledgeAddResponse,
    summary="Manuel bilgi ekle",
)
async def add_knowledge(body: KnowledgeAddRequest):
    full_text = f"{body.title}\n\n{body.content}"

    if len(full_text) > 500:
        temp_parser = DocumentParser(chunk_size=800, chunk_overlap=100)
        chunks = temp_parser._split_into_chunks(full_text, source=body.source)

        if not chunks:
            raise HTTPException(
                status_code=422,
                detail="Metin chunk'lara bolunemedi. Daha uzun bir icerik girin."
            )
        added = vector_store.add_chunks(chunks)
    else:
        vector_store.add_single_text(
            text=full_text,
            source=body.source,
            extra_metadata={"title": body.title},
        )
        added = 1

    return KnowledgeAddResponse(
        title=body.title,
        chunks_created=added,
        message=f"'{body.title}' basligiyla {added} bilgi parcasi eklendi.",
    )

@router.delete("/reset", summary="Bilgi tabanını sıfırla")
async def reset_knowledge_base():
    try:
        vector_store.reset()
        return {"message": "Bilgi tabani sifirlandi. Tum chunk'lar silindi."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sifirlama hatasi: {str(e)}")
