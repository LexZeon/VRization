import XCTest

/// Requires the original calibration-only host on loopback:18765 with token 123456.
/// No desktop capture, real game input, account or physical device is used by this test.
final class ViewerSmokeTests: XCTestCase {
    private let app = XCUIApplication()
    private var baseArguments: [String] { ["--ui-testing", "--transport", "lan", "--host", "127.0.0.1", "--port", "18765", "--code", "123456"] }

    override func setUpWithError() throws {
        continueAfterFailure = false
        app.launchArguments = baseArguments + ["--reset-preferences"]
        app.launch()
    }
    private func screenshot(_ name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
    }
    private func reveal(_ element: XCUIElement) {
        let scroll = app.scrollViews["settings.scroll"]
        for _ in 0..<8 {
            if element.isHittable { return }
            scroll.swipeUp()
        }
        XCTAssertTrue(element.isHittable)
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
        app.launch()
        XCTAssertTrue(app.segmentedControls["language.picker"].buttons["中文"].isSelected)
        XCTAssertEqual(app.buttons["settings.hide"].label, "隐藏设置")
        screenshot("02-Chinese-persisted")
        app.segmentedControls["language.picker"].buttons["English"].tap()
        app.terminate(); app.launch()
        XCTAssertTrue(app.segmentedControls["language.picker"].buttons["English"].isSelected)
        let toggle = app.buttons["connection.toggle"]
        reveal(toggle); toggle.tap()
        waitLabel(toggle, contains: "Disconnect")
        let frames = app.staticTexts["frame.status"]
        waitLabel(frames, contains: "1280")
        screenshot("03-real-WebSocket-JPEG")
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
}
