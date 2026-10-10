"""Original inverse angular image warp; independent of graphics and transport.

This changes a flat image's projection, not the source camera or scene depth.
The corresponding GLES/Metal implementations sample this mapping on the GPU.
Normalized coordinates use Y up; the texture adapter below flips Y once.
"""

import math


def _number(value, name):
    if type(value) not in (int, float):
        raise ValueError(f"{name} must be finite")
    try:
        value = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} must be finite") from exc
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def source_point(x: float, y: float, fov: float = 80.0):
    """Return source XY, or None outside the destination square.

    Source values outside [-1,1] are valid black-border samples. FOV 50...110
    bounds the largest square-corner angle to sqrt(2)*55 degrees < 90 degrees.
    This keeps the tangent finite and monotonic. Center maps to center.
    """
    x, y, fov = _number(x, "x"), _number(y, "y"), _number(fov, "fov")
    if not 50 <= fov <= 110:
        raise ValueError("fov outside 50..110")
    if abs(x) > 1 or abs(y) > 1:
        return None
    radius = math.hypot(x, y)
    if radius < 1e-6:
        return (0.0, 0.0)
    angle = math.radians(fov) * 0.5
    gain = math.tan(radius * angle) / (radius * math.tan(angle))
    return (x * gain, y * gain)


def texture_uv(x: float, y: float, fov: float = 80.0):
    """Inverse pixel mapping with black source/destination bounds and Y flip."""
    source = source_point(x, y, fov)
    if source is None or abs(source[0]) > 1 or abs(source[1]) > 1:
        return None
    return (source[0] * 0.5 + 0.5, 0.5 - source[1] * 0.5)
