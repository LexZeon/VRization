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
    /// Mobile touch adapter: horizontal panning is opposite the finger;
    /// vertical follows it. Core pan/resize retain ordinary normalized axes.
    public static func mobilePanDelta(screenDelta: FitPoint, eyeSize: FitPoint) throws -> FitPoint {
        guard screenDelta.x.isFinite, screenDelta.y.isFinite,
              eyeSize.x.isFinite, eyeSize.y.isFinite, eyeSize.x > 0, eyeSize.y > 0 else {
            throw VRCoreError.invalid("Invalid touch geometry")
        }
        let delta = FitPoint(x: -2 * screenDelta.x / eyeSize.x, y: -2 * screenDelta.y / eyeSize.y)
        guard delta.x.isFinite, delta.y.isFinite else { throw VRCoreError.invalid("Invalid touch delta") }
        return delta
    }
    public static func fit(imageAspect: Double, eyeAspect: Double) throws -> FitPoint {
        guard imageAspect.isFinite, eyeAspect.isFinite, imageAspect > 0, eyeAspect > 0 else {
            throw VRCoreError.invalid("Invalid preview aspect ratio")
        }
        return FitPoint(x: min(1, imageAspect / eyeAspect), y: min(1, eyeAspect / imageAspect))
    }
    public static func eyeRect(settings: VRSettings, imageAspect: Double, eyeAspect: Double, eyeSign: Double) throws -> FitRect {
        _ = try settings.validated()
        guard eyeSign == -1 || eyeSign == 1 else { throw VRCoreError.invalid("Invalid eye sign") }
        let fitted = try fit(imageAspect: imageAspect, eyeAspect: eyeAspect)
        return FitRect(center: FitPoint(x: settings.offsetX + eyeSign * settings.eyeSeparation, y: settings.offsetY),
                       halfSize: FitPoint(x: fitted.x * settings.scale, y: fitted.y * settings.scale))
    }
    public static func pan(entry: VRSettings, delta: FitPoint) throws -> VRSettings {
        _ = try entry.validated()
        let x = entry.offsetX + delta.x, y = entry.offsetY + delta.y
        guard delta.x.isFinite, delta.y.isFinite, x.isFinite, y.isFinite else { throw VRCoreError.invalid("Invalid drag delta") }
        var result = entry
        result.offsetX = min(0.3, max(-0.3, x)); result.offsetY = min(0.3, max(-0.3, y))
        return result
    }
    /// Resize around the existing center. Offsets and all optical/mode settings stay unchanged.
    public static func resize(entry: VRSettings, delta: FitPoint, cornerSign: FitPoint,
                              imageAspect: Double, eyeAspect: Double) throws -> VRSettings {
        _ = try entry.validated()
        guard delta.x.isFinite, delta.y.isFinite,
              abs(cornerSign.x) == 1, abs(cornerSign.y) == 1 else { throw VRCoreError.invalid("Invalid corner drag") }
        let fitted = try fit(imageAspect: imageAspect, eyeAspect: eyeAspect)
        let next = entry.scale + (cornerSign.x * delta.x * fitted.x + cornerSign.y * delta.y * fitted.y)
            / (fitted.x * fitted.x + fitted.y * fitted.y)
        guard next.isFinite else { throw VRCoreError.invalid("Invalid resize delta") }
        var result = entry; result.scale = min(1, max(0.5, next)); return result
    }
}
