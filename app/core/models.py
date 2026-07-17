from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import String, Text, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class QuestionStatus(str, PyEnum):
    """Bekleyen soruların durumu"""
    PENDING = "Bekliyor"
    ANSWERED = "Cevaplandı"


class PendingQuestion(Base):
    """
    Bilgi tabanında karşılığı bulunamayan soruları saklar.
    Yönetici bu tabloyu inceleyip cevap ekleyebilir.
    """
    __tablename__ = "pending_questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Kullanıcının sorduğu soru
    question: Mapped[str] = mapped_column(Text, nullable=False)

    # Soruyu soran kullanıcı (opsiyonel, şimdilik string)
    asked_by: Mapped[str] = mapped_column(String(100), nullable=False, default="anonymous")

    # Soru tarihi
    asked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Durum: Bekliyor / Cevaplandı
    status: Mapped[QuestionStatus] = mapped_column(
        Enum(QuestionStatus),
        default=QuestionStatus.PENDING,
        nullable=False,
    )

    # Yöneticinin eklediği cevap (cevaplandıktan sonra dolar)
    admin_answer: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Cevap tarihi
    answered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<PendingQuestion id={self.id} status={self.status} question='{self.question[:50]}'>"
