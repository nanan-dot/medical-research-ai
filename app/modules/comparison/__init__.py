"""Evidence-backed multi-paper comparison module.

R2-WP12 复用：SourceRef / ComparisonCellGenerated / DEFAULT_FIELDS /
FIELD_MAPPING 提升到 shared.py，供 evidence_matrix 模块复用，保证"从
单篇结构化分析取证据"的规则只有一份实现。
"""

from app.modules.comparison.shared import (
    DEFAULT_FIELDS,
    FIELD_MAPPING,
    MISSING_VALUE,
    CellStatus,
    ComparisonCellGenerated,
    ComparisonField,
    SourceRef,
)

__all__ = [
    "DEFAULT_FIELDS",
    "FIELD_MAPPING",
    "MISSING_VALUE",
    "CellStatus",
    "ComparisonCellGenerated",
    "ComparisonField",
    "SourceRef",
]
