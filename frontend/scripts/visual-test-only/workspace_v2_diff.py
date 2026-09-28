"""Generate V2 workspace overlay/diff and measured-image acceptance evidence.

This test-only tool never runs in the frontend bundle.  It requires two 1536x1024
PNG inputs and records reproducible numeric image-difference evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageStat


REGIONS = {
    "Sidebar": (0, 0, 229, 1024),
    "Header": (229, 0, 1536, 75),
    "Journey": (229, 75, 1536, 137),
    "Basis": (255, 137, 1510, 333),
    "Terms": (255, 343, 1510, 729),
    "Query": (255, 739, 1510, 837),
    "LimitsReady": (255, 857, 1510, 937),
    "Sticky": (229, 937, 1536, 1016),
}
APPROVED_HEADER_BUTTON_BOX = (1370, 16, 1512, 60)


def pixel_ratio(image: Image.Image) -> float:
    pixels = image.convert("RGB").getdata()
    return sum(pixel != (0, 0, 0) for pixel in pixels) / (image.width * image.height)


def global_ssim(reference: Image.Image, actual: Image.Image) -> float:
    """No extra dependency: global luminance/contrast/structure SSIM estimate."""
    reference_l = reference.convert("L")
    actual_l = actual.convert("L")
    ref_stat = ImageStat.Stat(reference_l)
    actual_stat = ImageStat.Stat(actual_l)
    mean_ref, mean_actual = ref_stat.mean[0], actual_stat.mean[0]
    var_ref, var_actual = ref_stat.var[0], actual_stat.var[0]
    paired = zip(reference_l.getdata(), actual_l.getdata(), strict=True)
    covariance = sum((left - mean_ref) * (right - mean_actual) for left, right in paired) / (reference.width * reference.height)
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    return ((2 * mean_ref * mean_actual + c1) * (2 * covariance + c2)) / ((mean_ref**2 + mean_actual**2 + c1) * (var_ref + var_actual + c2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", required=True)
    parser.add_argument("--actual", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    reference_source = Image.open(args.reference)
    actual_source = Image.open(args.actual)
    source_metadata = {
        "reference": {"size": reference_source.size, "mode": reference_source.mode, "info": reference_source.info},
        "actual": {"size": actual_source.size, "mode": actual_source.mode, "info": actual_source.info},
    }
    reference = reference_source.convert("RGBA")
    actual = actual_source.convert("RGBA")
    if reference.size != actual.size:
        raise SystemExit(f"dimension mismatch: {reference.size} != {actual.size}")

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    overlay = Image.blend(reference, actual, 0.5)
    difference = ImageChops.difference(reference, actual)
    overlay.save(output / "workspace-1536x1024-overlay.png")
    difference.save(output / "workspace-1536x1024-diff.png")

    stat = ImageStat.Stat(difference.convert("RGB"))
    mean = [round(value, 3) for value in stat.mean]
    rms = [round(value, 3) for value in stat.rms]
    changed = sum(1 for pixel in difference.convert("RGB").getdata() if pixel != (0, 0, 0))
    total = reference.width * reference.height
    edge_difference = ImageChops.difference(
        reference.convert("L").filter(ImageFilter.FIND_EDGES),
        actual.convert("L").filter(ImageFilter.FIND_EDGES),
    )
    approved_mask = Image.new("L", reference.size, 0)
    approved_mask.paste(255, APPROVED_HEADER_BUTTON_BOX)
    unapproved_difference = difference.copy()
    unapproved_difference.paste((0, 0, 0, 0), mask=approved_mask)
    region_differences = {}
    for name, box in REGIONS.items():
        crop = difference.crop(box).convert("RGB")
        pixels = list(crop.getdata())
        region_differences[name] = {
            "box": {"left": box[0], "top": box[1], "right": box[2], "bottom": box[3]},
            "changed_pixel_ratio": round(sum(pixel != (0, 0, 0) for pixel in pixels) / len(pixels), 6),
            "mean_abs_rgb": [round(value, 3) for value in ImageStat.Stat(crop).mean],
        }
    (output / "visual-acceptance.json").write_text(
        json.dumps(
            {
                "reference": str(args.reference),
                "actual": str(args.actual),
                "viewport": {"width": reference.width, "height": reference.height, "dpr": 1},
                "source_metadata": source_metadata,
                "mean_abs_rgb": mean,
                "rms_rgb": rms,
                "changed_pixel_ratio": round(changed / total, 6),
                "global_ssim_luminance": round(global_ssim(reference, actual), 6),
                "edge_changed_pixel_ratio": round(pixel_ratio(edge_difference), 6),
                "approved_difference_analysis": {
                    "approved_header_button_box": {"left": 1370, "top": 16, "right": 1512, "bottom": 60},
                    "raw_changed_pixel_ratio": round(changed / total, 6),
                    "masked_analysis_changed_pixel_ratio": round(pixel_ratio(unapproved_difference), 6),
                    "disclosure": "This mask is analysis-only. It overlaps the naturally reflowed version control, so raw diff remains the authoritative artifact.",
                },
                "region_differences": region_differences,
                "note": "Pixel diff is an iteration signal, not a claim of pixel-perfect parity.",
                "remaining_material_differences": [
                    "sidebar logo, navigation icon family, and density",
                    "typography and text rendering",
                    "header and journey spacing",
                    "PICO card internals, borders, and shadows",
                    "Terms, Limits, Ready, and Sticky internal layouts",
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
