import XCTest
@testable import VRizationCore

final class HeadsetFitTests: XCTestCase {
    func testMobileHorizontalTouchIsOppositeAndVerticalFollowsFinger() throws {
        XCTAssertEqual(try HeadsetFit.mobilePanDelta(screenDelta: FitPoint(x: -20, y: 20), eyeSize: FitPoint(x: 200, y: 400)), FitPoint(x: 0.2, y: -0.1))
        XCTAssertEqual(try HeadsetFit.mobilePanDelta(screenDelta: FitPoint(x: 20, y: -20), eyeSize: FitPoint(x: 200, y: 400)), FitPoint(x: -0.2, y: 0.1))
        XCTAssertThrowsError(try HeadsetFit.mobilePanDelta(screenDelta: FitPoint(x: .nan, y: 0), eyeSize: FitPoint(x: 200, y: 400)))
        XCTAssertThrowsError(try HeadsetFit.mobilePanDelta(screenDelta: FitPoint(x: 0, y: 0), eyeSize: FitPoint(x: 0, y: 400)))
    }
    func testAspectFitForPortraitLandscapeAndSquare() throws {
        XCTAssertEqual(try HeadsetFit.fit(imageAspect: 2, eyeAspect: 1), FitPoint(x: 1, y: 0.5))
        XCTAssertEqual(try HeadsetFit.fit(imageAspect: 0.5, eyeAspect: 1), FitPoint(x: 0.5, y: 1))
        XCTAssertEqual(try HeadsetFit.fit(imageAspect: 1, eyeAspect: 1), FitPoint(x: 1, y: 1))
    }
    func testTwoEyesShareSizeAndTranslationWithOnlySeparationChanging() throws {
        let start = try VRSettings().applying(["offsetX": 0.1, "offsetY": -0.2, "eyeSeparation": 0.05])
        let left = try HeadsetFit.eyeRect(settings: start, imageAspect: 2, eyeAspect: 1, eyeSign: -1)
        let right = try HeadsetFit.eyeRect(settings: start, imageAspect: 2, eyeAspect: 1, eyeSign: 1)
        XCTAssertEqual(left.halfSize, right.halfSize)
        XCTAssertEqual(left.center.x, 0.05, accuracy: 0.000001)
        XCTAssertEqual(right.center.x, 0.15, accuracy: 0.000001)
        XCTAssertEqual(left.center.y, right.center.y)
    }
    func testPanUsesStartingSnapshotAndClampsBothAxes() throws {
        var start = VRSettings(); start.mode = "fps"; start.distortion = 0.3
        let next = try HeadsetFit.pan(entry: start, delta: FitPoint(x: 0.7, y: -0.9))
        XCTAssertEqual(next.offsetX, 0.3); XCTAssertEqual(next.offsetY, -0.3)
        XCTAssertEqual(next.scale, start.scale); XCTAssertEqual(next.mode, "fps"); XCTAssertEqual(next.distortion, 0.3)
        XCTAssertEqual(start.offsetX, 0)
    }
    func testEveryCornerResizesAroundFixedCenterAndPreservesOptics() throws {
        let start = try VRSettings().applying(["mode": "cinema", "scale": 0.7, "offsetX": 0.12, "offsetY": -0.07,
                                               "fov": 95.0, "distance": 6.0, "distortion": 0.3])
        for x in [-1.0, 1.0] { for y in [-1.0, 1.0] {
            let next = try HeadsetFit.resize(entry: start, delta: FitPoint(x: x * 0.1, y: y * 0.05),
                cornerSign: FitPoint(x: x, y: y), imageAspect: 2, eyeAspect: 1)
            XCTAssertEqual(next.scale, 0.8, accuracy: 0.000001)
            var unchanged = next; unchanged.scale = start.scale; XCTAssertEqual(unchanged, start)
        } }
    }
    func testResizeClampsWithoutImplicitlyMovingCenter() throws {
        let start = try VRSettings().applying(["offsetX": 0.3, "offsetY": -0.3])
        let small = try HeadsetFit.resize(entry: start, delta: FitPoint(x: -10, y: -10), cornerSign: FitPoint(x: 1, y: 1), imageAspect: 1, eyeAspect: 1)
        let big = try HeadsetFit.resize(entry: start, delta: FitPoint(x: 10, y: 10), cornerSign: FitPoint(x: 1, y: 1), imageAspect: 1, eyeAspect: 1)
        XCTAssertEqual(small.scale, 0.5); XCTAssertEqual(big.scale, 1)
        XCTAssertEqual(small.offsetX, 0.3); XCTAssertEqual(big.offsetY, -0.3)
    }
    func testInvalidGeometryAndNonFiniteDeltasAreRejected() {
        for aspect in [0, -1, Double.nan, Double.infinity] { XCTAssertThrowsError(try HeadsetFit.fit(imageAspect: aspect, eyeAspect: 1)) }
        XCTAssertThrowsError(try HeadsetFit.pan(entry: VRSettings(), delta: FitPoint(x: .nan, y: 0)))
        XCTAssertThrowsError(try HeadsetFit.resize(entry: VRSettings(), delta: FitPoint(x: 0, y: .infinity), cornerSign: FitPoint(x: 1, y: 1), imageAspect: 1, eyeAspect: 1))
        XCTAssertThrowsError(try HeadsetFit.resize(entry: VRSettings(), delta: FitPoint(x: 0, y: 0), cornerSign: FitPoint(x: 0, y: 1), imageAspect: 1, eyeAspect: 1))
    }
}
