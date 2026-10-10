import XCTest

/// Requires the original calibration-only host on loopback:18765 with token 123456.
/// No desktop capture, real game input, account or physical device is used by this test.
final class ViewerSmokeTests: XCTestCase {
    private let app = XCUIApplication()
    private var baseArguments: [String] { ["--ui-testing", "--transport", "lan", "--host", "127.0.0.1", "--port", "18765", "--code", "123456"] }

    override func setUpWithError() throws {
        continueAfterFailure = false
        app.launchArguments = baseArguments + ["--reset-preferences"]
        launchViewer()
    }
    override func tearDownWithError() throws {
        app.terminate()
        try requestFixtureAction("resume-relay")
    }
    private func launchViewer() {
        app.launch()
        // Rotate the active app, rather than portrait-only SpringBoard before
        // launch. XCTest must observe the same orientation as the viewer scene.
        XCUIDevice.shared.orientation = .landscapeRight
        XCTAssertTrue(app.buttons["settings.hide"].waitForExistence(timeout: 10))
        let version = app.staticTexts["version.info"]
        XCTAssertTrue(version.waitForExistence(timeout: 5))
        XCTAssertTrue(version.label.contains("0.3.3"))
        XCTAssertTrue(version.label.contains("build 6") || version.label.contains("构建 6"))
    }
    private func screenshot(_ name: String) {
        // The physical screen avoids app-region crop/rotation ambiguity.
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
    }
    private func geometry(_ name: String, target: XCUIElement) {
        let scroll = app.scrollViews["settings.scroll"]
        let nativeGeometry = app.otherElements["vr.surface"].value as? String ?? "unavailable"
        let text = "device=\(XCUIDevice.shared.orientation.rawValue); app=\(app.frame); scroll=\(scroll.frame); target=\(target.frame); targetHittable=\(target.isHittable); UIKit=\(nativeGeometry)"
        let attachment = XCTAttachment(string: text)
        attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
    }
    private func dragScroll(_ scroll: XCUIElement, up: Bool) {
        // The 12-point content padding is a real scrollable gutter. Starting
        // here avoids dragging a field, segmented control or slider instead.
        let start = scroll.coordinate(withNormalizedOffset: CGVector(dx: 0.98, dy: up ? 0.85 : 0.15))
        let end = scroll.coordinate(withNormalizedOffset: CGVector(dx: 0.98, dy: up ? 0.15 : 0.85))
        start.press(forDuration: 0.05, thenDragTo: end)
    }
    private func reveal(_ element: XCUIElement) {
        let scroll = app.scrollViews["settings.scroll"]
        geometry("before-reveal", target: element)
        // Scene-backed landscape coordinates now describe the actual scroll
        // viewport. Prefer the direction of the real target to avoid repeatedly
        // returning to the top between editor and lower setting controls.
        for _ in 0..<16 {
            if element.isHittable { return }
            let rect = element.frame
            if rect.width <= 0 || rect.height <= 0 { break }
            dragScroll(scroll, up: rect.midY >= scroll.frame.midY)
        }
        for _ in 0..<8 {
            if element.isHittable { return }
            dragScroll(scroll, up: false)
        }
        for _ in 0..<14 {
            if element.isHittable { return }
            dragScroll(scroll, up: true)
        }
        geometry("failed-reveal", target: element)
        screenshot("failed-reveal-screen")
        XCTAssertTrue(element.isHittable)
    }
    private struct NativeRect: Decodable {
        let x: Double, y: Double, width: Double, height: Double
        var midX: Double { x + width / 2 }
        var midY: Double { y + height / 2 }
    }
    private struct SliderGeometry: Decodable {
        let frame: NativeRect, track: NativeRect, current: NativeRect, minimum: NativeRect, maximum: NativeRect
        let nativeValue: Double, minimumValue: Double, maximumValue: Double
    }
    private func scaleGeometry() throws -> SliderGeometry {
        let text = app.staticTexts["setting.scale.label"].value as? String
        let data = try XCTUnwrap(text?.data(using: .utf8), "Native slider diagnostics are missing")
        return try JSONDecoder().decode(SliderGeometry.self, from: data)
    }
    private func dragSlider(_ slider: XCUIElement, to position: Double, key: String = "scale", steps: Double = 50) throws {
        XCTAssertTrue(slider.isHittable)
        let text = app.staticTexts["setting.\(key).label"].value as? String
        let data = try XCTUnwrap(text?.data(using: .utf8), "Native slider diagnostics are missing")
        let native = try JSONDecoder().decode(SliderGeometry.self, from: data)
        XCTAssertEqual(native.frame.x, Double(slider.frame.minX), accuracy: 1)
        XCTAssertEqual(native.frame.y, Double(slider.frame.minY), accuracy: 1)
        XCTAssertGreaterThan(native.frame.width, 0)
        XCTAssertGreaterThan(native.frame.height, 0)
        XCTAssertEqual(native.minimumValue, 0)
        XCTAssertEqual(native.maximumValue, steps)
        let x = native.minimum.midX + (native.maximum.midX - native.minimum.midX) * position
        let y = native.current.midY
        let start = slider.coordinate(withNormalizedOffset: CGVector(
            dx: CGFloat((native.current.midX - native.frame.x) / native.frame.width),
            dy: CGFloat((y - native.frame.y) / native.frame.height)))
        let end = slider.coordinate(withNormalizedOffset: CGVector(
            dx: CGFloat((x - native.frame.x) / native.frame.width),
            dy: CGFloat((y - native.frame.y) / native.frame.height)))
        let attachment = XCTAttachment(string: "native=\(text ?? ""); targetWindowPoint=(\(x),\(y)); normalized=\(position)")
        attachment.name = "slider-real-touch"; attachment.lifetime = .keepAlways; add(attachment)
        start.press(forDuration: 0.1, thenDragTo: end)
    }
    private func setScaleWithPrecisionButtons(step target: Int) throws {
        XCTAssertTrue((0...50).contains(target))
        for _ in 0...50 {
            let current = Int(try scaleGeometry().nativeValue.rounded())
            if current == target { return }
            let direction = current < target ? "increase" : "decrease"
            let button = app.buttons["setting.scale.\(direction)"]
            XCTAssertTrue(button.isHittable); XCTAssertTrue(button.isEnabled)
            button.tap()
            let next = current + (current < target ? 1 : -1)
            waitLabel(app.staticTexts["setting.scale.label"], contains: "\(50 + next)%")
            XCTAssertEqual(Int(try scaleGeometry().nativeValue.rounded()), next)
        }
        XCTFail("Precision buttons did not reach the requested scale")
    }
    private func adjustScaleAndWaitForStableEcho() throws {
        let scale = app.sliders["setting.scale"]
        reveal(scale)
        let initial = app.staticTexts["setting.scale.label"].label
        try dragSlider(scale, to: 0.8)
        expectation(for: NSPredicate(format: "label != %@", initial), evaluatedWith: app.staticTexts["setting.scale.label"])
        waitForExpectations(timeout: 20)
        // Native slider tracking can use approximate scrubbing. Real, public
        // precision buttons supply the exact final value; no test setter exists.
        try setScaleWithPrecisionButtons(step: 40)
        waitLabel(app.staticTexts["setting.scale.label"], contains: "90%")
        Thread.sleep(forTimeInterval: 2)
        XCTAssertTrue(app.staticTexts["setting.scale.label"].label.contains("90%"))
        try dragSlider(scale, to: 0.7)
        try setScaleWithPrecisionButtons(step: 35)
        waitLabel(app.staticTexts["setting.scale.label"], contains: "85%")
    }
    private func waitLabel(_ element: XCUIElement, contains text: String, timeout: TimeInterval = 20) {
        let match = NSPredicate(format: "label CONTAINS %@", text)
        expectation(for: match, evaluatedWith: element)
        waitForExpectations(timeout: timeout)
    }

