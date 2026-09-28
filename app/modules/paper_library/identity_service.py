"""论文库直接添加的精确身份校验。"""

import re

from app.common.exceptions import ConflictError
from app.modules.document.matcher import normalize_doi

_PMID = re.compile(r"^[1-9][0-9]{0,19}$")


def normalize_pmid(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = value.strip()
    return candidate if _PMID.fullmatch(candidate) else None


def require_identity(
    doi: str | None, pmid: str | None
) -> tuple[str | None, str | None]:
    normalized_doi = normalize_doi(doi)
    normalized_pmid = normalize_pmid(pmid)
    if doi and normalized_doi is None:
        raise ConflictError("DOI 格式无效")
    if pmid and normalized_pmid is None:
        raise ConflictError("PMID 格式无效")
    return normalized_doi, normalized_pmid
