from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):

    app_name: str = Field(default="SoSmart Bilgi Asistanı", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=True, env="DEBUG")

    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="qwen2.5:3b", env="OLLAMA_MODEL")

    confidence_threshold: float = Field(default=0.5, env="CONFIDENCE_THRESHOLD")

    chroma_persist_dir: str = Field(default="./data/chroma_db", env="CHROMA_PERSIST_DIR")
    chroma_collection_name: str = Field(default="knowledge_base", env="CHROMA_COLLECTION_NAME")

    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/sosmart.db", env="DATABASE_URL"
    )

    upload_dir: str = Field(default="./data/uploads", env="UPLOAD_DIR")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

# Global settings nesnesi
settings = Settings()