    func testLanguageNetworkRendererAndReconnect() throws {
        let picker = app.segmentedControls["language.picker"]
        XCTAssertTrue(picker.buttons["English"].isSelected)
        screenshot("01-default-English")
        picker.buttons["中文"].tap()
        XCTAssertEqual(app.buttons["settings.hide"].label, "隐藏设置")
        app.terminate()
        app.launchArguments = baseArguments
        launchViewer()
        XCTAssertTrue(app.segmentedControls["language.picker"].buttons["中文"].isSelected)
        XCTAssertEqual(app.buttons["settings.hide"].label, "隐藏设置")
        screenshot("02-Chinese-persisted")
        app.segmentedControls["language.picker"].buttons["English"].tap()
        app.terminate(); launchViewer()
        XCTAssertTrue(app.segmentedControls["language.picker"].buttons["English"].isSelected)
        let toggle = app.buttons["connection.toggle"]
        reveal(toggle); toggle.tap()
        waitLabel(toggle, contains: "Disconnect")
        let frames = app.staticTexts["frame.status"]
        waitLabel(frames, contains: "1280")
        screenshot("03-real-WebSocket-JPEG")
        try adjustScaleAndWaitForStableEcho()
        let sensor = app.staticTexts["motion.status"]
        if sensor.exists {
            let modes = app.segmentedControls["view.mode"]
            reveal(modes)
            XCTAssertTrue(modes.buttons["Full"].isSelected)
            XCTAssertFalse(modes.buttons["Cinema"].isEnabled)
            XCTAssertFalse(modes.buttons["First person"].isEnabled)
            screenshot("04-no-sensor-full-fallback")
        }
        app.buttons["settings.hide"].tap()
        XCTAssertFalse(app.scrollViews["settings.scroll"].exists)
        // Several rendered frames must pass before the retained screenshot is captured.
        let rendered = app.otherElements["vr.surface"]
        XCTAssertTrue(rendered.waitForExistence(timeout: 5))
        Thread.sleep(forTimeInterval: 2)
        screenshot("05-full-stereo-Metal")
        rendered.press(forDuration: 1.2)
        XCTAssertTrue(app.scrollViews["settings.scroll"].waitForExistence(timeout: 5))
        reveal(toggle); toggle.tap(); try assertDisconnected()
        toggle.tap(); waitLabel(toggle, contains: "Disconnect")
        waitLabel(frames, contains: "1280")
        screenshot("06-reconnected")
        XCUIDevice.shared.press(.home)
        app.activate()
        waitLabel(toggle, contains: "Connect")
        reveal(toggle); toggle.tap(); waitLabel(toggle, contains: "Disconnect")
        waitLabel(frames, contains: "1280")
        screenshot("07-background-reconnect")
        reveal(toggle); toggle.tap(); try assertDisconnected()
    }

