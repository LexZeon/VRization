// swift-tools-version:5.3
import PackageDescription

let package = Package(
    name: "VRizationCore",
    platforms: [.iOS(.v13), .macOS(.v10_15)],
    products: [.library(name: "VRizationCore", targets: ["VRizationCore"])],
    targets: [
        .target(name: "VRizationCore"),
        .testTarget(name: "VRizationCoreTests", dependencies: ["VRizationCore"])
    ],
    swiftLanguageVersions: [.v5]
)
