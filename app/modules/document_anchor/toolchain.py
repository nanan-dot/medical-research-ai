"""独立版本及影响 TextItem 结果的配置集中定义。"""

from app.modules.document_anchor.fingerprint import record_hash
from app.modules.document_anchor.normalization import NORMALIZATION_VERSION

CONTRACT_SCHEMA_VERSION = "1.1"
EXTRACTOR_VERSION = "1.1.0"
PDFJS_VERSION = "6.2.108"
RESULT_OPTIONS = {
    "include_marked_content": True,
    "disable_normalization": False,
    "use_system_fonts": False,
    "disable_font_face": True,
    "use_worker_fetch": False,
    "verbosity": 0,
}
OPTIONS_HASH = record_hash(RESULT_OPTIONS)


def identity() -> dict[str, str]:
    """Return all independently versioned protocol identity fields."""
    return {
        "contract_schema_version": CONTRACT_SCHEMA_VERSION,
        "extractor_version": EXTRACTOR_VERSION,
        "pdfjs_version": PDFJS_VERSION,
        "normalization_version": NORMALIZATION_VERSION,
        "options_hash": OPTIONS_HASH,
    }