    func testUSBDetectionAndFrames() throws {
        // The CI fixture uses the production UsbManager/relay with a simulated mux
        // discovery adapter. It connects to the simulator listener on loopback18766.
        app.terminate()
        app.launchArguments = ["--ui-testing", "--reset-preferences"]
        launchViewer()
        XCTAssertTrue(app.segmentedControls["connection.transport"].buttons["USB"].isSelected)
        XCTAssertFalse(app.secureTextFields["connection.code"].exists)
        let toggle = app.buttons["connection.toggle"]
        try assertDisconnected()
        reveal(toggle); toggle.tap()
        waitLabel(toggle, contains: "Disconnect", timeout: 40)
        let frames = app.staticTexts["frame.status"]
        waitLabel(frames, contains: "1280")
        try adjustScaleAndWaitForStableEcho()
        try adjustStabilizationAndWaitForStableEcho(checkpoint: "stabilization-usb-saved")
        screenshot("USB-01-auto-detected-settings")
        app.buttons["settings.hide"].tap()
        let surface = app.otherElements["vr.surface"]
        XCTAssertTrue(surface.waitForExistence(timeout: 5))
        Thread.sleep(forTimeInterval: 2)
        screenshot("USB-02-real-Metal-stereo")
        surface.press(forDuration: 1.2)
        XCTAssertTrue(app.scrollViews["settings.scroll"].waitForExistence(timeout: 5))
        XCUIDevice.shared.press(.home)
        app.activate()
        waitLabel(toggle, contains: "Connect")
        reveal(toggle); toggle.tap()
        waitLabel(toggle, contains: "Disconnect", timeout: 40)
        waitLabel(frames, contains: "1280")
        screenshot("USB-03-explicit-background-reconnect")
        reveal(toggle); toggle.tap(); try assertDisconnected()
        // Disconnect stops video, but foreground PC control stays available.
        try requestFixturePhoneConnect()
        waitLabel(toggle, contains: "Disconnect", timeout: 40)
        waitLabel(frames, contains: "1280")
        let active = try observeHost()
        try requestFixturePhoneConnect()
        Thread.sleep(forTimeInterval: 1)
        XCTAssertTrue(try observeHost().connected)
        XCTAssertEqual(try observeHost().settingsCount, active.settingsCount)
        reveal(toggle); toggle.tap(); try assertDisconnected()
        // Cover PC Stop while phone video is waiting with no accepted peer.
        // The production stop control must close the pending video listener;
        // restoring automatic scanning must not resurrect its old action.
        try requestFixtureAction("pause-relay")
        reveal(toggle); toggle.tap(); waitLabel(toggle, contains: "Cancel")
        try requestFixtureAction("phone-stop")
        try assertDisconnected()
        try requestFixtureAction("resume-relay")
        Thread.sleep(forTimeInterval: 2); try assertDisconnected()
        try requestFixturePhoneConnect()
        waitLabel(toggle, contains: "Disconnect", timeout: 40)
        waitLabel(frames, contains: "1280")
        reveal(toggle); toggle.tap(); try assertDisconnected()
    }

