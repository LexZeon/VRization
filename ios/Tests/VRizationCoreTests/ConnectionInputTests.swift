import XCTest
@testable import VRizationCore

final class ConnectionInputTests: XCTestCase {
    func testIPv4HostnameAndLeadingZeroPairingCode() throws {
        let url = try ConnectionInput.url(host: " 192.168.1.2 ", port: "8765", token: "001234")
        XCTAssertEqual(url.absoluteString, "ws://192.168.1.2:8765/ws?token=001234")
        XCTAssertEqual(try ConnectionInput.url(host: "my-pc.local", port: "65535", token: "000000").host, "my-pc.local")
        XCTAssertEqual(try ConnectionInput.url(host: "DESKTOP", port: "1", token: "123456").host?.lowercased(), "desktop")
    }
    func testIPv6WithAndWithoutBrackets() throws {
        for host in ["::1", "[::1]", "fe80::1234", "2001:db8::1"] {
            let url = try ConnectionInput.url(host: host, port: "8765", token: "000001")
            XCTAssertTrue(url.absoluteString.hasPrefix("ws://["))
            XCTAssertTrue(url.absoluteString.hasSuffix(":8765/ws?token=000001"))
        }
    }
    func testRejectsURLsAndHostSyntaxThatCouldAlterDestinationOrLeakToken() throws {
        for host in ["", "ws://pc", "https://pc", "user@pc", "pc/ws", "pc\\ws", "pc?token=123456", "pc#part",
                     "pc:8765", "pc name", "pc\nname", "[::1]:8765", "::::", "fe80::1%en0", "999.1.1.1",
                     "192.168.1", "a..local", "-pc.local", "pc-.local", "pc_local"] {
            XCTAssertThrowsError(try ConnectionInput.url(host: host, port: "8765", token: "123456"), "Accepted \(host)")
        }
    }
    func testPortAndCodeAreASCIIAndStrictlyBounded() throws {
        for port in ["", "0", "65536", "-1", "+80", "80.0", "８０", "80/path"] {
            XCTAssertThrowsError(try ConnectionInput.url(host: "pc.local", port: port, token: "123456"))
        }
        for token in ["", "12345", "1234567", "１２３４５６", "123 45", "12&345", "12345a"] {
            XCTAssertThrowsError(try ConnectionInput.url(host: "pc.local", port: "8765", token: token))
        }
    }
}
