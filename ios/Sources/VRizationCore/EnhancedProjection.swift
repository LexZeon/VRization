import Foundation

/// Inverse radial equidistant-to-rectilinear mapping used by the Metal shader.
/// This warps a flat image; it does not create depth or new scene information.
public enum EnhancedProjection {
    /// Per-eye local coordinates and source coordinates span -1...1 (Y up).
    /// Nil means the shader must output black, including rounded outer corners.
    public static func sample(point: FitPoint, fov: Double) throws -> FitPoint? {
        guard point.x.isFinite, point.y.isFinite, fov.isFinite, (50...110).contains(fov) else {
            throw VRCoreError.invalid("Invalid enhanced projection coordinates or field of view")
        }
        guard abs(point.x) <= 1, abs(point.y) <= 1 else { return nil }
        let radius = hypot(point.x, point.y)
        if radius < 0.000001 { return FitPoint(x: 0, y: 0) }
        let angle = fov * .pi / 360
        let factor = tan(radius * angle) / (radius * tan(angle))
        let source = FitPoint(x: point.x * factor, y: point.y * factor)
        guard source.x.isFinite, source.y.isFinite, abs(source.x) <= 1, abs(source.y) <= 1 else { return nil }
        return source
    }
}
