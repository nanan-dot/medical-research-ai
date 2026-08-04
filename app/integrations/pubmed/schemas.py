"""PubMed E-utilities 客户端的稳定数据结构。

只暴露应用侧需要的最小字段，原始 XML/JSON 响应永远不出现在这些模型中。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class PubMedConfig(BaseModel):
    """NCBI E-utilities 调用配置。"""

    email: str | None = Field(default=None, max_length=200)
    api_key: SecretStr | None = None
    # NCBI 无 key 限流 3 req/s，推荐请求间隔 350ms；有 key 时 10 req/s，间隔 100ms。
    rate_limit_seconds: float = Field(default=0.35, gt=0)
    timeout_seconds: float = Field(default=20.0, gt=0)
    # E-utilities 返回的 tool 参数，用于标注请求来源。
    tool: str = Field(default="med-research-assistant", max_length=100)
    base_url: str = Field(default="https://eutils.ncbi.nlm.nih.gov/entrez/eutils", max_length=300)


class PubMedRecord(BaseModel):
    """标准化后的单条 PubMed 文献记录。"""

    model_config = ConfigDict(frozen=True)

    pmid: str = Field(min_length=1, max_length=20)
    doi: str | None = Field(default=None, max_length=200)
    title: str | None = Field(default=None, max_length=1000)
    authors: list[str] = Field(default_factory=list)
    journal: str | None = Field(default=None, max_length=500)
    year: int | None = Field(default=None)
    abstract: str | None = None
    publication_types: list[str] = Field(default_factory=list)
    is_open_access: bool = False
    withdrawn: bool = False

    @property
    def display_title(self) -> str:
        return self.title or f"[no title — PMID {self.pmid}]"


class PubMedSearchResult(BaseModel):
    """ESearch 的规范化结果。"""

    pmids: list[str] = Field(default_factory=list)
    total_count: int = Field(default=0, ge=0)
    query_key: str | None = Field(default=None, max_length=200)
    web_env: str | None = Field(default=None, max_length=300)
