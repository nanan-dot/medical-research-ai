"""Generate a transparent pixel-difference artifact for the paper-library viewport."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageEnhance


ARTIFACT_DIRECTORY = Path(__file__).resolve().parents[1] / "docs" / "frontend" / "paper-library-v31"
REFERENCE_PATH = ARTIFACT_DIRECTORY / "reference-1536x1024.png"
ACTUAL_PATH = ARTIFACT_DIRECTORY / "actual-1536x1024.png"
DIFF_PATH = ARTIFACT_DIRECTORY / "diff-1536x1024.png"
REPORT_PATH = ARTIFACT_DIRECTORY / "visual-diff-report.md"
PIXEL_THRESHOLD = 24


def changed_pixel_ratio(reference: Image.Image, actual: Image.Image) -> float:
    """Ignore tiny antialiasing changes so the metric reflects visible pixel changes."""
    difference = ImageChops.difference(reference, actual).convert("RGB")
    pixels = difference.load()
    changed = sum(
        1
        for vertical in range(difference.height)
        for horizontal in range(difference.width)
        if max(pixels[horizontal, vertical]) > PIXEL_THRESHOLD
    )
    return changed / (reference.width * reference.height)


def main() -> None:
    reference = Image.open(REFERENCE_PATH).convert("RGBA")
    actual = Image.open(ACTUAL_PATH).convert("RGBA")
    if reference.size != actual.size:
        raise ValueError(f"Screenshots must share a viewport: {reference.size} != {actual.size}")

    difference = ImageChops.difference(reference, actual).convert("RGB")
    enhanced = ImageEnhance.Contrast(difference).enhance(3.0).convert("RGBA")
    enhanced.putalpha(210)
    preview = Image.blend(reference, actual, 0.5).convert("RGBA")
    preview.alpha_composite(enhanced)
    preview.save(DIFF_PATH)

    ratio = changed_pixel_ratio(reference, actual)
    REPORT_PATH.write_text(
        "# 论文库 V3.1 视觉差异报告\n\n"
        "- 参考：`reference-1536x1024.png`（用户提供的固定预览）\n"
        "- 实拍：`actual-1536x1024.png`（隔离 SQLite 后端的真实 API 数据）\n"
        f"- 可见像素差异（阈值 `{PIXEL_THRESHOLD}`）：`{ratio:.2%}`\n"
        "- 差异图：`diff-1536x1024.png`。红紫区域代表参考和实拍的可见像素差异。\n\n"
        "## 解读\n\n"
        "该比率未遮罩真实论文标题、状态、研究关联、资料可用性与全局导航内容；"
        "因此它是保守的全页视觉指标，而不是把动态区域抹除后的布局指标。"
        "隔离库中的 5 条真实记录均为元数据论文、无全文且无研究关联，"
        "与参考图中的已阅读、已分析、已关联论文数据不同，数值不能被解释为纯 CSS 偏差。\n",
        encoding="utf-8",
    )
    print(f"visible_pixel_difference={ratio:.6f}")


if __name__ == "__main__":
    main()
