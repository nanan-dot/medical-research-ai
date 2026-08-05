"""citation_check — 请求/响应模型"""

from typing import Literal

from pydantic import BaseModel, Field

CitationKind = Literal["pmid", "doi"]


class CitationCheckRequest(BaseModel):
    """引用核验请求：用户提交手稿文本或引用列表。"""

    text: str = Field(min_length=1, max_length=50_000)


class CitationAuditItem(BaseModel):
    """单条引用的审计结果。

    verified 只表示该标识符在 PubMed/CrossRef 真实响应中被找到；反幻觉协议
    要求不可验证的引用必须标记 verified=false，绝不凭记忆补全。
    """

    raw: str = Field(max_length=500, description="文本中提取到的原始引用片段")
    kind: CitationKind
    identifier: str = Field(max_length=200, description="规范化后的 PMID 或 DOI")
    verified: bool
    verified_by: str | None = Field(default=None, max_length=40)
    verified_on: str | None = Field(default=None, max_length=40)
    matched: str | None = Field(default=None, max_length=200, description="匹配到的 PMID/DOI")
    notes: list[str] = Field(default_factory=list)


class CitationAuditSummary(BaseModel):
    """审计整体统计。"""

    total: int = Field(ge=0)
    verified: int = Field(ge=0)
    unverified: int = Field(ge=0)


class CitationCheckResult(BaseModel):
    """引用核验审计报告。"""

    items: list[CitationAuditItem] = Field(default_factory=list)
    summary: CitationAuditSummary
