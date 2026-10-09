import Foundation

/// Per-eye coordinates span -1...1, with positive Y pointing up.
public struct FitPoint: Equatable {
    public var x: Double, y: Double
    public init(x: Double, y: Double) { self.x = x; self.y = y }
}

public struct FitRect: Equatable {
    public let center: FitPoint, halfSize: FitPoint
}

/// The same geometry can be used by a native UI or an embedded game editor.
public enum HeadsetFit {
    /// Convert screen pixels (Y downward) to ordinary per-eye normalized axes.
    public static func touchDelta(screenDelta: FitPoint, eyeSize: FitPoint) throws -> FitPoint {
        guard screenDelta.x.isFinite, screenDelta.y.isFinite,
              eyeSize.x.isFinite, eyeSize.y.isFinite, eyeSize.x > 0, eyeSize.y > 0 else {
            throw VRCoreError.invalid("Invalid touch geometry")
        }
        let delta = FitPoint(x: 2 * screenDelta.x / eyeSize.x, y: -2 * screenDelta.y / eyeSize.y)
        guard delta.x.isFinite, delta.y.isFinite else { throw VRCoreError.invalid("Invalid touch delta") }
        return delta
    }
    /// Horizontal movement mirrors the other eye by changing separation only.
    /// Left eye dragged left / right eye dragged right widen the gap. Vertical
    /// movement translates both eyes. Near contact, the common horizontal offset
    /// is bounded by the remaining gap so neither inner edge crosses its viewport.
    public static func mirroredPan(entry: VRSettings, delta: FitPoint, eyeSign: Double,
                                   imageAspect: Double, eyeAspect: Double) throws -> VRSettings {
        let start = try resolvedFit(settings: entry, imageAspect: imageAspect, eyeAspect: eyeAspect)
        guard eyeSign == -1 || eyeSign == 1, delta.x.isFinite, delta.y.isFinite else {
            throw VRCoreError.invalid("Invalid mirrored drag")
        }
        let separation = start.eyeSeparation + eyeSign * delta.x, y = start.offsetY + delta.y
        guard separation.isFinite, y.isFinite else { throw VRCoreError.invalid("Invalid mirrored drag delta") }
        var result = start
        result.eyeSeparation = min(0.2, max(-1, separation)); result.offsetY = min(0.3, max(-0.3, y))
        return try resolvedFit(settings: result, imageAspect: imageAspect, eyeAspect: eyeAspect)
    }
    public static func fit(imageAspect: Double, eyeAspect: Double) throws -> FitPoint {
        guard imageAspect.isFinite, eyeAspect.isFinite, imageAspect > 0, eyeAspect > 0 else {
            throw VRCoreError.invalid("Invalid preview aspect ratio")
        }
        return FitPoint(x: min(1, imageAspect / eyeAspect), y: min(1, eyeAspect / imageAspect))
    }
    /// Resolve the desired placement against the current per-eye aspect ratio.
    /// Negative separation brings small images inward until their inner edges
    /// meet. A common horizontal offset consumes the remaining gap and reaches
    /// zero at contact. Wire/profile values remain independent of capture size.
    public static func resolvedFit(settings: VRSettings, imageAspect: Double, eyeAspect: Double) throws -> VRSettings {
        _ = try settings.validated()
        let fitted = try fit(imageAspect: imageAspect, eyeAspect: eyeAspect)
        let halfWidth = fitted.x * settings.scale
        var result = settings
        result.eyeSeparation = min(0.2, max(halfWidth - 1, settings.eyeSeparation))
        let gap = max(0, 1 + result.eyeSeparation - halfWidth)
        let offsetLimit = min(0.3, gap)
        result.offsetX = min(offsetLimit, max(-offsetLimit, settings.offsetX))
        return result
    }
    public static func eyeRect(settings: VRSettings, imageAspect: Double, eyeAspect: Double, eyeSign: Double) throws -> FitRect {
        let resolved = try resolvedFit(settings: settings, imageAspect: imageAspect, eyeAspect: eyeAspect)
        guard eyeSign == -1 || eyeSign == 1 else { throw VRCoreError.invalid("Invalid eye sign") }
        let fitted = try fit(imageAspect: imageAspect, eyeAspect: eyeAspect)
        return FitRect(center: FitPoint(x: resolved.offsetX + eyeSign * resolved.eyeSeparation, y: resolved.offsetY),
                       halfSize: FitPoint(x: fitted.x * resolved.scale, y: fitted.y * resolved.scale))
    }
    public static func pan(entry: VRSettings, delta: FitPoint) throws -> VRSettings {
        _ = try entry.validated()
        let x = entry.offsetX + delta.x, y = entry.offsetY + delta.y
        guard delta.x.isFinite, delta.y.isFinite, x.isFinite, y.isFinite else { throw VRCoreError.invalid("Invalid drag delta") }
        var result = entry
        result.offsetX = min(0.3, max(-0.3, x)); result.offsetY = min(0.3, max(-0.3, y))
        return result
    }
    /// Resize around the existing center, resolving placement only at the seam
    /// boundary. All optical/mode settings remain unchanged.
    public static func resize(entry: VRSettings, delta: FitPoint, cornerSign: FitPoint,
                              imageAspect: Double, eyeAspect: Double) throws -> VRSettings {
        _ = try entry.validated()
        guard delta.x.isFinite, delta.y.isFinite,
              abs(cornerSign.x) == 1, abs(cornerSign.y) == 1 else { throw VRCoreError.invalid("Invalid corner drag") }
        let fitted = try fit(imageAspect: imageAspect, eyeAspect: eyeAspect)
        let next = entry.scale + (cornerSign.x * delta.x * fitted.x + cornerSign.y * delta.y * fitted.y)
            / (fitted.x * fitted.x + fitted.y * fitted.y)
        guard next.isFinite else { throw VRCoreError.invalid("Invalid resize delta") }
        var result = try resolvedFit(settings: entry, imageAspect: imageAspect, eyeAspect: eyeAspect)
        result.scale = min(1, max(0.5, next))
        return try resolvedFit(settings: result, imageAspect: imageAspect, eyeAspect: eyeAspect)
    }
}
