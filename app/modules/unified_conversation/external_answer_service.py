"""通过已有 PubMed 执行器获取来源；外部内容只作为数据展示。"""

import asyncio
from collections.abc import Callable

from app.integrations.pubmed.client import PubMedClient
from app.integrations.pubmed.exceptions import PubMedError
from app.modules.literature_search.pubmed_executor import PubMedExecutor
from app.modules.unified_conversation.schema import (
    AnswerContent,
    UnifiedAnswerSection,
    UnifiedCitationRead,
)


class ExternalAnswerService:
    def __init__(
        self, client_factory: Callable[[], PubMedClient] = PubMedClient.from_settings
    ) -> None:
        self.client_factory = client_factory

    async def answer(self, query: str) -> AnswerContent:
        client = self.client_factory()
        try:
            records, _ = await asyncio.wait_for(
                PubMedExecutor(client).execute(query, retmax=8), timeout=45
            )
        except (PubMedError, TimeoutError):
            return AnswerContent(
                status="failed",
                warnings=["web_failure"],
                actions=["retry"],
                sections=[
                    UnifiedAnswerSection(
                        source_type="web_augmented",
                        answer_status="failed",
                        content="外部文献检索未能完成，尚未核实最新信息。",
                    )
                ],
            )
        finally:
            await client.aclose()
        sections = []
        for record in records:
            if not record.pmid.isdigit():
                continue
            citation = UnifiedCitationRead(
                pmid=record.pmid,
                url=f"https://pubmed.ncbi.nlm.nih.gov/{record.pmid}/",
                citation_text=record.title,
                evidence_text=record.abstract,
                source_level="abstract" if record.abstract else "metadata",
            )
            sections.append(
                UnifiedAnswerSection(
                    source_type="web_augmented",
                    citations=[citation],
                    content=(record.title or f"PubMed {record.pmid}")
                    + (
                        "\n\n摘要：" + record.abstract
                        if record.abstract
                        else "\n仅取得题录，未读取全文。"
                    ),
                )
            )
        return AnswerContent(
            sections=sections
            or [
                UnifiedAnswerSection(
                    source_type="web_augmented",
                    answer_status="insufficient_evidence",
                    content="本次 PubMed 检索未返回可用记录。",
                )
            ],
            status="answered" if sections else "insufficient_evidence",
            warnings=["pubmed_metadata_or_abstract_only"],
            actions=[] if sections else ["edit_web_query"],
        )
