import Foundation
import CoreFoundation

public enum VRCoreError: Error, LocalizedError, Equatable {
    case invalid(String)
    public var errorDescription: String? {
        switch self { case .invalid(let message): return message }
    }
}

/// Value semantics let a renderer keep a stable snapshot while controls are edited.
public struct VRSettings: Codable, Equatable {
    public var mode = "full"
    public var scale = 0.85
    public var offsetX = 0.0
    public var offsetY = 0.0
    public var eyeSeparation = 0.03
    public var fov = 80.0
    public var distance = 3.0
    public var distortion = 0.0
    public var sensitivity = 1000.0
    public var invertY = false

    public init() {}
    public static let defaults = VRSettings()
    internal static let names: Set<String> = ["mode", "scale", "offsetX", "offsetY", "eyeSeparation",
                                               "fov", "distance", "distortion", "sensitivity", "invertY"]

    public func validated() throws -> VRSettings {
        guard ["full", "cinema", "fps"].contains(mode) else { throw VRCoreError.invalid("Unknown viewing mode") }
        let values: [(String, Double, ClosedRange<Double>)] = [
            ("scale", scale, 0.5...1), ("offsetX", offsetX, -0.3...0.3),
            ("offsetY", offsetY, -0.3...0.3), ("eyeSeparation", eyeSeparation, -1...0.2),
            ("fov", fov, 50...110), ("distance", distance, 1...8),
            ("distortion", distortion, 0...0.5), ("sensitivity", sensitivity, 100...3000)
        ]
        for (name, value, bounds) in values {
            guard value.isFinite && bounds.contains(value) else { throw VRCoreError.invalid("Invalid setting: \(name)") }
        }
        return self
    }

    /// Apply a nonempty partial wire update atomically; no coercion or clamping.
    public func applying(_ patch: [String: Any]) throws -> VRSettings {
        guard !patch.isEmpty, Set(patch.keys).isSubset(of: Self.names) else {
            throw VRCoreError.invalid("Settings must be a nonempty object with known fields")
        }
        var result = self
        for (key, value) in patch {
            switch key {
            case "mode":
                guard let mode = value as? String else { throw VRCoreError.invalid("Mode must be a string") }
                result.mode = mode
            case "invertY": result.invertY = try WireValue.boolean(value, name: key)
            case "scale": result.scale = try WireValue.number(value, name: key)
            case "offsetX": result.offsetX = try WireValue.number(value, name: key)
            case "offsetY": result.offsetY = try WireValue.number(value, name: key)
            case "eyeSeparation": result.eyeSeparation = try WireValue.number(value, name: key)
            case "fov": result.fov = try WireValue.number(value, name: key)
            case "distance": result.distance = try WireValue.number(value, name: key)
            case "distortion": result.distortion = try WireValue.number(value, name: key)
            case "sensitivity": result.sensitivity = try WireValue.number(value, name: key)
            default: throw VRCoreError.invalid("Unknown setting")
            }
        }
        return try result.validated()
    }

    public static func decode(_ data: Data) throws -> VRSettings {
        return try JSONDecoder().decode(VRSettings.self, from: data)
    }

    internal static func complete(_ value: Any?) throws -> VRSettings {
        guard let object = value as? [String: Any], Set(object.keys) == names else {
            throw VRCoreError.invalid("Expected complete settings")
        }
        return try VRSettings().applying(object)
    }

    private struct Key: CodingKey {
        var stringValue: String
        var intValue: Int? { return nil }
        init?(stringValue: String) { self.stringValue = stringValue }
        init?(intValue: Int) { return nil }
    }
    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: Key.self)
        guard Set(container.allKeys.map { $0.stringValue }) == Self.names else {
            throw VRCoreError.invalid("Expected complete settings with known fields")
        }
        func key(_ name: String) -> Key { return Key(stringValue: name)! }
        mode = try container.decode(String.self, forKey: key("mode"))
        scale = try container.decode(Double.self, forKey: key("scale"))
        offsetX = try container.decode(Double.self, forKey: key("offsetX"))
        offsetY = try container.decode(Double.self, forKey: key("offsetY"))
        eyeSeparation = try container.decode(Double.self, forKey: key("eyeSeparation"))
        fov = try container.decode(Double.self, forKey: key("fov"))
        distance = try container.decode(Double.self, forKey: key("distance"))
        distortion = try container.decode(Double.self, forKey: key("distortion"))
        sensitivity = try container.decode(Double.self, forKey: key("sensitivity"))
        invertY = try container.decode(Bool.self, forKey: key("invertY"))
        self = try validated()
    }
    public func encode(to encoder: Encoder) throws {
        _ = try validated()
        var container = encoder.container(keyedBy: Key.self)
        func key(_ name: String) -> Key { return Key(stringValue: name)! }
        try container.encode(mode, forKey: key("mode"))
        try container.encode(scale, forKey: key("scale"))
        try container.encode(offsetX, forKey: key("offsetX"))
        try container.encode(offsetY, forKey: key("offsetY"))
        try container.encode(eyeSeparation, forKey: key("eyeSeparation"))
        try container.encode(fov, forKey: key("fov"))
        try container.encode(distance, forKey: key("distance"))
        try container.encode(distortion, forKey: key("distortion"))
        try container.encode(sensitivity, forKey: key("sensitivity"))
        try container.encode(invertY, forKey: key("invertY"))
    }
}

internal enum WireValue {
    static let maximumSequence: Int64 = 9_007_199_254_740_991
    static func boolean(_ value: Any, name: String) throws -> Bool {
        guard let number = value as? NSNumber, CFGetTypeID(number) == CFBooleanGetTypeID() else {
            throw VRCoreError.invalid("\(name) must be boolean")
        }
        return number.boolValue
    }
    static func number(_ value: Any, name: String) throws -> Double {
        guard let number = value as? NSNumber, CFGetTypeID(number) != CFBooleanGetTypeID(), number.doubleValue.isFinite else {
            throw VRCoreError.invalid("\(name) must be a finite number")
        }
        return number.doubleValue
    }
    static func integer(_ value: Any?, name: String) throws -> Int64 {
        guard let number = value as? NSNumber, CFGetTypeID(number) != CFBooleanGetTypeID(),
              !["f", "d"].contains(String(cString: number.objCType)),
              number.doubleValue >= 0, number.doubleValue <= Double(maximumSequence) else {
            throw VRCoreError.invalid("\(name) must be a nonnegative safe integer")
        }
        return number.int64Value
    }
    static func optionalInteger(_ object: [String: Any], key: String) throws -> Int64? {
        guard let value = object[key] else { return nil }
        return try integer(value, name: key)
    }
}
