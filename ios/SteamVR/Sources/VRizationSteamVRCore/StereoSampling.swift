import Foundation
import VRizationCore

public struct StereoEyeSampling: Equatable {
    public let contentAspect: Double
    public let uvMinimum: FitPoint
    public let uvMaximum: FitPoint
    public let uvOriginX: Double
    public let uvScaleX: Double
    public static func resolve(width: Int, height: Int, eye: Int, layout: StreamLayout) throws -> StereoEyeSampling {
        guard width > 0, height > 0, eye == 0 || eye == 1,
              layout != .sbs || width >= 2 && width % 2 == 0 else {
            throw SteamVRSessionError.invalid("Invalid eye raster dimensions")
        }
        let packed = layout == .sbs
        let eyeWidth = packed ? width / 2 : width
        let origin = packed ? Double(eye) / 2 : 0
        let scale = packed ? 0.5 : 1.0
        return StereoEyeSampling(contentAspect: Double(eyeWidth)/Double(height),
            uvMinimum: FitPoint(x: origin + 0.5/Double(width), y: 0.5/Double(height)),
            uvMaximum: FitPoint(x: origin + scale - 0.5/Double(width), y: 1-0.5/Double(height)),
            uvOriginX: origin, uvScaleX: scale)
    }
    public func uv(_ point: FitPoint) throws -> FitPoint {
        guard point.x.isFinite, point.y.isFinite else { throw SteamVRSessionError.invalid("Nonfinite source UV") }
        return FitPoint(x: min(uvMaximum.x, max(uvMinimum.x, uvOriginX + point.x*uvScaleX)),
                        y: min(uvMaximum.y, max(uvMinimum.y, point.y)))
    }
}

/// Only rendering geometry changes; the user's persisted source mode is retained.
public enum SteamVRGeometry {
    public static func renderSettings(_ settings: VRSettings, layout: StreamLayout) -> VRSettings {
        var result = settings
        if layout == .sbs { result.mode = "full" }
        return result
    }
    public static func restoringMode(_ geometry: VRSettings, from profile: VRSettings) -> VRSettings {
        var result = geometry; result.mode = profile.mode; return result
    }
}
