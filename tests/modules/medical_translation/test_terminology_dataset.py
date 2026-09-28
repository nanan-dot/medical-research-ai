import json
from pathlib import Path

from app.modules.medical_translation.terminology_dataset import (
    MedicalTerminologyDataset,
)
from scripts.import_medct_terminology import build_index


def test_medct_index_prefers_clean_chinese_and_respects_reserved_terms(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "find_sctid_syn-enzh.json").write_text(
        json.dumps(
            {
                "1": ["Pulmonary hypertension", "PH—肺动脉高压", "肺动脉高压"],
                "2": ["Interstitial lung disease", "间质性肺病"],
            }
        ),
        encoding="utf-8",
    )
    index_path = tmp_path / "terms.sqlite3"
    concepts, terms = build_index(source, index_path)
    dataset = MedicalTerminologyDataset(index_path)

    matched = dataset.lookup(
        "Interstitial lung disease and pulmonary hypertension.",
        reserved_terms=("interstitial lung disease",),
    )

    assert (concepts, terms) == (2, 2)
    assert matched == {"pulmonary hypertension": "肺动脉高压"}
