from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Uygulama
    app_name: str = Field(default="SoSmart Bilgi Asistanı", env="APP_NAME")
    app_version: str = Field(default="2.0.0", env="APP_VERSION")
    debug: bool = Field(default=True, env="DEBUG")

    # Ollama
    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="qwen2.5:3b", env="OLLAMA_MODEL")

    # Güven skoru eşiği
    confidence_threshold: float = Field(default=0.5, env="CONFIDENCE_THRESHOLD")

    # ChromaDB
    chroma_persist_dir: str = Field(default="./data/chroma_db", env="CHROMA_PERSIST_DIR")
    chroma_collection_name: str = Field(default="knowledge_base", env="CHROMA_COLLECTION_NAME")

    # SQLite
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/sosmart.db", env="DATABASE_URL"
    )

    # Doküman yükleme
    upload_dir: str = Field(default="./data/uploads", env="UPLOAD_DIR")

    # JWT Auth (2. Hafta)
    jwt_secret_key: str = Field(default="change-me-in-production", env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=480, env="JWT_EXPIRE_MINUTES")

    # Test kullanıcıları
    admin_username: str = Field(default="admin", env="ADMIN_USERNAME")
    admin_password: str = Field(default="admin123", env="ADMIN_PASSWORD")
    user_username: str = Field(default="user", env="USER_USERNAME")
    user_password: str = Field(default="user123", env="USER_PASSWORD")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()

