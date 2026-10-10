import Foundation
import VRizationCore

/// Hamilton quaternion [x,y,z,w], right handed: +X right, +Y up, -Z forward.
public struct HMDQuaternion: Equatable {
    public let x: Double, y: Double, z: Double, w: Double
    public var xyzw: [Double] { [x, y, z, w] }
    public static let identity = HMDQuaternion(x: 0, y: 0, z: 0, w: 1)
    public init(x: Double, y: Double, z: Double, w: Double) { self.x = x; self.y = y; self.z = z; self.w = w }
    public func validated() throws -> HMDQuaternion {
        let norm = x*x + y*y + z*z + w*w
        guard xyzw.allSatisfy({ $0.isFinite }), abs(norm - 1) <= 0.00001 else {
            throw SteamVRSessionError.invalid("HMD quaternion must be finite and unit length")
        }
        return self
    }
    public func dot(_ other: HMDQuaternion) -> Double { x*other.x + y*other.y + z*other.z + w*other.w }
    public func signAligned(to previous: HMDQuaternion?) -> HMDQuaternion {
        let negative = previous.map { dot($0) < 0 } ?? (w < 0)
        return negative ? HMDQuaternion(x: -x, y: -y, z: -z, w: -w) : self
    }
    public func matrix() throws -> [Double] {
        _ = try validated()
        return [1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w),
                2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w),
                2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]
    }
    public static func fromRotation(_ matrix: [Double]) throws -> HMDQuaternion {
        // Stable core validates proper orthonormal rotations before recentering.
        _ = try PoseMath.screenToWorld(referenceToDevice: matrix, landscapeLeft: false)
        let m = matrix
        var x = 0.0, y = 0.0, z = 0.0, w = 0.0
        let trace = m[0] + m[4] + m[8]
        if trace > 0 {
            let s = sqrt(trace + 1) * 2
            w = s/4; x = (m[7]-m[5])/s; y = (m[2]-m[6])/s; z = (m[3]-m[1])/s
        } else if m[0] > m[4] && m[0] > m[8] {
            let s = sqrt(max(0, 1+m[0]-m[4]-m[8]))*2
            x = s/4; y = (m[1]+m[3])/s; z = (m[2]+m[6])/s; w = (m[7]-m[5])/s
        } else if m[4] > m[8] {
            let s = sqrt(max(0, 1+m[4]-m[0]-m[8]))*2
            x = (m[1]+m[3])/s; y = s/4; z = (m[5]+m[7])/s; w = (m[2]-m[6])/s
        } else {
            let s = sqrt(max(0, 1+m[8]-m[0]-m[4]))*2
            x = (m[2]+m[6])/s; y = (m[5]+m[7])/s; z = s/4; w = (m[3]-m[1])/s
        }
        let norm = sqrt(x*x+y*y+z*z+w*w)
        guard norm.isFinite, norm > 0 else { throw SteamVRSessionError.invalid("Degenerate rotation quaternion") }
        return try HMDQuaternion(x: x/norm, y: y/norm, z: z/norm, w: w/norm).validated()
    }
}

/// R0-transpose * R from fused Core Motion matrices, with no Euler reconstruction.
public struct HMDQuaternionCenter {
    private var origin: [Double]?
    private var previous: HMDQuaternion?
    public init() {}
    public mutating func recenter() { origin = nil; previous = nil }
    public mutating func sample(screenToWorld matrix: [Double]) throws -> HMDQuaternion {
        _ = try HMDQuaternion.fromRotation(matrix)
        guard let center = origin else { origin = matrix; previous = .identity; return .identity }
        let relative = try PoseMath.multiply(PoseMath.transpose(center), matrix)
        let result = try HMDQuaternion.fromRotation(relative).signAligned(to: previous)
        previous = result
        return result
    }
}
