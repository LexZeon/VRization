"""Original, platform-independent headset-fit geometry and draft transactions.

Coordinates are normalized independently in each eye to [-1, 1], with y up.
Drag deltas are measured from pointer-down; they are never incremental events.
This module does not render, save preferences, send messages or control input.
"""

import math

from .protocol import Settings


def _finite(value: float, name: str) -> float:
    if type(value) not in (int, float):
        raise ValueError(f"{name} must be a finite number")
    try:
        number = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} must be finite") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _settings(value: Settings) -> Settings:
    if not isinstance(value, Settings):
        raise TypeError("expected Settings")
    # Settings is immutable, but direct dataclass construction can bypass the
    # protocol validator. Reject invalid snapshots before they enter a draft.
    value.update(value.to_dict())
    return value


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def fit_size(image_aspect: float, eye_aspect: float) -> tuple[float, float]:
    """Return aspect-preserving half-extents for an image at scale 1."""
    image = _finite(image_aspect, "image_aspect")
    eye = _finite(eye_aspect, "eye_aspect")
    if image <= 0 or eye <= 0:
        raise ValueError("aspect ratios must be positive")
    return min(1.0, image / eye), min(1.0, eye / image)


def resolved_fit(settings: Settings, image_aspect: float,
                 eye_aspect: float) -> Settings:
    """Resolve a flat fit without an inner gap caused by shared X at contact.

    Signed separation allows small images to move inward until their inner
    edges meet. The remaining gap limits shared horizontal offset, reaching
    zero at contact. Raw settings are retained by the caller; this function
    neither mutates them nor saves this aspect-dependent rendering result.
    """
    entry = _settings(settings)
    fit_x, _ = fit_size(image_aspect, eye_aspect)
    half_x = fit_x * entry.scale
    separation = _clamp(entry.eyeSeparation, half_x - 1.0, 0.2)
    gap = max(0.0, 1.0 + separation - half_x)
    limit_x = min(0.3, gap)
    return entry.update({
        "eyeSeparation": separation,
        "offsetX": _clamp(entry.offsetX, -limit_x, limit_x),
    })


def eye_bounds(settings: Settings, eye: int, image_aspect: float,
               eye_aspect: float) -> tuple[float, float, float, float]:
    """Return (left, bottom, right, top); eye 0 is left and eye 1 right.

    Uses the same resolved flat fit as rendering. Outer bounds can extend
    beyond [-1, 1]; this function leaves those bounds intact for hit testing.
    """
    entry = resolved_fit(settings, image_aspect, eye_aspect)
    if type(eye) is not int or eye not in (0, 1):
        raise ValueError("eye must be 0 (left) or 1 (right)")
    fit_x, fit_y = fit_size(image_aspect, eye_aspect)
    center_x = entry.offsetX + (-1 if eye == 0 else 1) * entry.eyeSeparation
    half_x, half_y = fit_x * entry.scale, fit_y * entry.scale
    return (center_x - half_x, entry.offsetY - half_y,
            center_x + half_x, entry.offsetY + half_y)


def dragged(settings: Settings, kind: str, dx: float, dy: float,
            image_aspect: float, eye_aspect: float,
            corner_signs: tuple[int, int] = (1, 1), *,
            eye: int | None = None) -> Settings:
    """Compute a new snapshot from gesture-start settings and total deltas.

    ``pan`` moves shared offsets and remains available to other integrations.
    The app editor uses ``eye_pan``: horizontal movement changes mirrored eye
    separation; vertical movement changes shared offsetY. Shared X is retained
    while the inner gap permits it and recenters as the images reach contact.
    Eye 0 is left, eye 1 right. ``resize`` projects signed corner movement onto
    the aspect-preserving fit vector with the center fixed. Corner signs use
    y-up coordinates. Contact constraints can move centers during enlargement.
    Unrelated mode and optical fields remain unchanged. Callers freeze both
    aspects for the duration of each gesture.
    """
    entry = _settings(settings)
    delta_x, delta_y = _finite(dx, "dx"), _finite(dy, "dy")
    fit_x, fit_y = fit_size(image_aspect, eye_aspect)
    if kind == "pan":
        return entry.update({
            "offsetX": _clamp(entry.offsetX + delta_x, -0.3, 0.3),
            "offsetY": _clamp(entry.offsetY + delta_y, -0.3, 0.3),
        })
    if kind == "eye_pan":
        if type(eye) is not int or eye not in (0, 1):
            raise ValueError("eye must be 0 (left) or 1 (right) for eye_pan")
        sign = -1 if eye == 0 else 1
        origin = resolved_fit(entry, image_aspect, eye_aspect)
        candidate = origin.update({
            "eyeSeparation": _clamp(origin.eyeSeparation + sign * delta_x,
                                    fit_x * origin.scale - 1.0, 0.2),
            "offsetY": _clamp(origin.offsetY + delta_y, -0.3, 0.3),
        })
        return resolved_fit(candidate, image_aspect, eye_aspect)
    if kind != "resize":
        raise ValueError("kind must be 'pan', 'eye_pan' or 'resize'")
    if (not isinstance(corner_signs, (tuple, list)) or len(corner_signs) != 2
            or any(type(sign) is not int or sign not in (-1, 1)
                   for sign in corner_signs)):
        raise ValueError("corner_signs must contain two signs, each -1 or 1")
    sign_x, sign_y = corner_signs
    growth = ((delta_x * sign_x * fit_x + delta_y * sign_y * fit_y)
              / (fit_x * fit_x + fit_y * fit_y))
    origin = resolved_fit(entry, image_aspect, eye_aspect)
    return resolved_fit(origin.update({
        "scale": _clamp(origin.scale + growth, 0.5, 1.0),
    }), image_aspect, eye_aspect)


class EditTransaction:
    """An immutable entry snapshot, local draft, and single terminal action.

    A GUI captures ``draft`` at each pointer-down and supplies it as
    ``gesture_start`` to every preview for that gesture. Omitting it uses the
    entry snapshot, which is convenient for the first gesture. Committing only
    returns the chosen snapshot; the caller owns persistence and broadcasting.
    """

    def __init__(self, entry: Settings):
        self._entry = _settings(entry)
        self._draft = self._entry
        self._active = True

    @property
    def entry(self) -> Settings:
        return self._entry

    @property
    def draft(self) -> Settings:
        return self._draft

    @property
    def active(self) -> bool:
        return self._active

    def _require_active(self) -> None:
        if not self._active:
            raise RuntimeError("edit transaction is closed")

    def preview(self, kind: str, dx: float, dy: float,
                image_aspect: float, eye_aspect: float,
                corner_signs: tuple[int, int] = (1, 1), *,
                gesture_start: Settings | None = None,
                eye: int | None = None) -> Settings:
        self._require_active()
        origin = self._entry if gesture_start is None else gesture_start
        self._draft = dragged(origin, kind, dx, dy, image_aspect, eye_aspect,
                              corner_signs, eye=eye)
        return self._draft

    def commit(self) -> Settings:
        self._require_active()
        self._active = False
        return self._draft

    def discard(self) -> Settings:
        self._require_active()
        self._draft = self._entry
        self._active = False
        return self._entry