    private struct SavedSettings: Decodable, Equatable {
        let mode: String
        let scale: Double, offsetX: Double, offsetY: Double, eyeSeparation: Double
        let fov: Double, distance: Double, distortion: Double, sensitivity: Double
        let stabilization: Double
        let invertY: Bool
    }
    private struct HostObservation: Decodable {
        let settingsCount: Int
        let connected: Bool
        let settings: SavedSettings
        let mouseMoves: [[Int]]
    }
    private func observeHost(checkpoint name: String? = nil) throws -> HostObservation {
        let endpoint = name == nil ? "snapshot" : "checkpoint"
        var request = URLRequest(url: URL(string: "http://127.0.0.1:18769/\(endpoint)")!)
        request.timeoutInterval = 5
        if let name = name {
            request.httpMethod = "POST"; request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try JSONSerialization.data(withJSONObject: ["name": name])
        }
        let completed = expectation(description: "Observe calibration-only host")
        var payload: Data?, failure: Error?, status: Int?
        URLSession.shared.dataTask(with: request) { data, response, error in
            payload = data; failure = error; status = (response as? HTTPURLResponse)?.statusCode; completed.fulfill()
        }.resume()
        wait(for: [completed], timeout: 8)
        XCTAssertNil(failure); XCTAssertEqual(status, 200)
        return try JSONDecoder().decode(HostObservation.self, from: XCTUnwrap(payload))
    }
    private func assertDisconnected() throws {
        waitLabel(app.buttons["connection.toggle"], contains: "Connect")
        waitLabel(app.staticTexts["frame.status"], contains: "Waiting")
        let surface = app.otherElements["vr.surface"]
        expectation(for: NSPredicate(format: "value CONTAINS %@", "texture=no texture"), evaluatedWith: surface)
        waitForExpectations(timeout: 5)
        for _ in 0..<40 {
            if !(try observeHost().connected) { break }
            Thread.sleep(forTimeInterval: 0.05)
        }
        XCTAssertFalse(try observeHost().connected)
        // Recheck after several fixture frames: late decode/old session callbacks
        // must not resurrect a texture or keep the desktop session alive.
        Thread.sleep(forTimeInterval: 1)
        XCTAssertFalse(try observeHost().connected)
        XCTAssertTrue((surface.value as? String ?? "").contains("texture=no texture"))
        XCTAssertTrue(app.staticTexts["frame.status"].label.contains("Waiting"))
    }
    private func requestFixturePhoneConnect() throws {
        try requestFixtureAction("phone-connect")
    }
    private func requestFixtureAction(_ action: String) throws {
        var request = URLRequest(url: URL(string: "http://127.0.0.1:18769/\(action)")!)
        request.httpMethod = "POST"; request.timeoutInterval = 5
        let completed = expectation(description: "Explicit PC control through production paired USB adapter")
        var status: Int?, failure: Error?
        URLSession.shared.dataTask(with: request) { _, response, error in
            status = (response as? HTTPURLResponse)?.statusCode; failure = error; completed.fulfill()
        }.resume()
        wait(for: [completed], timeout: 8); XCTAssertNil(failure); XCTAssertEqual(status, 200)
    }
    private func draftSettings() throws -> SavedSettings {
        let summary = app.staticTexts["editor.summary"]
        let data = try XCTUnwrap((summary.value as? String)?.data(using: .utf8))
        return try JSONDecoder().decode(SavedSettings.self, from: data)
    }
    private func updateFixtureDesktopScale(_ scale: Double) throws {
        try updateFixtureDesktop(["scale": scale])
    }
    private func updateFixtureDesktop(_ patch: [String: Double]) throws {
        try updateFixtureDesktopObject(patch.mapValues { $0 as Any })
    }
    private func updateFixtureDesktopObject(_ patch: [String: Any]) throws {
        // This changes the synthetic PC's real HostServer settings, never the
        // app's values or preferences. The app must receive its normal broadcast.
        var request = URLRequest(url: URL(string: "http://127.0.0.1:18769/host-update")!)
        request.httpMethod = "POST"; request.timeoutInterval = 5
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: patch)
        let completed = expectation(description: "Update original fixture desktop settings")
        var status: Int?, failure: Error?
        URLSession.shared.dataTask(with: request) { _, response, error in
            status = (response as? HTTPURLResponse)?.statusCode; failure = error; completed.fulfill()
        }.resume()
        wait(for: [completed], timeout: 8); XCTAssertNil(failure); XCTAssertEqual(status, 200)
    }
    func testFreshUSBNoSensorFallbackPreservesNegotiatedStabilization() throws {
        app.terminate()
        try updateFixtureDesktopObject(["mode": "fps", "stabilization": 0.72])
        let before = try observeHost()
        app.launchArguments = ["--ui-testing", "--reset-preferences"]
        launchViewer()
        let initialToggle = app.buttons["connection.toggle"]
        reveal(initialToggle); initialToggle.tap()
        // A native Simulator has no usable motion source: the real application
        // must fall back after learning the host's full, negotiated settings.
        XCTAssertTrue(app.staticTexts["motion.status"].exists)
        let toggle = app.buttons["connection.toggle"]
        waitLabel(toggle, contains: "Disconnect", timeout: 40)
        waitLabel(app.staticTexts["frame.status"], contains: "1280")
        let label = app.staticTexts["setting.stabilization.label"]
        reveal(label); waitLabel(label, contains: "72%")
        Thread.sleep(forTimeInterval: 2)
        let after = try observeHost(checkpoint: "stabilization-fresh-usb-fallback")
        XCTAssertEqual(after.settings.mode, "full")
        XCTAssertEqual(after.settings.stabilization, 0.72, accuracy: 0.000001)
        XCTAssertEqual(after.settingsCount, before.settingsCount + 1)
        XCTAssertTrue(after.mouseMoves.isEmpty)
        app.terminate(); app.launchArguments = ["--ui-testing"]; launchViewer()
        reveal(label); XCTAssertTrue(label.label.contains("72%"))
        reveal(toggle); toggle.tap()
        waitLabel(toggle, contains: "Disconnect", timeout: 40)
        XCTAssertEqual(try observeHost(checkpoint: "stabilization-fresh-usb-restarted").settings.stabilization, 0.72, accuracy: 0.000001)
        screenshot("STABILIZATION-03-fresh-USB-fallback-preserved")
        reveal(toggle); toggle.tap(); try assertDisconnected()
    }
    private func stabilizationGeometry() throws -> SliderGeometry {
        let text = app.staticTexts["setting.stabilization.label"].value as? String
        return try JSONDecoder().decode(SliderGeometry.self, from: XCTUnwrap(text?.data(using: .utf8)))
    }
    private func adjustStabilizationAndWaitForStableEcho(checkpoint: String) throws {
        let slider = app.sliders["setting.stabilization"]
        reveal(slider)
        try dragSlider(slider, to: 0.6, key: "stabilization", steps: 100)
        // Real public precision controls retain exact percentage endpoints
        // without writing app state through a test-only setter.
        for _ in 0...100 {
            let current = Int(try stabilizationGeometry().nativeValue.rounded())
            if current == 60 { break }
            let button = app.buttons["setting.stabilization.\(current < 60 ? "increase" : "decrease")"]
            XCTAssertTrue(button.isHittable); XCTAssertTrue(button.isEnabled); button.tap()
        }
        waitLabel(app.staticTexts["setting.stabilization.label"], contains: "60%")
        XCTAssertEqual(Int(try stabilizationGeometry().nativeValue.rounded()), 60)
        Thread.sleep(forTimeInterval: 2)
        XCTAssertTrue(app.staticTexts["setting.stabilization.label"].label.contains("60%"))
        let received = try observeHost(checkpoint: checkpoint)
        XCTAssertEqual(received.settings.stabilization, 0.6, accuracy: 0.000001)
        XCTAssertTrue(received.mouseMoves.isEmpty)
    }
    func testStabilizationSliderSyncPersistenceAndReset() throws {
        let label = app.staticTexts["setting.stabilization.label"]
        reveal(label); XCTAssertTrue(label.label.contains("0%"))
        let toggle = app.buttons["connection.toggle"]
        reveal(toggle); toggle.tap(); waitLabel(toggle, contains: "Disconnect")
        waitLabel(app.staticTexts["frame.status"], contains: "1280")
        try adjustStabilizationAndWaitForStableEcho(checkpoint: "stabilization-lan-saved")
        screenshot("STABILIZATION-01-real-slider-60")
        try updateFixtureDesktop(["stabilization": 0.65])
        waitLabel(label, contains: "65%")
        Thread.sleep(forTimeInterval: 1)
        app.terminate(); app.launchArguments = baseArguments; launchViewer()
        reveal(label); XCTAssertTrue(label.label.contains("65%"))
        reveal(toggle); toggle.tap(); waitLabel(toggle, contains: "Disconnect")
        Thread.sleep(forTimeInterval: 1)
        XCTAssertEqual(try observeHost(checkpoint: "stabilization-restored").settings.stabilization, 0.65, accuracy: 0.000001)
        reveal(toggle); toggle.tap(); waitLabel(toggle, contains: "Connect")
        reveal(app.sliders["setting.stabilization"])
        app.buttons["setting.stabilization.decrease"].tap(); waitLabel(label, contains: "64%")
        app.terminate(); launchViewer()
        reveal(label); XCTAssertTrue(label.label.contains("64%"))
        reveal(toggle); toggle.tap(); waitLabel(toggle, contains: "Disconnect")
        Thread.sleep(forTimeInterval: 1)
        let restored = try observeHost(checkpoint: "stabilization-offline-restored")
        XCTAssertEqual(restored.settings.stabilization, 0.64, accuracy: 0.000001); XCTAssertTrue(restored.mouseMoves.isEmpty)
        let reset = app.buttons["view.reset"]; reveal(reset); reset.tap()
        waitLabel(toggle, contains: "Connect")
        reveal(label); XCTAssertTrue(label.label.contains("0%"))
        XCTAssertTrue(app.segmentedControls["language.picker"].buttons["English"].isSelected)
        XCTAssertTrue(app.segmentedControls["connection.transport"].buttons["USB"].isSelected)
        screenshot("STABILIZATION-02-reset-zero")
    }
    private func panEditor(eye: Int = 0, horizontal: CGFloat = -28, vertical: CGFloat = -22) {
        let image = app.otherElements["editor.eye\(eye).interior"]
        XCTAssertTrue(image.isHittable)
        let start = image.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.6))
        let end = start.withOffset(CGVector(dx: horizontal, dy: vertical))
        start.press(forDuration: 0.1, thenDragTo: end)
    }
    private func resizeEditor(horizontal: CGFloat = -32, vertical: CGFloat = -18) {
        let corner = app.otherElements["editor.eye0.bottomRight"]
        XCTAssertTrue(corner.isHittable)
        let start = corner.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5))
        start.press(forDuration: 0.1, thenDragTo: start.withOffset(CGVector(dx: horizontal, dy: vertical)))
    }
    private func openFitEditor() {
        let open = app.buttons["view.editor"]; reveal(open); open.tap()
        XCTAssertTrue(app.buttons["editor.save"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.scrollViews["settings.scroll"].exists)
    }
    private func waitHostSettings(_ expected: SavedSettings) throws -> HostObservation {
        for _ in 0..<25 {
            let result = try observeHost()
            if result.settings == expected { return result }
            Thread.sleep(forTimeInterval: 0.2)
        }
        XCTFail("The real host did not receive the saved phone snapshot")
        return try observeHost()
    }
    func testEditorSaveDiscardPersistenceAndReset() throws {
        let toggle = app.buttons["connection.toggle"]
        reveal(toggle); toggle.tap(); waitLabel(toggle, contains: "Disconnect")
        waitLabel(app.staticTexts["frame.status"], contains: "1280")
        // Let the initial local-profile acknowledgment settle before counting edits.
        Thread.sleep(forTimeInterval: 1)
        let entry = try observeHost(checkpoint: "editor-entry")
        openFitEditor()
        let leftBefore = app.otherElements["editor.eye0.interior"].frame
        let rightBefore = app.otherElements["editor.eye1.interior"].frame
        panEditor()
        let panned = try draftSettings()
        XCTAssertGreaterThan(panned.eyeSeparation, entry.settings.eyeSeparation)
        XCTAssertLessThan(app.otherElements["editor.eye0.interior"].frame.midX, leftBefore.midX)
        XCTAssertGreaterThan(app.otherElements["editor.eye1.interior"].frame.midX, rightBefore.midX)
        panEditor(eye: 1, horizontal: 28)
        let rightPanned = try draftSettings()
        XCTAssertGreaterThan(rightPanned.eyeSeparation, panned.eyeSeparation)
        resizeEditor()
        let discarded = try draftSettings()
        XCTAssertNotEqual(discarded.scale, entry.settings.scale)
        XCTAssertEqual(discarded.offsetX, entry.settings.offsetX)
        // Left-eye left and right-eye right both widen separation; vertical
        // movement is shared. Resizing preserves spacing and both offsets.
        XCTAssertGreaterThan(discarded.eyeSeparation, entry.settings.eyeSeparation)
        XCTAssertGreaterThan(discarded.offsetY, entry.settings.offsetY)
        XCTAssertEqual(discarded.offsetX, rightPanned.offsetX); XCTAssertEqual(discarded.offsetY, rightPanned.offsetY)
        XCTAssertEqual(discarded.eyeSeparation, rightPanned.eyeSeparation)
        Thread.sleep(forTimeInterval: 1)
        let preview = try observeHost(checkpoint: "editor-discard-preview")
        XCTAssertEqual(preview.settingsCount, entry.settingsCount)
        XCTAssertEqual(preview.settings, entry.settings)
        screenshot("EDITOR-01-local-preview")
        app.buttons["editor.discard"].tap()
        let afterDiscard = try observeHost(checkpoint: "editor-discarded")
        XCTAssertEqual(afterDiscard.settingsCount, entry.settingsCount)
        XCTAssertEqual(afterDiscard.settings, entry.settings)
        reveal(app.staticTexts["setting.scale.label"])
        XCTAssertTrue(app.staticTexts["setting.scale.label"].label.contains("85%"))
        // Genuine corner touches make a small image. A long inward left-eye
        // drag reaches the new contact bound; no hidden settings setter exists.
        openFitEditor(); resizeEditor(horizontal: -180, vertical: -80)
        panEditor(horizontal: 350)
        let joined = try draftSettings()
        XCTAssertEqual(joined.scale, 0.5, accuracy: 0.000001)
        XCTAssertEqual(joined.eyeSeparation, -0.5, accuracy: 0.000001)
        XCTAssertEqual(joined.offsetX, 0, accuracy: 0.000001)
        screenshot("EDITOR-06-small-images-touch")
        resizeEditor(horizontal: 60, vertical: 40)
        let saved = try draftSettings()
        XCTAssertGreaterThan(saved.scale, joined.scale)
        XCTAssertEqual(saved.eyeSeparation, saved.scale - 1, accuracy: 0.000001)
        XCTAssertLessThan(saved.eyeSeparation, 0)
        XCTAssertEqual(saved.offsetX, 0, accuracy: 0.000001)
        let left = app.otherElements["editor.eye0.interior"].frame, right = app.otherElements["editor.eye1.interior"].frame
        XCTAssertEqual(left.width, right.width, accuracy: 1); XCTAssertEqual(left.height, right.height, accuracy: 1)
        XCTAssertEqual(saved.mode, entry.settings.mode); XCTAssertEqual(saved.distortion, entry.settings.distortion)
        XCTAssertEqual(saved.fov, entry.settings.fov); XCTAssertEqual(saved.distance, entry.settings.distance)
        screenshot("EDITOR-02-save-draft")
        app.buttons["editor.save"].tap()
        _ = try waitHostSettings(saved)
        Thread.sleep(forTimeInterval: 2)
        let committed = try observeHost(checkpoint: "editor-saved")
        XCTAssertEqual(committed.settingsCount, entry.settingsCount + 1)
        XCTAssertEqual(committed.settings, saved)
        XCTAssertTrue(committed.mouseMoves.isEmpty)
        app.buttons["settings.hide"].tap()
        Thread.sleep(forTimeInterval: 2)
        screenshot("EDITOR-05-negative-seam-Metal")
        app.otherElements["vr.surface"].press(forDuration: 1.2)
        XCTAssertTrue(app.scrollViews["settings.scroll"].waitForExistence(timeout: 5))
        try updateFixtureDesktopScale(0.78)
        reveal(app.staticTexts["setting.scale.label"])
        waitLabel(app.staticTexts["setting.scale.label"], contains: "78%")
        let desktopProfile = try observeHost(checkpoint: "editor-desktop-updated")
        XCTAssertEqual(desktopProfile.settingsCount, committed.settingsCount + 1)
        XCTAssertEqual(desktopProfile.settings.scale, 0.78)

        // The same profile is visible offline after an actual app relaunch.
        let language = app.segmentedControls["language.picker"]; reveal(language); language.buttons["中文"].tap()
        app.terminate(); app.launchArguments = baseArguments; launchViewer()
        XCTAssertTrue(app.segmentedControls["language.picker"].buttons["中文"].isSelected)
        openFitEditor(); XCTAssertEqual(try draftSettings(), desktopProfile.settings)
        screenshot("EDITOR-03-Chinese-persisted")
        app.buttons["editor.discard"].tap()
        let english = app.segmentedControls["language.picker"]; reveal(english); english.buttons["English"].tap()
        reveal(toggle); toggle.tap(); waitLabel(toggle, contains: "Disconnect")
        _ = try waitHostSettings(desktopProfile.settings)

        // Change a real public precision control while disconnected. The next
        // valid hello must restore this local value over the host's old profile.
        reveal(toggle); toggle.tap(); waitLabel(toggle, contains: "Connect")
        let scale = app.sliders["setting.scale"]; reveal(scale)
        app.buttons["setting.scale.increase"].tap()
        let localStep = Int(try scaleGeometry().nativeValue.rounded())
        let localScale = 0.5 + Double(localStep) / 100
        XCTAssertNotEqual(localScale, saved.scale)
        app.terminate(); launchViewer()
        reveal(app.staticTexts["setting.scale.label"])
        XCTAssertTrue(app.staticTexts["setting.scale.label"].label.contains("\(50 + localStep)%"))
        reveal(toggle); toggle.tap(); waitLabel(toggle, contains: "Disconnect")
        waitLabel(app.staticTexts["frame.status"], contains: "1280")
        Thread.sleep(forTimeInterval: 1)
        let restored = try observeHost(checkpoint: "editor-local-restored")
        XCTAssertEqual(restored.settings.scale, localScale, accuracy: 0.000001)
        XCTAssertEqual(restored.settings.offsetX, saved.offsetX, accuracy: 0.000001)
        XCTAssertEqual(restored.settings.eyeSeparation, saved.eyeSeparation, accuracy: 0.000001)

        openFitEditor(); panEditor()
        XCUIDevice.shared.press(.home); app.activate()
        XCTAssertFalse(app.buttons["editor.save"].exists)
        waitLabel(toggle, contains: "Connect")
        openFitEditor(); XCTAssertEqual(try draftSettings(), restored.settings); app.buttons["editor.discard"].tap()

        let chinese = app.segmentedControls["language.picker"]; reveal(chinese); chinese.buttons["中文"].tap()
        let reset = app.buttons["view.reset"]; reveal(reset); reset.tap()
        XCTAssertTrue(app.segmentedControls["language.picker"].buttons["English"].isSelected)
        XCTAssertTrue(app.segmentedControls["connection.transport"].buttons["USB"].isSelected)
        waitLabel(toggle, contains: "Connect")
        Thread.sleep(forTimeInterval: 1)
        XCTAssertTrue(toggle.label.contains("Connect"))
        openFitEditor()
        let defaults = try draftSettings()
        XCTAssertEqual(defaults.scale, 0.85); XCTAssertEqual(defaults.offsetX, 0); XCTAssertEqual(defaults.offsetY, 0)
        XCTAssertEqual(defaults.mode, "full"); XCTAssertEqual(defaults.distortion, 0); XCTAssertFalse(defaults.invertY)
        XCTAssertEqual(defaults.eyeSeparation, 0.03); XCTAssertEqual(defaults.fov, 80)
        XCTAssertEqual(defaults.distance, 3); XCTAssertEqual(defaults.sensitivity, 1000)
        XCTAssertEqual(defaults.stabilization, 0)
        app.buttons["editor.discard"].tap()
        let route = app.segmentedControls["connection.transport"]; reveal(route); route.buttons["LAN"].tap()
        reveal(app.textFields["connection.host"])
        XCTAssertEqual(app.textFields["connection.host"].value as? String, "Computer IP or hostname")
        reveal(app.textFields["connection.port"])
        XCTAssertEqual(app.textFields["connection.port"].value as? String, "8765")
        reveal(app.secureTextFields["connection.code"])
        XCTAssertEqual(app.secureTextFields["connection.code"].value as? String, "Six-digit pairing code")
        screenshot("EDITOR-04-reset-all-defaults")
        reveal(route); route.buttons["USB"].tap()
        app.terminate(); app.launchArguments = ["--ui-testing"]; launchViewer()
        XCTAssertTrue(app.segmentedControls["language.picker"].buttons["English"].isSelected)
        XCTAssertTrue(app.segmentedControls["connection.transport"].buttons["USB"].isSelected)
        try assertDisconnected(); reveal(toggle); toggle.tap()
        waitLabel(toggle, contains: "Disconnect", timeout: 40)
        openFitEditor(); XCTAssertEqual(try draftSettings(), defaults); app.buttons["editor.discard"].tap()
    }
}
