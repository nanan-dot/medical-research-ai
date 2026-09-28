"""Convert A0 PDF corner bounds to rotation-aware natural reading coordinates."""

def natural_bbox(bbox: list[float], view_box: list[float], width: float, height: float,
                 rotation: int) -> tuple[float, float, float, float]:
    """Keep A0 corner semantics; apply the same orthogonal rotation as PDF.js."""
    if len(bbox) != 4 or width <= 0 or height <= 0 or rotation % 90:
        raise ValueError("Invalid A0 page geometry")
    if len(view_box) == 4:
        left, bottom, right, top = view_box
    else:
        left, bottom = 0.0, 0.0
        right, top = (height, width) if rotation % 180 else (width, height)
    x0, y0, x1, y1 = bbox
    if x1 < x0 or y1 < y0:
        raise ValueError("A0 bbox must contain ordered corner coordinates")

    def point(x: float, y: float) -> tuple[float, float]:
        match rotation % 360:
            case 90:
                return ((y - bottom) / width, (x - left) / height)
            case 180:
                return ((right - x) / width, (y - bottom) / height)
            case 270:
                return ((top - y) / width, (right - x) / height)
            case _:
                return ((x - left) / width, (top - y) / height)

    points = [point(x, y) for x, y in [(x0, y0), (x0, y1), (x1, y0), (x1, y1)]]
    x, y = min(p[0] for p in points), min(p[1] for p in points)
    return x, y, max(p[0] for p in points) - x, max(p[1] for p in points) - y
