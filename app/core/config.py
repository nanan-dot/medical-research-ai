"""应用配置 — Pydantic Settings"""

from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "医学科研智能助手平台"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    DISCLOSURE_NOTICE_ENABLED: bool = True

    DATABASE_URL: str = "sqlite+aiosqlite:///./data/app.db"
    DB_ECHO: bool = False

    DATA_DIR: Path = Path("./data")
    UPLOAD_DIR: Path = Path("./uploads")
    PAPERQA_INDEX_DIR: Path = Path("./data/paperqa_index")
    NOTES_INDEX_DIR: Path = Path("./data/notes_index")
    EXPORT_DIR: Path = Path("./data/exports")

    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    DEFAULT_MODEL_PROVIDER: Literal["openai", "ollama", "openrouter"] = "openai"
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = ""
    OLLAMA_TIMEOUT_SECONDS: float = 120.0
    PAPERQA_VERSION: str = "2026.3.18"
    PAPERQA_EMBEDDING_MODEL: str = "nomic-embed-text"
    PAPERQA_TIMEOUT_SECONDS: float = 300.0
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = ""
    LLM_TIMEOUT_SECONDS: float = 30.0
    MODEL_CONFIG_ENCRYPTION_KEYS: str = ""

    SEARCH_TOP_K: int = 5
    RERANK_TOP_K: int = 5

    # Mini-RAG 笔记检索（R2-WP09）：本地优先，ollama 失败时用 dummy 兜底而非云端
    EMBEDDING_PROVIDER: Literal["ollama", "dummy"] = "dummy"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    # 索引向量维度（nomic-embed-text 为 384；dummy 开发用默认 16）
    EMBEDDING_DIMENSION: int = 384

    PUBMED_API_KEY: str = ""
    PUBMED_EMAIL: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
