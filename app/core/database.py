from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


# Async SQLAlchemy engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # Debug modda SQL sorgularını logla
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# Base model sınıfı (tüm tablolar buradan türeyecek)
class Base(DeclarativeBase):
    pass


async def init_db():
    """Veritabanı tablolarını oluşturur. Uygulama başladığında çalışır."""
    from app.core import models  # noqa: F401 — modellerin import edilmesi şart
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """FastAPI dependency injection için DB session döndürür."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
