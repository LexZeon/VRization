import XCTest
@testable import VRizationCore

final class USBFramingTests: XCTestCase {
    func testBigEndianLengthIncludesKind() throws {
        let frame = USBFrame(kind: .json, payload: Data("{}".utf8))
        let data = try USBFraming.encode(frame)
        XCTAssertEqual(Array(data.prefix(5)), [0,0,0,3,1])
        XCTAssertEqual(try USBFraming.length(fromHeader: Data(data.prefix(4))), 3)
        XCTAssertEqual(try USBFraming.decode(body: Data(data.dropFirst(4))), frame)
    }
    func testEveryByteFragmentedAndCoalescedFrames() throws {
        let a = USBFrame(kind: .json, payload: Data("{\"v\":1}".utf8))
        let b = USBFrame(kind: .jpeg, payload: Data([255,216,255,217]))
        let wire = try USBFraming.encode(a) + USBFraming.encode(b)
        var decoder = USBFrameDecoder(), received: [USBFrame] = []
        for byte in wire { received += try decoder.feed(Data([byte])) }
        XCTAssertEqual(received, [a,b])
        var coalesced = USBFrameDecoder()
        XCTAssertEqual(try coalesced.feed(wire), [a,b])
    }
    func testRejectsInvalidLengthAndKindWithoutResynchronizing() throws {
        let invalidHeaders: [[UInt8]] = [[0,0,0,0], [0,128,0,1], [255,255,255,255]]
        for header in invalidHeaders {
            XCTAssertThrowsError(try USBFraming.length(fromHeader: Data(header)))
        }
        var decoder = USBFrameDecoder()
        XCTAssertThrowsError(try decoder.feed(Data([0,0,0,1,3])))
        XCTAssertThrowsError(try decoder.feed(Data([0,0,0,1,2])))
        decoder.reset()
        XCTAssertEqual(try decoder.feed(Data([0,0,0,1,2])), [USBFrame(kind: .jpeg, payload: Data())])
    }
    func testMaximumBodyAndUTF8TextLimit() throws {
        XCTAssertEqual(try USBFraming.length(fromHeader: Data([0,128,0,0])), USBFraming.maximumLength)
        XCTAssertThrowsError(try USBFraming.encode(USBFrame(kind: .json, payload: Data(repeating: 32, count: 16385))))
        XCTAssertThrowsError(try USBFraming.decode(body: Data([1,255])))
        let large = USBFrame(kind: .jpeg, payload: Data(repeating: 0, count: USBFraming.maximumLength-1))
        XCTAssertEqual(try USBFraming.encode(large).count, USBFraming.maximumLength+4)
    }
}
