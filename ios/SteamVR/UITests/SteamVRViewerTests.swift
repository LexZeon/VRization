import XCTest

/// Real preview app + host protocol + Metal. Pixel source and USB enumeration
/// are synthetic; no physical iPhone, game, sensor bypass or driver registration.
final class SteamVRViewerTests: XCTestCase {
    private let app = XCUIApplication()
    private struct PoseRecord: Decodable { let q: [Double]?, seq: Int64, connected: Bool, paused: Bool }
    private struct RefreshRecord: Decodable { let epoch: Int64, requestId: Int64, paused: Bool }
    private struct Snapshot: Decodable {
        let fixtureReady: Bool, connected: Bool, settingsCount: Int, mouseMoves: [[Double]], poses: [PoseRecord]
        let epoch: Int64, paused: Bool
        let videoRefreshes: [RefreshRecord]
        let settings: Settings
    }
    private struct Settings: Decodable, Equatable {
        let mode: String
        let scale, offsetX, offsetY, eyeSeparation, fov, distance, distortion, sensitivity, stabilization: Double
        let invertY: Bool
    }
    private struct Rect: Decodable { let x, y, width, height: Double }
    override func setUpWithError() throws { continueAfterFailure = false }
    override func tearDownWithError() throws { app.terminate() }
    private func launch(_ transport: String) {
        app.launchArguments = ["--ui-testing", "--reset-preferences", "--transport", transport,
                               "--host", "127.0.0.1", "--port", "18785", "--code", "123456"]
        app.launch(); XCUIDevice.shared.orientation = .landscapeRight
        XCTAssertTrue(app.buttons["settings.hide"].waitForExistence(timeout: 10))
        let version = app.staticTexts["version.info"]
        XCTAssertTrue(version.label.contains("0.5.1")); XCTAssertTrue(version.label.contains("build 2"))
        XCTAssertTrue(app.buttons["connection.refresh"].isHittable)
    }
    private func waitContains(_ element: XCUIElement, _ text: String, timeout: TimeInterval = 20) {
        let predicate = NSPredicate(format: "label CONTAINS %@", text)
        let expectation = XCTNSPredicateExpectation(predicate: predicate, object: element)
        XCTAssertEqual(XCTWaiter.wait(for: [expectation], timeout: timeout), .completed)
    }
    private func reveal(_ element: XCUIElement) {
        let scroll = app.scrollViews["settings.scroll"]
        for _ in 0..<16 {
            if element.isHittable { return }
            let up = element.frame.midY >= scroll.frame.midY
            let a = scroll.coordinate(withNormalizedOffset: CGVector(dx: 0.98, dy: up ? 0.85 : 0.15))
            let b = scroll.coordinate(withNormalizedOffset: CGVector(dx: 0.98, dy: up ? 0.15 : 0.85))
            a.press(forDuration: 0.05, thenDragTo: b)
        }
        XCTAssertTrue(element.isHittable)
    }
    private func screenshot(_ name: String) {
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
    }
    private func observe(_ checkpoint: String? = nil, pauseTracking: Bool = false) throws -> Snapshot {
        let path = pauseTracking ? "pause-tracking" : (checkpoint == nil ? "snapshot" : "checkpoint")
        var request = URLRequest(url: URL(string: "http://127.0.0.1:18789/" + path)!)
        if pauseTracking { request.httpMethod = "POST" }
        else if let name = checkpoint {
            request.httpMethod = "POST"; request.httpBody = try JSONSerialization.data(withJSONObject: ["name": name])
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        let semaphore = DispatchSemaphore(value: 0)
        var body: Data?, failure: Error?
        URLSession.shared.dataTask(with: request) { data, _, error in body = data; failure = error; semaphore.signal() }.resume()
        XCTAssertEqual(semaphore.wait(timeout: .now() + 5), .success)
        if let error = failure { throw error }
        return try JSONDecoder().decode(Snapshot.self, from: XCTUnwrap(body))
    }
    private func connect() throws {
        let button = app.buttons["connection.toggle"]; reveal(button); button.tap()
        waitContains(app.staticTexts["connection.status"], "Connected.")
        waitContains(app.staticTexts["frame.status"], "1280 × 480")
        let descriptor = app.staticTexts["stream.session"].value as? String ?? ""
        XCTAssertTrue(descriptor.contains("accepted=true;layout=sbs;target=virtual-hmd"))
        let host = try observe(); XCTAssertTrue(host.connected); XCTAssertTrue(host.fixtureReady); XCTAssertTrue(host.mouseMoves.isEmpty)
    }
    private func showOverlay() {
        let surface = app.otherElements["vr.surface"]
        surface.coordinate(withNormalizedOffset: CGVector(dx: 0.94, dy: 0.82)).press(forDuration: 1.2)
    }
    private func assertEditorHalfImageAspect() throws {
        for eye in 0..<2 {
            let value = app.otherElements["editor.eye\(eye).interior"].value as? String
            let rect = try JSONDecoder().decode(Rect.self, from: XCTUnwrap(value?.data(using: .utf8)))
            XCTAssertGreaterThan(rect.width, 0); XCTAssertGreaterThan(rect.height, 0)
            XCTAssertEqual(rect.width / rect.height, 640.0/480, accuracy: 0.001)
        }
        let summary = app.staticTexts["editor.summary"].value as? String ?? ""
        XCTAssertTrue(summary.contains("fps_enhanced"))
    }
    private func editorSettings() throws -> Settings {
        let value = app.staticTexts["editor.summary"].value as? String
        return try JSONDecoder().decode(Settings.self, from: XCTUnwrap(value?.data(using: .utf8)))
    }
    private func waitEditorScaleLessThan(_ scale: Double) throws {
        let summary = app.staticTexts["editor.summary"]
        let predicate = NSPredicate { element, _ in
            guard let element = element as? XCUIElement,
                  let value = element.value as? String, let data = value.data(using: .utf8),
                  let draft = try? JSONDecoder().decode(Settings.self, from: data) else { return false }
            return draft.scale < scale && draft.mode == "fps_enhanced"
        }
        let expectation = XCTNSPredicateExpectation(predicate: predicate, object: summary)
        XCTAssertEqual(XCTWaiter.wait(for: [expectation], timeout: 5), .completed)
        XCTAssertLessThan(try editorSettings().scale, scale)
    }
    private func waitHost(_ predicate: (Snapshot) -> Bool) throws -> Snapshot {
        let deadline = Date().addingTimeInterval(5)
        repeat {
            let value = try observe()
            if predicate(value) { return value }
            Thread.sleep(forTimeInterval: 0.05)
        } while Date() < deadline
        let value = try observe(); XCTAssertTrue(predicate(value)); return value
    }
    private func refreshKeepingSettingsAndPause(_ checkpoint: String) throws {
        // Apply the real host's emergency latch, never a sensor/UI bypass.
        let previous = try observe(pauseTracking: true)
        XCTAssertTrue(previous.connected); XCTAssertTrue(previous.paused)
        let button = app.buttons["connection.refresh"]
        XCTAssertTrue(button.isHittable); button.tap()
        waitContains(app.staticTexts["connection.status"], "Video refreshed. Tracking is paused;")
        waitContains(app.staticTexts["frame.status"], "1280 × 480")
        let refreshed = try waitHost { $0.connected && $0.epoch == previous.epoch && $0.videoRefreshes.count > previous.videoRefreshes.count }
        XCTAssertEqual(refreshed.epoch, previous.epoch)
        let acknowledgement = try XCTUnwrap(refreshed.videoRefreshes.last)
        XCTAssertEqual(acknowledgement.epoch, previous.epoch); XCTAssertGreaterThan(acknowledgement.requestId, 0)
        XCTAssertTrue(acknowledgement.paused)
        XCTAssertEqual(refreshed.settings, previous.settings)
        XCTAssertTrue(refreshed.paused); XCTAssertTrue(refreshed.mouseMoves.isEmpty)
        XCTAssertTrue(refreshed.poses.allSatisfy { $0.q == nil })
        let descriptor = app.staticTexts["stream.session"].value as? String ?? ""
        XCTAssertTrue(descriptor.contains("epoch=\(refreshed.epoch);accepted=true;layout=sbs;target=virtual-hmd"))
        let recorded = try observe(checkpoint)
        XCTAssertEqual(recorded.epoch, refreshed.epoch); XCTAssertTrue(recorded.paused)
        XCTAssertEqual(recorded.settings, previous.settings)
    }
    func testLANIndependentStereoEyesBypassEnhancedAndCinemaProjection() throws {
        launch("lan"); try connect()
        let before = try observe("steamvr-lan-connected")
        XCTAssertEqual(before.settings.mode, "fps_enhanced")
        app.buttons["settings.hide"].tap(); screenshot("STEAMVR-01-LAN-enhanced-independent-eyes")
        showOverlay()
        let picker = app.segmentedControls["view.mode"]; reveal(picker)
        XCTAssertTrue(picker.buttons["Cinema"].isEnabled); picker.buttons["Cinema"].tap()
        app.buttons["settings.hide"].tap(); screenshot("STEAMVR-02-LAN-cinema-independent-eyes")
        showOverlay(); reveal(picker); picker.buttons["Enhanced first person"].tap()
        _ = try waitHost { $0.settings.mode == "fps_enhanced" }
        let editor = app.buttons["view.editor"]; reveal(editor); editor.tap()
        XCTAssertTrue(app.buttons["editor.save"].waitForExistence(timeout: 5))
        try assertEditorHalfImageAspect(); screenshot("STEAMVR-03-SBS-editor-half-aspect")
        app.buttons["editor.discard"].tap()
        XCTAssertTrue(try observe("steamvr-editor-discarded").mouseMoves.isEmpty)
        reveal(editor); editor.tap()
        XCTAssertTrue(app.buttons["editor.save"].waitForExistence(timeout: 5))
        try assertEditorHalfImageAspect()
        let corner = app.otherElements["editor.eye0.bottomRight"]
        XCTAssertTrue(corner.waitForExistence(timeout: 5)); XCTAssertTrue(corner.isHittable)
        let draftBeforeDrag = try editorSettings()
        let start = corner.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5))
        // A very short default-velocity drag can miss the pan recognizer on a
        // busy Simulator. Use the real handle with enough native move/hold time,
        // then require the actual draft to change before Save is exercised.
        start.press(forDuration: 0.2, thenDragTo: start.withOffset(CGVector(dx: -35, dy: -25)),
                    withVelocity: .slow, thenHoldForDuration: 0.2)
        try waitEditorScaleLessThan(draftBeforeDrag.scale)
        try assertEditorHalfImageAspect(); app.buttons["editor.save"].tap()
        _ = try waitHost { $0.settings.scale < before.settings.scale && $0.settings.mode == "fps_enhanced" }
        let saved = try observe("steamvr-editor-saved")
        XCTAssertEqual(saved.settings.mode, "fps_enhanced"); XCTAssertLessThan(saved.settings.scale, before.settings.scale)
        XCTAssertTrue(saved.mouseMoves.isEmpty); XCTAssertTrue(saved.poses.allSatisfy { $0.q == nil })
        app.buttons["settings.hide"].tap(); screenshot("STEAMVR-04-SBS-saved-profile")
        showOverlay(); try refreshKeepingSettingsAndPause("steamvr-lan-refreshed")
        app.buttons["settings.hide"].tap(); screenshot("STEAMVR-08-LAN-refreshed-independent-eyes")
        showOverlay(); let toggle = app.buttons["connection.toggle"]; reveal(toggle); toggle.tap()
        waitContains(app.staticTexts["connection.status"], "Disconnected.")
        _ = try waitHost { !$0.connected }
        XCTAssertFalse(try observe("steamvr-lan-disconnected").connected)
        app.buttons["settings.hide"].tap(); screenshot("STEAMVR-05-disconnected-clears-Metal")
    }
    func testSimulatedUSBRealFramedStereoAndHonestUnavailableTracking() throws {
        launch("usb"); try connect()
        let motion = app.staticTexts["motion.status"]; reveal(motion)
        waitContains(motion, "No device motion tracking")
        let host = try observe("steamvr-usb-connected")
        XCTAssertTrue(host.poses.allSatisfy { $0.q == nil })
        XCTAssertTrue(host.poses.contains { $0.connected && $0.seq > 0 && $0.q == nil })
        app.buttons["settings.hide"].tap(); screenshot("STEAMVR-06-USB-independent-eyes")
        showOverlay(); try refreshKeepingSettingsAndPause("steamvr-usb-refreshed")
        app.buttons["settings.hide"].tap(); screenshot("STEAMVR-09-USB-refreshed-independent-eyes")
        showOverlay(); let toggle = app.buttons["connection.toggle"]; reveal(toggle); toggle.tap()
        waitContains(app.staticTexts["connection.status"], "Disconnected.")
        _ = try waitHost { !$0.connected }
        let stopped = try observe("steamvr-usb-disconnected")
        XCTAssertFalse(stopped.connected)
        let session = app.staticTexts["stream.session"].value as? String ?? ""
        XCTAssertEqual(session, "unnegotiated")
        app.buttons["settings.hide"].tap(); screenshot("STEAMVR-07-USB-disconnected-clears-Metal")
        // A genuine transport disconnect still creates a new accepted epoch;
        // unlike live video Refresh it must retain the host's pause latch.
        showOverlay(); reveal(toggle); toggle.tap()
        waitContains(app.staticTexts["connection.status"], "Connected.")
        waitContains(app.staticTexts["frame.status"], "1280 × 480")
        let reconnected = try waitHost { $0.connected && $0.epoch > stopped.epoch }
        XCTAssertTrue(reconnected.paused); XCTAssertEqual(reconnected.settings, host.settings)
        XCTAssertTrue(reconnected.mouseMoves.isEmpty); XCTAssertTrue(reconnected.poses.allSatisfy { $0.q == nil })
        _ = try observe("steamvr-usb-reconnected")
        reveal(toggle); toggle.tap(); waitContains(app.staticTexts["connection.status"], "Disconnected.")
        _ = try waitHost { !$0.connected }; _ = try observe("steamvr-usb-disconnected-final")
    }
}
