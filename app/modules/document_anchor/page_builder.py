"""纯函数生成持久化页面与明确标注的源/合成范围。"""

import json
import math

from app.modules.document_anchor.contract import PageRecord, TextItemRecord
from app.modules.document_anchor.model import DocumentSourcePage, DocumentSourceTextItem
from app.modules.document_anchor.normalization import normalize_text_item, utf16_length
from app.modules.document_anchor.quality import item_bbox, page_quality


def separator(previous: TextItemRecord, current: TextItemRecord) -> str:
    """Choose only observable layout separators, never join split words."""
    if previous.text.endswith(("\n", "\r")) or current.text.startswith(("\n", "\r")):
        return ""
    if previous.has_eol:
        return "\n"
    if (
        not previous.text
        or not current.text
        or previous.text[-1].isspace()
        or current.text[0].isspace()
    ):
        return ""
    if previous.direction != current.direction:
        return "\n"
    a, b, _, _, x, y = previous.transform
    norm = math.hypot(a, b) or 1
    ux, uy = a / norm, b / norm
    dx, dy = current.transform[4] - x, current.transform[5] - y
    if abs(dx * -uy + dy * ux) > max(previous.height, current.height, 1) * 0.5:
        return "\n"
    gap = dx * ux + dy * uy
    if previous.direction == "rtl":
        gap = -gap
    gap -= previous.width
    return " " if gap > max(previous.height, 1) * 0.15 else ""


def page_entities(
    revision_id: int, page_record: PageRecord, flags: list[str], page_hash: str
) -> tuple[DocumentSourcePage, list[DocumentSourceTextItem]]:
    raw_parts: list[str] = []
    normalized_parts: list[str] = []
    mappings: list[dict[str, object]] = []
    entities: list[DocumentSourceTextItem] = []
    cursor = 0
    previous = None
    for item in page_record.items:
        normalized = normalize_text_item(item.text)
        join = separator(previous, item) if previous else ""
        if join:
            mappings.append(
                {
                    "kind": "synthetic",
                    "start": cursor,
                    "end": cursor + utf16_length(join),
                    "left_item_index": previous.item_index if previous else None,
                    "right_item_index": item.item_index,
                }
            )
            normalized_parts.append(join)
            cursor += utf16_length(join)
        start = cursor
        raw_parts.append(item.text)
        normalized_parts.append(normalized.normalized_text)
        local_map = []
        for char, (raw_start, raw_end) in zip(
            normalized.normalized_text, normalized.char_map, strict=True
        ):
            end = cursor + utf16_length(char)
            local_map.append(
                {
                    "start": cursor - start,
                    "end": end - start,
                    "raw_start": raw_start,
                    "raw_end": raw_end,
                }
            )
            cursor = end
        mappings.append(
            {
                "kind": "source",
                "start": start,
                "end": cursor,
                "item_index": item.item_index,
            }
        )
        entities.append(
            DocumentSourceTextItem(
                page_id=0,
                item_index=item.item_index,
                source_array_index=item.source_array_index,
                raw_text=item.text,
                normalized_text=normalized.normalized_text,
                transform_json=json.dumps(item.transform),
                width=item.width,
                height=item.height,
                has_eol=item.has_eol,
                direction=item.direction,
                font_name=item.font_name,
                normalized_char_start=start,
                normalized_char_end=cursor,
                raw_utf16_length=normalized.raw_utf16_length,
                char_map_json=json.dumps(local_map),
                bbox_json=json.dumps(item_bbox(item)),
            )
        )
        previous = item
    return DocumentSourcePage(
        revision_id=revision_id,
        page_number=page_record.page_number,
        width=page_record.width,
        height=page_record.height,
        rotation=page_record.rotation,
        view_box_json=json.dumps(page_record.view_box),
        raw_text="".join(raw_parts),
        normalized_text="".join(normalized_parts),
        text_hash=page_hash,
        text_item_count=len(entities),
        quality_flags_json=json.dumps(flags),
        styles_json=json.dumps(
            {name: style.model_dump() for name, style in page_record.styles.items()}
        ),
        quality_metrics_json=json.dumps(page_quality(page_record)[0]),
        char_map_json=json.dumps(mappings),
    ), entities
