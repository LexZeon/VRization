// swift-tools-version:5.5
import PackageDescription

let package = Package(
    name: "VRizationSteamVRCore",
    platforms: [.iOS(.v15), .macOS(.v10_15)],
    products: [.library(name: "VRizationSteamVRCore", targets: ["VRizationSteamVRCore"])],
    dependencies: [.package(path: "..")],
    targets: [
        .target(name: "VRizationSteamVRCore", dependencies: [.product(name: "VRizationCore", package: "ios")]),
        .testTarget(name: "VRizationSteamVRCoreTests", dependencies: ["VRizationSteamVRCore", .product(name: "VRizationCore", package: "ios")])
    ],
    swiftLanguageVersions: [.v5]
)
