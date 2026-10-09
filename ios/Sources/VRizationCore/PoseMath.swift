import Foundation

public struct Pose: Equatable {
    public let yaw: Double
    public let pitch: Double
    public let roll: Double
    public init(yaw: Double = 0, pitch: Double = 0, roll: Double = 0) {
        self.yaw = yaw; self.pitch = pitch; self.roll = roll
    }
}

public enum PoseMath {
    public static func wrap(_ radians: Double) throws -> Double {
        guard radians.isFinite else { throw VRCoreError.invalid("Angle must be finite") }
        var value = radians.truncatingRemainder(dividingBy: 2 * .pi)
        if value > .pi { value -= 2 * .pi }
        if value < -.pi { value += 2 * .pi }
        return value
    }
    public static func relative(_ current: Double, origin: Double) throws -> Double {
        return try wrap(current - origin)
    }

    /// Row-major screen-to-world rotation: yaw right, pitch up, roll clockwise.
    public static func rotation(yaw: Double, pitch: Double, roll: Double) throws -> [Double] {
        guard yaw.isFinite, pitch.isFinite, roll.isFinite else { throw VRCoreError.invalid("Angles must be finite") }
        let cy = cos(yaw), sy = sin(yaw), cp = cos(pitch), sp = sin(pitch), cr = cos(roll), sr = sin(roll)
        let y: [Double] = [cy, 0, -sy, 0, 1, 0, sy, 0, cy]
        let p: [Double] = [1, 0, 0, 0, cp, -sp, 0, sp, cp]
        let r: [Double] = [cr, sr, 0, -sr, cr, 0, 0, 0, 1]
        return try multiply(multiply(y, p), r)
    }
    public static func multiply(_ a: [Double], _ b: [Double]) throws -> [Double] {
        try validateElements(a); try validateElements(b)
        var result = Array(repeating: 0.0, count: 9)
        for row in 0..<3 { for col in 0..<3 { for inner in 0..<3 {
            result[row * 3 + col] += a[row * 3 + inner] * b[inner * 3 + col]
        } } }
        return result
    }
    public static func transpose(_ matrix: [Double]) throws -> [Double] {
        try validateElements(matrix)
        return [matrix[0], matrix[3], matrix[6], matrix[1], matrix[4], matrix[7], matrix[2], matrix[5], matrix[8]]
    }
    /// Input maps reference coordinates into portrait device coordinates. UIKit
    /// landscapeLeft means Home button left: screen x=+device y, screen y=-device x.
    /// The result maps landscape screen coordinates into the reference/world frame.
    public static func screenToWorld(referenceToDevice: [Double], landscapeLeft: Bool) throws -> [Double] {
        try validateRotation(referenceToDevice)
        let basis: [Double] = landscapeLeft ? [0, -1, 0, 1, 0, 0, 0, 0, 1] : [0, 1, 0, -1, 0, 0, 0, 0, 1]
        return try multiply(transpose(referenceToDevice), basis)
    }
    internal static func validateElements(_ matrix: [Double]) throws {
        guard matrix.count == 9, matrix.allSatisfy({ $0.isFinite }) else { throw VRCoreError.invalid("Expected finite 3 by 3 matrix") }
    }
    internal static func validateRotation(_ matrix: [Double]) throws {
        try validateElements(matrix)
        for row in 0..<3 { for other in row..<3 {
            var dot = 0.0
            for col in 0..<3 { dot += matrix[row * 3 + col] * matrix[other * 3 + col] }
            guard abs(dot - (row == other ? 1 : 0)) < 0.005 else { throw VRCoreError.invalid("Matrix must be an orthonormal rotation") }
        } }
        let determinant = matrix[0] * (matrix[4] * matrix[8] - matrix[5] * matrix[7])
            - matrix[1] * (matrix[3] * matrix[8] - matrix[5] * matrix[6])
            + matrix[2] * (matrix[3] * matrix[7] - matrix[4] * matrix[6])
        guard abs(determinant - 1) < 0.005 else { throw VRCoreError.invalid("Matrix must be a proper rotation") }
    }
}

/// Exact R0-transpose times R recentering; Euler subtraction is incorrect for a tilted center.
public struct RotationCenter {
    private var origin: [Double]?
    public init() {}
    public mutating func recenter() { origin = nil }
    public mutating func sample(screenToWorld matrix: [Double]) throws -> Pose {
        try PoseMath.validateRotation(matrix)
        guard let center = origin else { origin = matrix; return Pose() }
        let relative = try PoseMath.multiply(PoseMath.transpose(center), matrix)
        return Pose(yaw: atan2(-relative[2], relative[8]),
                    pitch: asin(max(-1, min(1, -relative[5]))),
                    roll: atan2(-relative[3], relative[4]))
    }
}
