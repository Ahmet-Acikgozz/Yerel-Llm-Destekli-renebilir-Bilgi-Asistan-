from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import String, Text, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class QuestionStatus(str, PyEnum):
    PENDING = "Bekliyor"
    ANSWERED = "Cevaplandı"

class PendingQuestion(Base):
    __tablename__ = "pending_questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    question: Mapped[str] = mapped_column(Text, nullable=False)

    asked_by: Mapped[str] = mapped_column(String(100), nullable=False, default="anonymous")

    asked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    status: Mapped[QuestionStatus] = mapped_column(
        Enum(QuestionStatus),
        default=QuestionStatus.PENDING,
        nullable=False,
    )

    admin_answer: Mapped[str | None] = mapped_column(Text, nullable=True)

    answered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<PendingQuestion id={self.id} status={self.status} question='{self.question[:50]}'>"
