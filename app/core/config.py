"""应用配置 — Pydantic Settings"""

from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "医学科研智能助手平台"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite+aiosqlite:///./data/app.db"
    DB_ECHO: bool = False

    DATA_DIR: Path = Path("./data")
    UPLOAD_DIR: Path = Path("./uploads")
    PAPERQA_INDEX_DIR: Path = Path("./data/paperqa_index")
    NOTES_INDEX_DIR: Path = Path("./data/notes_index")

    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    DEFAULT_MODEL_PROVIDER: Literal["openai", "ollama", "openrouter"] = "openai"
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OPENROUTER_API_KEY: str = ""

    SEARCH_TOP_K: int = 5
    RERANK_TOP_K: int = 5

    PUBMED_API_KEY: str = ""
    PUBMED_EMAIL: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
