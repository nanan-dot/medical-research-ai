"""应用配置 — Pydantic Settings"""

from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "医学科研智能助手平台"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    DISCLOSURE_NOTICE_ENABLED: bool = True

    DATABASE_URL: str = "sqlite+aiosqlite:///./data/app.db"
    DB_ECHO: bool = False

    DATA_DIR: Path = Path("./data")
    ENABLE_LOCAL_DIRECTORY_OPEN: bool = False
    LOCAL_DESKTOP_MODE: bool = False
    UPLOAD_DIR: Path = Path("./uploads")
    MAX_UPLOAD_PDF_BYTES: int = 50 * 1024 * 1024
    MAX_LIBRARY_UPLOAD_BYTES: int = 50 * 1024 * 1024
    MAX_LIBRARY_IMPORT_FILES: int = 25
    MAX_LIBRARY_ARCHIVE_UNCOMPRESSED_BYTES: int = 250 * 1024 * 1024
    LIBRARY_STORAGE_QUOTA_BYTES: int | None = None
    MAX_DOCX_PREVIEW_BYTES: int = 10 * 1024 * 1024
    JOURNAL_METRIC_IMPORT_MAX_BYTES: int = 32 * 1024 * 1024
    OCR_OUTPUT_DIR: Path = Path("./data/ocr")
    OCR_LANGUAGE: str = "eng"
    OCR_MAX_PAGES: int = 50
    OCR_RENDER_SCALE: float = 2.0
    TESSERACT_COMMAND: str = ""
    # A0 uses a separately installed, fixed-PDF.js executable. Empty means the
    # capability is unavailable; it deliberately never falls back to pypdf offsets.
    PDF_TEXTITEM_EXTRACTOR_COMMAND: str = ""
    PDF_TEXTITEM_EXTRACTOR_TIMEOUT_SECONDS: float = Field(default=120.0, gt=0, le=3600)
    PDF_TEXTITEM_EXTRACTOR_MAX_PAGES: int = Field(default=500, ge=1, le=500)
    PDF_TEXTITEM_EXTRACTOR_MAX_ITEMS_PER_PAGE: int = Field(default=50_000, ge=1, le=50_000)
    PDF_TEXTITEM_EXTRACTOR_MAX_OUTPUT_BYTES: int = Field(default=128 * 1024 * 1024, ge=1, le=1024**3)
    PDF_TEXTITEM_EXTRACTOR_MAX_FILE_BYTES: int = Field(default=100 * 1024 * 1024, ge=1, le=1024**3)
    PDF_TEXTITEM_EXTRACTOR_MAX_LINE_BYTES: int = Field(default=16 * 1024 * 1024, ge=1, le=128 * 1024 * 1024)
    PDF_TEXTITEM_EXTRACTOR_IDLE_TIMEOUT_SECONDS: float = Field(default=30.0, gt=0, le=3600)
    OPEN_FULLTEXT_DIR: Path = Path("./data/open_fulltext")
    MAX_OPEN_FULLTEXT_PDF_BYTES: int = 100 * 1024 * 1024
    PMC_REQUEST_TIMEOUT_SECONDS: float = 30.0
    PMC_DOWNLOAD_TIMEOUT_SECONDS: float = 90.0
    PMC_CONTACT_EMAIL: str = ""
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

    # 本地离线医学翻译模型；目录必须由运维预先校验 manifest，应用不会联网下载。
    MEDICAL_TRANSLATION_LOCAL_MODEL_DIR: Path | None = None
    MEDICAL_TRANSLATION_LOCAL_TOKENIZER_DIR: Path | None = None
    MEDICAL_TRANSLATION_LOCAL_DEVICE: Literal["auto", "cpu", "cuda"] = "auto"
    MEDICAL_TRANSLATION_ENGINE: Literal["auto", "local-transformers", "ollama"] = "auto"
    MEDICAL_TERMINOLOGY_INDEX_PATH: Path | None = None
    MEDICAL_TRANSLATION_LOCAL_CPU_THREADS: int = Field(default=2, ge=1, le=16)
    MEDICAL_TRANSLATION_TIMEOUT_SECONDS: float = Field(default=600.0, ge=10, le=3600)

    SEARCH_TOP_K: int = 5
    # Legacy compatibility only: new callers select a named retrieval profile.
    DENSE_TOP_K: int | None = None
    SPARSE_TOP_K: int | None = None
    FUSION_TOP_K: int | None = None
    RERANK_TOP_K: int | None = None
    LLM_CONTEXT_TOP_K: int | None = None
    RRF_K: int = 60
    RERANK_ENABLED: bool = False
    NAVIGATION_RERANK_ENABLED: bool = False
    NAVIGATION_RERANK_MODEL_DIR: Path | None = None
    NAVIGATION_RERANK_INITIALIZATION_TIMEOUT_SECONDS: float = Field(
        default=60.0, ge=1, le=600
    )
    NAVIGATION_RERANK_TIMEOUT_SECONDS: float = Field(default=30.0, ge=1, le=300)
    NAVIGATION_DENSE_TOP_K: int = Field(default=30, ge=1, le=500)
    NAVIGATION_SPARSE_TOP_K: int = Field(default=30, ge=1, le=500)
    NAVIGATION_FUSION_TOP_K: int = Field(default=40, ge=1, le=500)
    NAVIGATION_RERANK_CANDIDATE_TOP_K: int = Field(default=40, ge=1, le=500)
    GROUNDED_RAG_MODE: Literal["paperqa", "shadow", "grounded"] = "paperqa"
    GROUNDED_RAG_ENABLED: bool = False
    # RAG 审计轨迹仅在项目 DATA_DIR 下持久化；默认最小化采集，不保留问题/正文。
    RAG_TRACE_ENABLED: bool = False
    RAG_TRACE_DIR: Path | None = None
    RAG_TRACE_STORE_QUERY: bool = False
    RAG_TRACE_STORE_TEXT: bool = False
    RAG_TRACE_MAX_CANDIDATES: int = 50
    RAG_TRACE_MAX_TEXT_CHARS: int = 500
    RAG_TRACE_RETENTION_DAYS: int = 30
    # 专家 Shadow 的性能门默认未批准；阈值只能经项目审批后填写。
    MEDICAL_SHADOW_PERFORMANCE_BUDGET_APPROVED: bool = False
    MEDICAL_SHADOW_PERFORMANCE_BUDGET_SOURCE: str = ""
    retrieval_config_notice: str | None = None
    RETRIEVAL_PROFILE: Literal["single_document", "local_evidence", "multi_document"] = "local_evidence"

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_search_top_k(cls, values: object) -> object:
        if not isinstance(values, dict):
            return values
        stage_names = ("DENSE_TOP_K", "SPARSE_TOP_K", "FUSION_TOP_K", "RERANK_TOP_K", "LLM_CONTEXT_TOP_K")
        has_explicit_stage = any(name in values and values[name] not in (None, "") for name in stage_names)
        legacy = values.get("SEARCH_TOP_K")
        if legacy not in (None, "", 5):
            if has_explicit_stage:
                values["retrieval_config_notice"] = "SEARCH_TOP_K ignored where explicit stage values exist"
            else:
                values.update({name: legacy for name in stage_names})
        return values

    @model_validator(mode="after")
    def apply_legacy_retrieval_compatibility(self) -> "Settings":
        """SEARCH_TOP_K remains an explicit fallback, never a hidden global switch."""
        defaults = {"single_document": (20, 20, 25, 6, 5), "local_evidence": (30, 30, 40, 8, 6), "multi_document": (50, 50, 80, 12, 10)}
        dense, sparse, fusion, rerank, context = defaults[self.RETRIEVAL_PROFILE]
        self.DENSE_TOP_K = self.DENSE_TOP_K or dense
        self.SPARSE_TOP_K = self.SPARSE_TOP_K or sparse
        self.FUSION_TOP_K = self.FUSION_TOP_K or fusion
        self.RERANK_TOP_K = self.RERANK_TOP_K or rerank
        self.LLM_CONTEXT_TOP_K = self.LLM_CONTEXT_TOP_K or context
        if self.RERANK_TOP_K > self.FUSION_TOP_K:
            raise ValueError("RERANK_TOP_K must not exceed FUSION_TOP_K")
        if self.LLM_CONTEXT_TOP_K > self.RERANK_TOP_K:
            raise ValueError("LLM_CONTEXT_TOP_K must not exceed RERANK_TOP_K")
        if self.RAG_TRACE_MAX_CANDIDATES <= 0 or self.RAG_TRACE_MAX_TEXT_CHARS < 0:
            raise ValueError("RAG trace candidate and text limits are invalid")
        if self.RAG_TRACE_RETENTION_DAYS < 0:
            raise ValueError("RAG_TRACE_RETENTION_DAYS must not be negative")
        if self.RAG_TRACE_DIR is not None:
            try:
                self.RAG_TRACE_DIR.resolve().relative_to(self.DATA_DIR.resolve())
            except ValueError as error:
                raise ValueError("RAG_TRACE_DIR must stay under DATA_DIR") from error
        return self

    # Mini-RAG 笔记检索（R2-WP09）：本地优先，ollama 失败时用 dummy 兜底而非云端
    EMBEDDING_PROVIDER: Literal["ollama", "dummy"] = "dummy"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    # 索引向量维度（nomic-embed-text 为 384；dummy 开发用默认 16）
    EMBEDDING_DIMENSION: int = 384

    PUBMED_API_KEY: str = ""
    PUBMED_EMAIL: str = ""

    # Zotero 凭证只来自运行时环境；数据库只保存 library identity 和同步游标。
    ZOTERO_API_KEY: str = ""
    ZOTERO_API_BASE_URL: str = "https://api.zotero.org"
    ZOTERO_TIMEOUT_SECONDS: float = 30.0
    ZOTERO_MAX_RETRIES: int = 3

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
