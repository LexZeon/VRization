import Foundation
#if canImport(Darwin)
import Darwin
#elseif canImport(Glibc)
import Glibc
#endif

public enum ConnectionInput {
    /// Host is only an IP address or DNS name, never a URL, userinfo, port or path.
    /// Pairing codes stay strings so leading zeros survive unchanged.
    public static func url(host: String, port: String, token: String, settingsSchema: Int? = nil,
                           enhancedFirstPerson: Bool = false) throws -> URL {
        let host = host.trimmingCharacters(in: .whitespacesAndNewlines)
        let port = port.trimmingCharacters(in: .whitespacesAndNewlines)
        let token = token.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !host.isEmpty, host.utf8.count <= 253,
              !host.unicodeScalars.contains(where: { CharacterSet.whitespacesAndNewlines.contains($0) }),
              host.rangeOfCharacter(from: CharacterSet(charactersIn: "/\\@?#%")) == nil else {
            throw VRCoreError.invalid("Enter only the PC host name or IP address")
        }
        guard !port.isEmpty, port.utf8.allSatisfy({ (48...57).contains($0) }),
              let portNumber = Int(port), (1...65535).contains(portNumber) else {
            throw VRCoreError.invalid("Port must be from 1 to 65535")
        }
        guard token.utf8.count == 6, token.utf8.allSatisfy({ (48...57).contains($0) }) else {
            throw VRCoreError.invalid("Pairing code must contain six digits")
        }
        var unbracketed = host
        if host.hasPrefix("[") && host.hasSuffix("]") { unbracketed = String(host.dropFirst().dropLast()) }
        let isIPv6 = unbracketed.contains(":")
        if isIPv6 {
            var address = in6_addr()
            guard inet_pton(AF_INET6, unbracketed, &address) == 1 else { throw VRCoreError.invalid("Invalid IPv6 address") }
        } else {
            guard !host.contains("["), !host.contains("]") else { throw VRCoreError.invalid("Invalid host name") }
            let numeric = host.split(separator: ".", omittingEmptySubsequences: false)
            if host.utf8.allSatisfy({ (48...57).contains($0) || $0 == 46 }) {
                guard numeric.count == 4, numeric.allSatisfy({ !$0.isEmpty && $0.count <= 3 && (Int($0).map { (0...255).contains($0) } ?? false) }) else {
                    throw VRCoreError.invalid("Invalid IPv4 address")
                }
            } else {
                let dns = host.hasSuffix(".") ? String(host.dropLast()) : host
                let labels = dns.split(separator: ".", omittingEmptySubsequences: false)
                guard !labels.isEmpty, labels.allSatisfy({ label in
                    !label.isEmpty && label.utf8.count <= 63 && !label.hasPrefix("-") && !label.hasSuffix("-")
                        && label.utf8.allSatisfy { (65...90).contains($0) || (97...122).contains($0) || (48...57).contains($0) || $0 == 45 }
                }) else { throw VRCoreError.invalid("Invalid host name") }
            }
        }
        var components = URLComponents()
        components.scheme = "ws"
        components.host = isIPv6 ? "[\(unbracketed)]" : host
        components.port = portNumber
        components.path = "/ws"
        components.queryItems = [URLQueryItem(name: "token", value: token)]
        if let schema = settingsSchema {
            guard schema == VRProtocol.settingsSchema else { throw VRCoreError.invalid("Unsupported settings schema") }
            components.queryItems?.append(URLQueryItem(name: "settingsSchema", value: String(schema)))
        }
        if enhancedFirstPerson { components.queryItems?.append(URLQueryItem(name: "enhancedFirstPerson", value: "1")) }
        guard let url = components.url else { throw VRCoreError.invalid("Invalid connection address") }
        return url
    }
}
