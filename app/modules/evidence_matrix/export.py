"""Evidence-matrix export helpers: CSV and Markdown serialisation.

复用 WP11 comparison 导出模式：CSV 用标准库 csv.writer（自动处理引号/
逗号/换行转义），Markdown 用 escape_markdown 对表格元字符转义。导出只
展示 active 字段与现有单元格；缺失值保留显式"缺失"标记，不编造数据。
"""

import csv
import io

from app.modules.evidence_matrix.schema import EvidenceMatrixRead
from app.modules.export.markdown_renderer import escape_markdown


def to_csv(matrix: EvidenceMatrixRead) -> str:
    """按"字段行 x 文献列"输出 CSV；document 列头带备注与状态标注。"""
    active_fields = [field for field in matrix.fields if field.active]
    documents = sorted(matrix.documents, key=lambda item: item.added_at)
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        [
            "字段",
            *[
                f"文档 {item.document_id} (阅读:{item.reading_status})"
                for item in documents
            ],
        ]
    )
    for field in active_fields:
        row = [field.field_label]
        for document in documents:
            row.append(
                _cell_for(matrix, document.document_id, field.field_key).cell_value
            )
        writer.writerow(row)
    return output.getvalue()


def to_markdown(matrix: EvidenceMatrixRead) -> str:
    """输出矩阵 Markdown 表格；行/列与 CSV 一致。"""
    active_fields = [field for field in matrix.fields if field.active]
    documents = sorted(matrix.documents, key=lambda item: item.added_at)
    header = ["字段", *[f"文档 {item.document_id}" for item in documents]]
    lines = [
        f"# 证据矩阵：{matrix.name}",
        "",
        f"> 版本 v{matrix.version} ｜ {len(documents)} 篇文献 ｜ 来源为真实 PMID/DOI，缺失值显式标注。",
        "",
        _markdown_row(header),
        _markdown_row(["---"] * len(header)),
    ]
    for field in active_fields:
        values = [field.field_label]
        values.extend(
            _cell_for(matrix, document.document_id, field.field_key).cell_value
            for document in documents
        )
        lines.append(_markdown_row(values))
    # 文献状态尾注：人工备注/阅读状态属于用户态，导出为可读说明。
    for document in documents:
        notes = document.user_notes.strip()
        suffix = f"（备注：{notes}）" if notes else ""
        lines.append(
            f"- 文档 {document.document_id}：{document.document_status}{suffix}"
        )
    return "\n".join(lines) + "\n"


def _cell_for(matrix: EvidenceMatrixRead, document_id: int, field_key: str):
    return next(
        cell
        for cell in matrix.cells
        if cell.document_id == document_id and cell.field_key == field_key
    )


def _markdown_row(values: list[str]) -> str:
    escaped = [escape_markdown(value) for value in values]
    return f"| {' | '.join(escaped)} |"
