"""Conservative, explainable medical search-term expansion."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TermExpansion:
    core_term: str
    synonyms: tuple[str, ...]
    source: str = "curated_local_mapping"


_TERM_MAPPINGS: dict[str, TermExpansion] = {
    "gastric cancer": TermExpansion(
        "Gastric Neoplasms", ("gastric cancer", "stomach cancer")
    ),
    "lung cancer": TermExpansion(
        "Lung Neoplasms", ("lung cancer", "pulmonary neoplasm")
    ),
    "breast cancer": TermExpansion(
        "Breast Neoplasms", ("breast cancer", "mammary carcinoma")
    ),
    "locally advanced rectal cancer": TermExpansion(
        "Rectal Neoplasms",
        ("locally advanced rectal cancer", "locally advanced rectal neoplasm"),
    ),
    "diabetes": TermExpansion("Diabetes Mellitus", ("diabetes", "diabetic")),
    "alzheimer disease": TermExpansion(
        "Alzheimer Disease", ("Alzheimer's disease", "Alzheimer disease")
    ),
    "immunotherapy": TermExpansion(
        "Immunotherapy", ("cancer immunotherapy", "immune therapy")
    ),
    "neoadjuvant immunotherapy": TermExpansion(
        "Immunotherapy",
        ("neoadjuvant immunotherapy", "neoadjuvant immune checkpoint inhibitor"),
    ),
    "metformin": TermExpansion("Metformin", ("metformin", "dimethylbiguanide")),
    "aspirin": TermExpansion("Aspirin", ("aspirin", "acetylsalicylic acid", "ASA")),
    "egfr": TermExpansion("EGFR", ("epidermal growth factor receptor", "ERBB1")),
    "brca1": TermExpansion("BRCA1", ("breast cancer 1", "BRCA1 gene")),
    "pd-l1": TermExpansion("CD274", ("PD-L1", "programmed death-ligand 1")),
}

_CHINESE_ALIASES = {
    "胃癌": "gastric cancer",
    "肺癌": "lung cancer",
    "乳腺癌": "breast cancer",
    "糖尿病": "diabetes",
    "阿尔茨海默病": "alzheimer disease",
    "免疫治疗": "immunotherapy",
    "二甲双胍": "metformin",
    "阿司匹林": "aspirin",
    "表皮生长因子受体": "egfr",
    "靶向治疗": "targeted therapy",
    # 精确别名优先于猜测翻译，避免中文输入在生成查询时被静默丢弃。
    "局部晚期直肠癌": "locally advanced rectal cancer",
    "新辅助免疫治疗": "neoadjuvant immunotherapy",
}


def _resolve_curated_chinese_alias(value: str) -> str | None:
    """Resolve a known Chinese concept embedded in a longer clinical phrase."""
    compact_value = "".join(value.split())
    for phrase, english_term in sorted(
        _CHINESE_ALIASES.items(), key=lambda item: len(item[0]), reverse=True
    ):
        if phrase in compact_value:
            return english_term
    return None


def expand_term(value: str) -> TermExpansion:
    """Return a conservative English expansion; unknown terms are never invented."""
    normalized = _resolve_curated_chinese_alias(value) or " ".join(
        value.casefold().split()
    )
    if known := _TERM_MAPPINGS.get(normalized):
        return known
    return TermExpansion(value.strip(), (value.strip(),), source="user_supplied")


def is_ascii_search_term(value: str) -> bool:
    return value.isascii() and bool(value.strip())
