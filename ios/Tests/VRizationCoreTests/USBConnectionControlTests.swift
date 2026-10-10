import XCTest
@testable import VRizationCore

final class USBConnectionControlTests: XCTestCase {
    func testExactFramedConnectRequestRoundTrips() throws {
        let frame = USBFrame(kind: .json, payload: USBConnectionControl.connectMessage())
        let wire = try USBFraming.encode(frame)
        try USBConnectionControl.validateConnect(USBFraming.decode(body: Data(wire.dropFirst(4))))
        XCTAssertEqual(USBConnectionControl.port, 18767)
    }
    func testOnlyAnExplicitConnectControlIsAccepted() {
        for text in ["{}", "{\"v\":true,\"type\":\"connect\"}", "{\"v\":2,\"type\":\"connect\"}",
                     "{\"v\":1,\"type\":\"pose\"}", "{\"v\":1,\"type\":\"connect\",\"arm\":true}"] {
            XCTAssertThrowsError(try USBConnectionControl.validateConnect(USBFrame(kind: .json, payload: Data(text.utf8))))
        }
        XCTAssertThrowsError(try USBConnectionControl.validateConnect(USBFrame(kind: .jpeg, payload: USBConnectionControl.connectMessage())))
    }
    func testStopIsControlOnlyAndAcknowledgmentIsNotAnAction() throws {
        let stop = USBFrame(kind: .json, payload: USBConnectionControl.stopMessage())
        XCTAssertEqual(try USBConnectionControl.action(stop), .stop)
        XCTAssertThrowsError(try USBConnectionControl.validateConnect(stop))
        XCTAssertThrowsError(try USBConnectionControl.action(USBFrame(kind: .json, payload: USBConnectionControl.stoppedMessage())))
    }
}
