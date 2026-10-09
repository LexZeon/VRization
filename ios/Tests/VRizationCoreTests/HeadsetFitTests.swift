import XCTest
@testable import VRizationCore

final class HeadsetFitTests: XCTestCase {
    func testTouchPixelsNormalizeHorizontalDirectlyAndVerticalUpward() throws {
        XCTAssertEqual(try HeadsetFit.touchDelta(screenDelta: FitPoint(x: -20, y: 20), eyeSize: FitPoint(x: 200, y: 400)), FitPoint(x: -0.2, y: -0.1))
        XCTAssertEqual(try HeadsetFit.touchDelta(screenDelta: FitPoint(x: 20, y: -20), eyeSize: FitPoint(x: 200, y: 400)), FitPoint(x: 0.2, y: 0.1))
        XCTAssertThrowsError(try HeadsetFit.touchDelta(screenDelta: FitPoint(x: .nan, y: 0), eyeSize: FitPoint(x: 200, y: 400)))
        XCTAssertThrowsError(try HeadsetFit.touchDelta(screenDelta: FitPoint(x: 0, y: 0), eyeSize: FitPoint(x: 0, y: 400)))
    }
    func testMirroredPanAllFourDirectionsKeepsOffsetXAndOtherSettings() throws {
        let entry = try VRSettings().applying(["eyeSeparation": 0.1, "offsetX": 0.12, "offsetY": -0.1, "distortion": 0.3, "mode": "cinema"])
        for (eye, dx, expected) in [(-1.0, -0.05, 0.15), (-1.0, 0.05, 0.05), (1.0, 0.05, 0.15), (1.0, -0.05, 0.05)] {
            let result = try HeadsetFit.mirroredPan(entry: entry, delta: FitPoint(x: dx, y: 0.08), eyeSign: eye,
                imageAspect: 2, eyeAspect: 1)
            XCTAssertEqual(result.eyeSeparation, expected, accuracy: 0.000001)
            XCTAssertEqual(result.offsetY, -0.02, accuracy: 0.000001)
            var preserved = result; preserved.eyeSeparation = entry.eyeSeparation; preserved.offsetY = entry.offsetY
            XCTAssertEqual(preserved, entry)
        }
    }
    func testMirroredPanClampsSpacingAndHeightAndRejectsInvalidEye() throws {
        let entry = try VRSettings().applying(["offsetX": 0.2, "eyeSeparation": 0.1])
        let wide = try HeadsetFit.mirroredPan(entry: entry, delta: FitPoint(x: -1, y: 1), eyeSign: -1, imageAspect: 2, eyeAspect: 1)
        let narrow = try HeadsetFit.mirroredPan(entry: entry, delta: FitPoint(x: -1, y: -1), eyeSign: 1, imageAspect: 2, eyeAspect: 1)
        XCTAssertEqual(wide.eyeSeparation, 0.2); XCTAssertEqual(wide.offsetY, 0.3)
        XCTAssertEqual(narrow.eyeSeparation, -0.15, accuracy: 0.000001); XCTAssertEqual(narrow.offsetY, -0.3)
        XCTAssertEqual(wide.offsetX, 0.2); XCTAssertEqual(narrow.offsetX, 0, accuracy: 0.000001)
        XCTAssertThrowsError(try HeadsetFit.mirroredPan(entry: entry, delta: FitPoint(x: 0, y: 0), eyeSign: 0, imageAspect: 2, eyeAspect: 1))
        XCTAssertThrowsError(try HeadsetFit.mirroredPan(entry: entry, delta: FitPoint(x: .nan, y: 0), eyeSign: 1, imageAspect: 2, eyeAspect: 1))
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
    func testResizeKeepsPlacementExceptAtTheSeamBoundary() throws {
        let start = try VRSettings().applying(["offsetX": 0.3, "offsetY": -0.3])
        let small = try HeadsetFit.resize(entry: start, delta: FitPoint(x: -10, y: -10), cornerSign: FitPoint(x: 1, y: 1), imageAspect: 1, eyeAspect: 1)
        let big = try HeadsetFit.resize(entry: start, delta: FitPoint(x: 10, y: 10), cornerSign: FitPoint(x: 1, y: 1), imageAspect: 1, eyeAspect: 1)
        XCTAssertEqual(small.scale, 0.5); XCTAssertEqual(big.scale, 1)
        XCTAssertEqual(small.offsetX, 0.18, accuracy: 0.000001)
        XCTAssertEqual(big.offsetX, 0.03, accuracy: 0.000001); XCTAssertEqual(big.offsetY, -0.3)
    }
    func testSmallAndPortraitImagesJoinWithoutCrossingEitherViewport() throws {
        let entry = try VRSettings().applying(["scale": 0.5, "eyeSeparation": -1.0, "offsetX": 0.3, "offsetY": 0.1])
        for (imageAspect, expectedSeparation) in [(2.0, -0.5), (0.5, -0.75)] {
            let result = try HeadsetFit.resolvedFit(settings: entry, imageAspect: imageAspect, eyeAspect: 1)
            XCTAssertEqual(result.eyeSeparation, expectedSeparation, accuracy: 0.000001)
            XCTAssertEqual(result.offsetX, 0, accuracy: 0.000001); XCTAssertEqual(result.offsetY, 0.1)
            let left = try HeadsetFit.eyeRect(settings: result, imageAspect: imageAspect, eyeAspect: 1, eyeSign: -1)
            let right = try HeadsetFit.eyeRect(settings: result, imageAspect: imageAspect, eyeAspect: 1, eyeSign: 1)
            XCTAssertEqual(left.center.x + left.halfSize.x, 1, accuracy: 0.000001)
            XCTAssertEqual(right.center.x - right.halfSize.x, -1, accuracy: 0.000001)
        }
    }
    func testNearContactHorizontalOffsetConsumesOnlyRemainingGap() throws {
        let entry = try VRSettings().applying(["scale": 0.5, "eyeSeparation": -0.4, "offsetX": 0.3])
        let result = try HeadsetFit.resolvedFit(settings: entry, imageAspect: 2, eyeAspect: 1)
        XCTAssertEqual(result.eyeSeparation, -0.4); XCTAssertEqual(result.offsetX, 0.1, accuracy: 0.000001)
        let contact = try HeadsetFit.mirroredPan(entry: entry, delta: FitPoint(x: 0.2, y: 0), eyeSign: -1,
            imageAspect: 2, eyeAspect: 1)
        XCTAssertEqual(contact.eyeSeparation, -0.5); XCTAssertEqual(contact.offsetX, 0)
    }
    func testEnlargingAJoinedImageMovesSpacingOutwardAndKeepsContact() throws {
        let entry = try VRSettings().applying(["scale": 0.5, "eyeSeparation": -0.5, "offsetY": 0.1,
                                               "mode": "fps", "distortion": 0.2])
        let result = try HeadsetFit.resize(entry: entry, delta: FitPoint(x: 0.2, y: 0.2), cornerSign: FitPoint(x: 1, y: 1),
            imageAspect: 1, eyeAspect: 1)
        XCTAssertEqual(result.scale, 0.7, accuracy: 0.000001)
        XCTAssertEqual(result.eyeSeparation, -0.3, accuracy: 0.000001)
        XCTAssertEqual(result.offsetX, 0); XCTAssertEqual(result.offsetY, 0.1)
        XCTAssertEqual(result.mode, "fps"); XCTAssertEqual(result.distortion, 0.2)
        let smaller = try HeadsetFit.resize(entry: result, delta: FitPoint(x: -0.2, y: -0.2), cornerSign: FitPoint(x: 1, y: 1),
            imageAspect: 1, eyeAspect: 1)
        XCTAssertEqual(smaller.scale, 0.5, accuracy: 0.000001)
        XCTAssertEqual(smaller.eyeSeparation, result.eyeSeparation)
    }
    func testSignedSeparationRoundTripsAndStillRejectsOutOfRangeOrBoolean() throws {
        for separation in [-1.0, -0.75, -0.5, 0.2] {
            let settings = try VRSettings().applying(["eyeSeparation": separation])
            XCTAssertEqual(try VRSettings.decode(JSONEncoder().encode(settings)), settings)
        }
        let badValues: [Any] = [-1.01, 0.21, true]
        for bad in badValues { XCTAssertThrowsError(try VRSettings().applying(["eyeSeparation": bad])) }
    }
    func testInvalidGeometryAndNonFiniteDeltasAreRejected() {
        for aspect in [0, -1, Double.nan, Double.infinity] { XCTAssertThrowsError(try HeadsetFit.fit(imageAspect: aspect, eyeAspect: 1)) }
        XCTAssertThrowsError(try HeadsetFit.pan(entry: VRSettings(), delta: FitPoint(x: .nan, y: 0)))
        XCTAssertThrowsError(try HeadsetFit.resize(entry: VRSettings(), delta: FitPoint(x: 0, y: .infinity), cornerSign: FitPoint(x: 1, y: 1), imageAspect: 1, eyeAspect: 1))
        XCTAssertThrowsError(try HeadsetFit.resize(entry: VRSettings(), delta: FitPoint(x: 0, y: 0), cornerSign: FitPoint(x: 0, y: 1), imageAspect: 1, eyeAspect: 1))
    }
}
