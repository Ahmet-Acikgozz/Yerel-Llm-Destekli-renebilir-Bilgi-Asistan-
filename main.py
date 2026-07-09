import os
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[BASLANGIC] SoSmart Bilgi Asistani baslatiliyor...")

    os.makedirs("./data/chroma_db", exist_ok=True)
    os.makedirs("./data/uploads", exist_ok=True)

    await init_db()
    print("[OK] Veritabani hazir.")

    yield

    print("[KAPANIS] Uygulama kapatiliyor...")

# FastAPI uygulaması
app = FastAPI(
    title="SoSmart Bilgi Asistanı",
    description="""
## 🧠 Yerel LLM Destekli Kurumsal Bilgi Asistanı

Bu sistem, kurumsal dokümanlardan öğrenen ve yerel LLM ile çalışan bir bilgi asistanıdır.

### Özellikler
- 📄 **Doküman Yükleme**: PDF, DOCX, TXT, Markdown desteği
- 🔍 **Akıllı Sorgulama**: RAG mimarisi ile bağlam tabanlı cevap üretimi
- ❓ **Bilinmeyen Sorular**: Cevap bulunamazsa yönetici incelemesine alınır
- 🎓 **Eğitim Modülü**: Yönetici cevap ekleyerek sistemi eğitebilir
    """,
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Router'lari bagla
from app.api import query, documents, knowledge, admin

app.include_router(query.router, prefix="/query", tags=["Sorgulama (RAG)"])
app.include_router(documents.router, prefix="/documents", tags=["Doküman Yönetimi"])
app.include_router(knowledge.router, prefix="/knowledge", tags=["Manuel Bilgi Girişi"])
app.include_router(admin.router, prefix="/admin", tags=["Yönetici İşlemleri"])

@app.get("/health", tags=["Genel"])
async def health_check():
    """Sistemin çalışıp çalışmadığını ve Ollama bağlantısını kontrol eder."""
    from app.core.config import settings

    ollama_status = "bağlı değil"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            if resp.status_code == 200:
                ollama_status = f"✅ bağlı ({settings.ollama_model})"
    except Exception:
        ollama_status = "❌ bağlantı kurulamadı — Ollama çalışıyor mu?"

    return {
        "status": "✅ çalışıyor",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "ollama": ollama_status,
        "docs": "http://localhost:8000/docs",
    }
