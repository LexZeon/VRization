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
    override func tearDownWithError() throws { app.terminate() }
    private func launchViewer() {
        app.launch()
        // Rotate the active app, rather than portrait-only SpringBoard before
        // launch. XCTest must observe the same orientation as the viewer scene.
        XCUIDevice.shared.orientation = .landscapeRight
        XCTAssertTrue(app.buttons["settings.hide"].waitForExistence(timeout: 10))
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
    private func dragSlider(_ slider: XCUIElement, to position: Double) throws {
        XCTAssertTrue(slider.isHittable)
        let text = app.staticTexts["setting.scale.label"].value as? String
        let data = try XCTUnwrap(text?.data(using: .utf8), "Native slider diagnostics are missing")
        let native = try JSONDecoder().decode(SliderGeometry.self, from: data)
        XCTAssertEqual(native.frame.x, Double(slider.frame.minX), accuracy: 1)
        XCTAssertEqual(native.frame.y, Double(slider.frame.minY), accuracy: 1)
        XCTAssertGreaterThan(native.frame.width, 0)
        XCTAssertGreaterThan(native.frame.height, 0)
        XCTAssertEqual(native.minimumValue, 0)
        XCTAssertEqual(native.maximumValue, 50)
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
            XCTAssertFalse(modes.buttons["FPS"].isEnabled)
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
        reveal(toggle); toggle.tap(); waitLabel(toggle, contains: "Connect")
        toggle.tap(); waitLabel(toggle, contains: "Disconnect")
        waitLabel(frames, contains: "1280")
        screenshot("06-reconnected")
        XCUIDevice.shared.press(.home)
        app.activate()
        waitLabel(toggle, contains: "Connect")
        reveal(toggle); toggle.tap(); waitLabel(toggle, contains: "Disconnect")
        waitLabel(frames, contains: "1280")
        screenshot("07-background-reconnect")
        toggle.tap()
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
        waitLabel(toggle, contains: "Disconnect", timeout: 40)
        let frames = app.staticTexts["frame.status"]
        waitLabel(frames, contains: "1280")
        try adjustScaleAndWaitForStableEcho()
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
        reveal(toggle); toggle.tap()
    }

    private struct SavedSettings: Decodable, Equatable {
        let mode: String
        let scale: Double, offsetX: Double, offsetY: Double, eyeSeparation: Double
        let fov: Double, distance: Double, distortion: Double, sensitivity: Double
        let invertY: Bool
    }
    private struct HostObservation: Decodable {
        let settingsCount: Int
        let settings: SavedSettings
        let mouseMoves: [[Int]]
    }
    private func observeHost(checkpoint name: String? = nil) throws -> HostObservation {
        let endpoint = name == nil ? "snapshot" : "checkpoint"
        var request = URLRequest(url: URL(string: "http://127.0.0.1:18767/\(endpoint)")!)
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
    private func draftSettings() throws -> SavedSettings {
        let summary = app.staticTexts["editor.summary"]
        let data = try XCTUnwrap((summary.value as? String)?.data(using: .utf8))
        return try JSONDecoder().decode(SavedSettings.self, from: data)
    }
    private func updateFixtureDesktopScale(_ scale: Double) throws {
        // This changes the synthetic PC's real HostServer settings, never the
        // app's values or preferences. The app must receive its normal broadcast.
        var request = URLRequest(url: URL(string: "http://127.0.0.1:18767/host-update")!)
        request.httpMethod = "POST"; request.timeoutInterval = 5
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: ["scale": scale])
        let completed = expectation(description: "Update original fixture desktop settings")
        var status: Int?, failure: Error?
        URLSession.shared.dataTask(with: request) { _, response, error in
            status = (response as? HTTPURLResponse)?.statusCode; failure = error; completed.fulfill()
        }.resume()
        wait(for: [completed], timeout: 8); XCTAssertNil(failure); XCTAssertEqual(status, 200)
    }
    private func panEditor(eye: Int = 0, horizontal: CGFloat = -28) {
        let image = app.otherElements["editor.eye\(eye).interior"]
        XCTAssertTrue(image.isHittable)
        let start = image.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.6))
        let end = start.withOffset(CGVector(dx: horizontal, dy: -22))
        start.press(forDuration: 0.1, thenDragTo: end)
    }
    private func resizeEditor() {
        let corner = app.otherElements["editor.eye0.bottomRight"]
        XCTAssertTrue(corner.isHittable)
        let start = corner.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5))
        start.press(forDuration: 0.1, thenDragTo: start.withOffset(CGVector(dx: -32, dy: -18)))
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
        openFitEditor(); panEditor(); resizeEditor()
        let saved = try draftSettings()
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
        waitLabel(toggle, contains: "Disconnect", timeout: 40)
        openFitEditor(); XCTAssertEqual(try draftSettings(), defaults); app.buttons["editor.discard"].tap()
    }
}
