import Foundation

public struct USBFrame: Equatable {
    public enum Kind: UInt8 { case json = 1, jpeg = 2 }
    public let kind: Kind
    public let payload: Data
    public init(kind: Kind, payload: Data) { self.kind = kind; self.payload = payload }
}

public enum USBFraming {
    /// The length includes the kind byte and excludes the four-byte length prefix.
    public static let maximumLength = 8 * 1024 * 1024
    public static func length(fromHeader header: Data) throws -> Int {
        guard header.count == 4 else { throw VRCoreError.invalid("Expected four-byte USB header") }
        let length = header.reduce(UInt32(0)) { ($0 << 8) | UInt32($1) }
        guard length > 0, length <= UInt32(maximumLength) else { throw VRCoreError.invalid("Invalid USB frame length") }
        return Int(length)
    }
    public static func decode(body: Data) throws -> USBFrame {
        guard !body.isEmpty, body.count <= maximumLength,
              let kind = USBFrame.Kind(rawValue: body[body.startIndex]) else { throw VRCoreError.invalid("Invalid USB frame kind or length") }
        let payload = Data(body.dropFirst())
        if kind == .json {
            guard payload.count <= VRProtocol.maximumTextBytes, String(data: payload, encoding: .utf8) != nil
            else { throw VRCoreError.invalid("Expected bounded UTF-8 JSON") }
        }
        return USBFrame(kind: kind, payload: payload)
    }
    public static func encode(_ frame: USBFrame) throws -> Data {
        let length = frame.payload.count + 1
        guard length <= maximumLength else { throw VRCoreError.invalid("USB frame too large") }
        if frame.kind == .json {
            guard frame.payload.count <= VRProtocol.maximumTextBytes, String(data: frame.payload, encoding: .utf8) != nil
            else { throw VRCoreError.invalid("Expected bounded UTF-8 JSON") }
        }
        let n = UInt32(length)
        var result = Data([UInt8((n >> 24) & 255), UInt8((n >> 16) & 255), UInt8((n >> 8) & 255), UInt8(n & 255), frame.kind.rawValue])
        result.append(frame.payload)
        return result
    }
}

/// Incremental framing for embedders. Internal storage holds at most one bounded frame.
/// Invalid input poisons the decoder until reset, preventing accidental resynchronization.
public struct USBFrameDecoder {
    private var buffer = Data()
    private var expected: Int?
    private var failed = false
    public init() {}
    public mutating func reset() { self = USBFrameDecoder() }
    public mutating func feed(_ input: Data) throws -> [USBFrame] {
        guard !failed else { throw VRCoreError.invalid("Reset failed USB decoder before reuse") }
        do {
            var output: [USBFrame] = []
            var offset = input.startIndex
            while offset < input.endIndex {
                let goal = expected ?? 4
                let count = min(goal - buffer.count, input.distance(from: offset, to: input.endIndex))
                let end = input.index(offset, offsetBy: count)
                buffer.append(contentsOf: input[offset..<end]); offset = end
                if expected != nil, !buffer.isEmpty, USBFrame.Kind(rawValue: buffer[buffer.startIndex]) == nil {
                    throw VRCoreError.invalid("Invalid USB frame kind")
                }
                if buffer.count == goal {
                    if expected == nil { expected = try USBFraming.length(fromHeader: buffer); buffer.removeAll(keepingCapacity: false) }
                    else { output.append(try USBFraming.decode(body: buffer)); buffer = Data(); expected = nil }
                }
            }
            return output
        } catch {
            buffer = Data(); expected = nil; failed = true; throw error
        }
    }
}
