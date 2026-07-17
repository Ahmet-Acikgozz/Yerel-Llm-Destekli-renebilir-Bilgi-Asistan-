from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.core.models import QuestionStatus

# QUERY (Soru Sorma)

class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Kullanıcının sorusu",
        examples=["Laboratuvar numunesi nasıl teslim edilir?"],
    )
    user: str = Field(
        default="anonymous",
        max_length=100,
        description="Soruyu soran kullanıcı adı",
    )
    source_filter: Optional[str] = Field(
        default=None,
        description="Sadece bu dokümanda ara (ör: 'ik_rehberi.pdf')",
    )

class QueryResponse(BaseModel):
    question: str
    answer: str
    confidence_score: float = Field(description="Embedding benzerlik skoru (0-1)")
    rerank_score: float = Field(default=0.0, description="Cross-Encoder re-rank skoru (0-1)")
    sources: list[str] = Field(default=[], description="Cevabın dayandığı kaynak chunk'lar")
    answered: bool = Field(description="True = cevap bulundu, False = bilgi bulunamadı")

# DOCUMENT (Doküman Yükleme)

class DocumentUploadResponse(BaseModel):
    filename: str
    chunks_created: int
    message: str

# KNOWLEDGE (Manuel Bilgi Ekleme)

class KnowledgeAddRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=200, description="Bilgi başlığı")
    content: str = Field(..., min_length=10, description="Eklenecek bilgi içeriği")
    source: str = Field(default="manuel_giris", description="Kaynak etiketi")

class KnowledgeAddResponse(BaseModel):
    title: str
    chunks_created: int
    message: str

# ADMIN (Yönetici İşlemleri)

class PendingQuestionOut(BaseModel):
    id: int
    question: str
    asked_by: str
    asked_at: datetime
    status: QuestionStatus
    admin_answer: Optional[str] = None
    answered_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class AnswerRequest(BaseModel):
    answer: str = Field(
        ...,
        min_length=5,
        description="Soruya verilecek cevap",
        examples=["Numuneler barkod okutulduktan sonra Laboratuvar Kabul Birimine teslim edilir."],
    )

class AnswerResponse(BaseModel):
    question_id: int
    question: str
    answer: str
    chunks_created: int
    message: str

# HEALTH CHECK

class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    ollama_status: str
    knowledge_base_count: int
