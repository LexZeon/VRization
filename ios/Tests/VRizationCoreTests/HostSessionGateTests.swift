import XCTest
@testable import VRizationCore

/// Exercises the same fail-closed gate used before either transport reaches ImageIO.
final class HostSessionGateTests: XCTestCase {
    private func helloObject() throws -> [String: Any] {
        ["v": 1, "type": "hello", "name": "VRization", "version": "0.2.0",
         "settings": try JSONSerialization.jsonObject(with: JSONEncoder().encode(VRSettings())),
         "mouseArmed": false, "stream": ["codec": "jpeg", "fps": 30, "maxWidth": 1280]]
    }
    private func hello() throws -> Data { try JSONSerialization.data(withJSONObject: helloObject()) }
    private func settings() throws -> Data {
        try JSONSerialization.data(withJSONObject: ["v": 1, "type": "settings", "revision": 1, "clientSeq": 2,
            "settings": JSONSerialization.jsonObject(with: JSONEncoder().encode(VRSettings()))])
    }

    func testOnlyValidatedHelloEstablishesSessionThenMessagesAndVideoAreAccepted() throws {
        var gate = HostSessionGate()
        XCTAssertFalse(gate.isEstablished)
        guard case .established(let host) = try gate.receiveText(hello()) else { return XCTFail("Expected one establishment") }
        XCTAssertEqual(host.stream.codec, "jpeg")
        XCTAssertTrue(gate.isEstablished)
        XCTAssertNoThrow(try gate.receiveJPEG(byteCount: 4))
        XCTAssertNoThrow(try gate.receiveJPEG(byteCount: HostSessionGate.maximumJPEGBytes))
        XCTAssertEqual(try gate.receiveText(Data("{\"v\":1,\"type\":\"pong\"}".utf8)), .message(.pong))
        guard case .message(.settings(let update)) = try gate.receiveText(settings()) else { return XCTFail("Expected settings") }
        XCTAssertEqual(update.clientSeq, 2)
        XCTAssertEqual(update.revision, 1)
    }

    func testPreHelloJPEGIsRejectedAndCannotBeRescuedByLaterHello() throws {
        var gate = HostSessionGate()
        XCTAssertThrowsError(try gate.receiveJPEG(byteCount: 100))
        XCTAssertFalse(gate.isEstablished)
        XCTAssertThrowsError(try gate.receiveText(hello()))
        gate.reset()
        XCTAssertNoThrow(try gate.receiveText(hello()))
        XCTAssertTrue(gate.isEstablished)
    }

    func testSettingsPongAndErrorCannotSubstituteForHandshake() throws {
        let messages = [try settings(), Data("{\"v\":1,\"type\":\"pong\"}".utf8),
                        Data("{\"v\":1,\"type\":\"error\",\"message\":\"rejected\"}".utf8)]
        for message in messages {
            var gate = HostSessionGate()
            XCTAssertThrowsError(try gate.receiveText(message))
            XCTAssertFalse(gate.isEstablished)
            XCTAssertThrowsError(try gate.receiveText(hello()))
        }
    }

    func testMalformedVersionCodecJSONAndOversizedTextPoisonBothSessionPhases() throws {
        var wrongVersion = try helloObject(); wrongVersion["v"] = 2
        var wrongCodec = try helloObject(); wrongCodec["stream"] = ["codec": "h264", "fps": 30, "maxWidth": 1280]
        let invalid = [try JSONSerialization.data(withJSONObject: wrongVersion),
                       try JSONSerialization.data(withJSONObject: wrongCodec), Data("{".utf8), Data([0xff]),
                       Data(repeating: 32, count: VRProtocol.maximumTextBytes + 1)]
        for alreadyEstablished in [false, true] {
            for data in invalid {
                var gate = HostSessionGate()
                if alreadyEstablished { _ = try gate.receiveText(hello()) }
                XCTAssertThrowsError(try gate.receiveText(data))
                XCTAssertFalse(gate.isEstablished)
                XCTAssertThrowsError(try gate.receiveJPEG(byteCount: 100))
                XCTAssertThrowsError(try gate.receiveText(hello()))
            }
        }
    }

    func testDuplicateHelloNeverEstablishesOrResetsSessionTwice() throws {
        var gate = HostSessionGate()
        _ = try gate.receiveText(hello())
        XCTAssertThrowsError(try gate.receiveText(hello()))
        XCTAssertFalse(gate.isEstablished)
        XCTAssertThrowsError(try gate.receiveJPEG(byteCount: 100))
    }

    func testInvalidFrameLengthsCloseAnEstablishedSession() throws {
        for count in [-1, 0, 3, HostSessionGate.maximumJPEGBytes + 1] {
            var gate = HostSessionGate()
            _ = try gate.receiveText(hello())
            XCTAssertThrowsError(try gate.receiveJPEG(byteCount: count))
            XCTAssertFalse(gate.isEstablished)
            XCTAssertThrowsError(try gate.receiveText(hello()))
        }
    }

    func testNewTransportMustPerformItsOwnHandshake() throws {
        var gate = HostSessionGate()
        _ = try gate.receiveText(hello())
        gate.reset()
        XCTAssertFalse(gate.isEstablished)
        XCTAssertThrowsError(try gate.receiveJPEG(byteCount: 100))
        gate.reset()
        guard case .established = try gate.receiveText(hello()) else { return XCTFail("New session must establish once") }
    }
}
