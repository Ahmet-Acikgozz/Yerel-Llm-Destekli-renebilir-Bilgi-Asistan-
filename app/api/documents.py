import os
import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends

from app.core.config import settings
from app.core.auth import require_admin
from app.services.document_parser import parser
from app.services.vector_store import vector_store
from app.schemas.schemas import DocumentUploadResponse

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".markdown"}

def _process_document(file_path: str, original_name: str, category: str = "genel") -> int:
    print(f"[Documents] Isleniyor: {original_name} (kategori: {category})")
    chunks = parser.parse(file_path, category=category)
    print(f"[Documents] {len(chunks)} chunk olusturuldu.")
    added = vector_store.add_chunks(chunks)
    print(f"[Documents] {added} chunk ChromaDB'ye eklendi.")
    return added

@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    summary="Doküman yükle [ADMIN]",
    description="Kurumsal doküman yükler ve bilgi tabanına ekler.",
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category: str = "genel",
    _admin: dict = Depends(require_admin),
):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Desteklenmeyen dosya formatı: '{suffix}'. İzin verilenler: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    os.makedirs(settings.upload_dir, exist_ok=True)
    save_path = os.path.join(settings.upload_dir, file.filename)
    
    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dosya kaydedilemedi: {str(e)}")
    finally:
        file.file.close()

    try:
        chunks_created = _process_document(save_path, file.filename, category=category)
    except Exception as e:
        if os.path.exists(save_path):
            os.remove(save_path)
        raise HTTPException(status_code=422, detail=f"Doküman işlenirken hata oluştu: {str(e)}")

    return DocumentUploadResponse(
        filename=file.filename,
        chunks_created=chunks_created,
        message=f"'{file.filename}' basariyla yuklendi ve {chunks_created} chunk olusturuldu.",
    )

@router.get("/stats")
async def get_stats():
    count = vector_store.count()
    return {
        "total_chunks": count,
        "message": f"Bilgi tabaninda toplam {count} chunk mevcut.",
    }
