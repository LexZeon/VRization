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
    private func adjustScaleAndWaitForStableEcho() throws {
        let scale = app.sliders["setting.scale"]
        reveal(scale)
        try dragSlider(scale, to: 0.8)
        waitLabel(app.staticTexts["setting.scale.label"], contains: "90%")
        Thread.sleep(forTimeInterval: 2)
        XCTAssertTrue(app.staticTexts["setting.scale.label"].label.contains("90%"))
        try dragSlider(scale, to: 0.7)
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
}
