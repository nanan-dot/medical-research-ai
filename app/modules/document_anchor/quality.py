"""可观测的页级技术质量，不能替代医学语义审核。"""

import math
import unicodedata
from collections import Counter
from statistics import median

from app.modules.document_anchor.contract import PageRecord, TextItemRecord


def item_bbox(item: TextItemRecord) -> tuple[float, float, float, float]:
    """Estimate PDF-space AABB from baseline vectors; raw transform remains authoritative."""
    a, b, c, d, x, y = item.transform
    baseline = math.hypot(a, b) or 1
    vertical = math.hypot(c, d) or 1
    ux, uy = a / baseline * item.width, b / baseline * item.width
    vx, vy = c / vertical * item.height, d / vertical * item.height
    points = ((x, y), (x + ux, y + uy), (x + vx, y + vy), (x + ux + vx, y + uy + vy))
    return (
        min(p[0] for p in points),
        min(p[1] for p in points),
        max(p[0] for p in points),
        max(p[1] for p in points),
    )


def page_quality(page: PageRecord) -> tuple[dict[str, object], list[str]]:
    """Compute deterministic bounded metrics; pathological overlap fails closed."""
    texts = [item.text for item in page.items]
    text = "".join(texts)
    boxes = [item_bbox(item) for item in page.items]
    x0, y0, x1, y1 = page.view_box
    outside = sum(
        box[0] < x0 - 1 or box[1] < y0 - 1 or box[2] > x1 + 1 or box[3] > y1 + 1
        for box in boxes
    )
    # 扫描线只比较 x 范围重合的项；比较预算防止恶意 5 万项同点退化为平方复杂度。
    active: list[tuple[float, float, float, float]] = []
    overlaps, comparisons = 0, 0
    capped = False
    for box in sorted(boxes):
        active = [other for other in active if other[2] > box[0]]
        for other in active:
            comparisons += 1
            if comparisons > 1_000_000:
                capped = True
                break
            overlaps += min(other[3], box[3]) > max(other[1], box[1])
        if capped:
            break
        active.append(box)
    nonwhite = sum(not char.isspace() for char in text)
    controls = sum(
        unicodedata.category(char) == "Cc" and char not in "\t\r\n" for char in text
    )
    coverage = min(
        1.0,
        sum(max(0, b[2] - b[0]) * max(0, b[3] - b[1]) for b in boxes)
        / ((x1 - x0) * (y1 - y0)),
    )
    count = len(texts)
    rotated = sum(
        abs(item.transform[1]) > 1e-6 or abs(item.transform[2]) > 1e-6
        for item in page.items
    )
    metrics: dict[str, object] = {
        "text_item_count": count,
        "non_whitespace_character_count": nonwhite,
        "replacement_character_count": text.count("�"),
        "control_character_count": controls,
        "invalid_numeric_value_count": 0,
        "overlapping_item_pair_count": overlaps,
        "overlap_count_is_lower_bound": capped,
        "out_of_bounds_item_count": outside,
        "rotated_item_count": rotated,
        "direction_counts": dict(Counter(item.direction for item in page.items)),
        "font_count": len({item.font_name for item in page.items if item.font_name}),
        "empty_item_ratio": sum(not value.strip() for value in texts) / max(count, 1),
        "duplicate_text_item_ratio": (count - len(set(texts))) / max(count, 1),
        "estimated_text_coverage": coverage,
    }
    flags: list[str] = []
    if not nonwhite:
        flags.append("NO_SELECTABLE_TEXT")
        if page.has_raster_image:
            flags.append("LIKELY_SCANNED_PAGE")
    if coverage < 0.001:
        flags.append("VERY_LOW_TEXT_COVERAGE")
    if controls or "�" in text:
        flags.append("INVALID_CHARACTERS_PRESENT")
    missing_metrics = sum(
        style.ascent is None or style.descent is None for style in page.styles.values()
    )
    metrics["font_styles_with_unknown_metrics"] = missing_metrics
    if missing_metrics:
        flags.append("UNKNOWN_FONT_METRICS")
    if outside:
        flags.append("OUT_OF_BOUNDS_GEOMETRY")
    if overlaps > max(count, 10) or capped:
        flags.append("EXCESSIVE_OVERLAP")
    if rotated:
        flags.append("MIXED_ROTATION_COMPLEXITY")
    if flags:
        flags.append("MANUAL_REVIEW_RECOMMENDED")
    return metrics, flags


def document_quality(
    counts: list[int], flags: list[list[str]], content_hash: str
) -> dict[str, object]:
    """Summarize downstream eligibility without asserting medical correctness."""
    unusable = sum("NO_SELECTABLE_TEXT" in values for values in flags)
    return {
        "page_count": len(counts),
        "pages_requiring_review": sum(bool(values) for values in flags),
        "normal_page_count": sum(not values for values in flags),
        "unusable_page_count": unusable,
        "selectable_text_page_ratio": 1 - unusable / len(counts),
        "max_text_item_count": max(counts),
        "median_text_item_count": median(counts),
        "warning_counts": dict(Counter(flag for values in flags for flag in values)),
        "eligible_for_a1": not any(flags),
        "document_content_hash": content_hash,
    }
