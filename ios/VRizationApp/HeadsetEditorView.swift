import UIKit
import VRizationCore

/// Transparent controls over the live local full-mode preview. Drafts never
/// touch the connection or preferences; the owner handles Save and Discard.
final class HeadsetEditorView: UIView, UIGestureRecognizerDelegate {
    private(set) var draft: VRSettings
    private var dragEntry: VRSettings?
    private var dragCorner: FitPoint?
    private var dragImageAspect = 16.0 / 9, dragEyeAspect = 1.0
    private var dragSize = CGSize.zero
    private let imageAspect: () -> Double
    private var interiors: [UIView] = [], handles: [[UIView]] = [], borders: [CAShapeLayer] = []
    private let summary = UILabel()
    private let toolbar = UIStackView()
    var onDraft: ((VRSettings) -> Void)?
    var onSave: ((VRSettings) -> Void)?
    var onDiscard: (() -> Void)?
    private let signs = [FitPoint(x: -1, y: 1), FitPoint(x: 1, y: 1), FitPoint(x: -1, y: -1), FitPoint(x: 1, y: -1)]
    private let cornerNames = ["topLeft", "topRight", "bottomLeft", "bottomRight"]

    init(entry: VRSettings, imageAspect: @escaping () -> Double) {
        self.draft = entry; self.imageAspect = imageAspect
        super.init(frame: .zero)
        accessibilityIdentifier = "editor.overlay"
        backgroundColor = .clear
        for eye in 0..<2 {
            let border = CAShapeLayer(); border.fillColor = UIColor.clear.cgColor
            border.strokeColor = UIColor.systemTeal.cgColor; border.lineWidth = 2
            border.actions = ["path": NSNull(), "bounds": NSNull(), "position": NSNull()]; border.masksToBounds = true
            layer.addSublayer(border); borders.append(border)
            let interior = UIView()
            interior.isAccessibilityElement = true; interior.accessibilityIdentifier = "editor.eye\(eye).interior"
            interior.accessibilityLabel = L.text("editorPan"); addSubview(interior); interiors.append(interior)
            var corners: [UIView] = []
            for corner in 0..<4 {
                let handle = UIView(); handle.backgroundColor = UIColor.systemTeal.withAlphaComponent(0.85)
                handle.layer.cornerRadius = 14; handle.layer.borderColor = UIColor.white.cgColor; handle.layer.borderWidth = 2
                handle.isAccessibilityElement = true
                handle.accessibilityIdentifier = "editor.eye\(eye).\(cornerNames[corner])"
                handle.accessibilityLabel = L.text("editorResize"); addSubview(handle); corners.append(handle)
            }
            handles.append(corners)
        }
        summary.textColor = .white; summary.font = .systemFont(ofSize: 14, weight: .medium); summary.numberOfLines = 2
        summary.accessibilityIdentifier = "editor.summary"
        let save = control("editorSave", id: "editor.save", action: #selector(saveDraft))
        let discard = control("editorDiscard", id: "editor.discard", action: #selector(discardDraft))
        toolbar.axis = .horizontal; toolbar.alignment = .center; toolbar.spacing = 10
        toolbar.addArrangedSubview(summary); toolbar.addArrangedSubview(discard); toolbar.addArrangedSubview(save)
        toolbar.backgroundColor = UIColor(white: 0.05, alpha: 0.92); toolbar.layer.cornerRadius = 8
        toolbar.translatesAutoresizingMaskIntoConstraints = false; addSubview(toolbar)
        NSLayoutConstraint.activate([
            toolbar.topAnchor.constraint(equalTo: safeAreaLayoutGuide.topAnchor, constant: 6),
            toolbar.leadingAnchor.constraint(equalTo: safeAreaLayoutGuide.leadingAnchor, constant: 12),
            toolbar.trailingAnchor.constraint(equalTo: safeAreaLayoutGuide.trailingAnchor, constant: -12),
            toolbar.heightAnchor.constraint(greaterThanOrEqualToConstant: 58)
        ])
        let pan = UIPanGestureRecognizer(target: self, action: #selector(drag(_:))); pan.delegate = self
        addGestureRecognizer(pan); updateSummary()
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) is unavailable") }
    private func control(_ key: String, id: String, action: Selector) -> UIButton {
        let button = UIButton(type: .system); button.setTitle(L.text(key), for: .normal)
        button.accessibilityIdentifier = id; button.backgroundColor = UIColor(white: 0.22, alpha: 1)
        button.layer.cornerRadius = 6; button.addTarget(self, action: action, for: .touchUpInside)
        button.widthAnchor.constraint(greaterThanOrEqualToConstant: 95).isActive = true
        button.heightAnchor.constraint(equalToConstant: 44).isActive = true; return button
    }
    private func eyeRect(_ eye: Int) -> CGRect {
        guard bounds.width > 0, bounds.height > 0,
              let rect = try? HeadsetFit.eyeRect(settings: draft, imageAspect: imageAspect(),
                    eyeAspect: Double(bounds.width / 2 / bounds.height), eyeSign: eye == 0 ? -1 : 1) else { return .zero }
        let width = bounds.width / 2, x = CGFloat(eye) * width
        return CGRect(x: x + (CGFloat(rect.center.x - rect.halfSize.x) + 1) * width / 2,
                      y: (1 - CGFloat(rect.center.y + rect.halfSize.y)) * bounds.height / 2,
                      width: CGFloat(rect.halfSize.x) * width, height: CGFloat(rect.halfSize.y) * bounds.height)
    }
    private func eyeViewport(_ eye: Int) -> CGRect {
        return CGRect(x: CGFloat(eye) * bounds.width / 2, y: 0, width: bounds.width / 2, height: bounds.height)
    }
    override func layoutSubviews() {
        super.layoutSubviews()
        if dragEntry != nil && dragSize != bounds.size { dragEntry = nil; dragCorner = nil }
        for eye in 0..<2 {
            let rect = eyeRect(eye), viewport = eyeViewport(eye)
            borders[eye].frame = viewport
            borders[eye].path = UIBezierPath(rect: rect.offsetBy(dx: -viewport.minX, dy: 0)).cgPath
            let visible = rect.intersection(viewport)
            interiors[eye].frame = visible.insetBy(dx: min(32, visible.width / 4), dy: min(32, visible.height / 4))
            for corner in 0..<4 {
                let sign = signs[corner]
                let raw = CGPoint(x: sign.x < 0 ? rect.minX : rect.maxX, y: sign.y > 0 ? rect.minY : rect.maxY)
                let eyeStart = CGFloat(eye) * bounds.width / 2
                // Even an offset portrait stream can extend beyond its eye
                // viewport. Keep the four real controls reachable, while the
                // projected resize still uses the actual centered image.
                let point = CGPoint(x: min(eyeStart + bounds.width / 2 - 16, max(eyeStart + 16, raw.x)),
                    y: min(bounds.height - 16, max(toolbar.frame.maxY + 16, raw.y)))
                handles[eye][corner].frame = CGRect(x: point.x - 14, y: point.y - 14, width: 28, height: 28)
            }
        }
        bringSubviewToFront(toolbar)
    }
    func refreshVideoAspect() { setNeedsLayout() }
    private func updateSummary() {
        summary.text = String(format: L.text("editorSummary"), draft.scale * 100, draft.offsetX, draft.offsetY)
        // This is a read-only description of the real draft, also useful to
        // assistive clients. It never provides a settings mutation path.
        if let data = try? JSONEncoder().encode(draft) { summary.accessibilityValue = String(data: data, encoding: .utf8) }
    }
    func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer, shouldReceive touch: UITouch) -> Bool {
        return !(touch.view is UIControl) && !toolbar.frame.contains(touch.location(in: self))
    }
    @objc private func drag(_ gesture: UIPanGestureRecognizer) {
        if gesture.state == .began {
            // Subtract accumulated movement to use the actual touch-down point.
            let location = gesture.location(in: self), translation = gesture.translation(in: self)
            let start = CGPoint(x: location.x - translation.x, y: location.y - translation.y)
            dragEntry = nil; dragCorner = nil
            let eye = start.x < bounds.width / 2 ? 0 : 1
            for corner in 0..<4 where handles[eye][corner].frame.insetBy(dx: -14, dy: -14).contains(start) {
                dragEntry = draft; dragCorner = signs[corner]; break
            }
            if dragEntry == nil && eyeRect(eye).intersection(eyeViewport(eye)).contains(start) { dragEntry = draft }
            dragImageAspect = imageAspect(); dragSize = bounds.size
            dragEyeAspect = Double(bounds.width / 2 / bounds.height)
        }
        guard let entry = dragEntry, dragSize == bounds.size, dragSize.width > 0, dragSize.height > 0 else { return }
        if gesture.state == .changed || gesture.state == .ended {
            let translation = gesture.translation(in: self)
            let delta = FitPoint(x: Double(translation.x * 4 / dragSize.width), y: Double(-translation.y * 2 / dragSize.height))
            let next: VRSettings?
            if let corner = dragCorner {
                next = try? HeadsetFit.resize(entry: entry, delta: delta, cornerSign: corner,
                    imageAspect: dragImageAspect, eyeAspect: dragEyeAspect)
            } else if let panDelta = try? HeadsetFit.mobilePanDelta(
                screenDelta: FitPoint(x: Double(translation.x), y: Double(translation.y)),
                eyeSize: FitPoint(x: Double(dragSize.width / 2), y: Double(dragSize.height))) {
                next = try? HeadsetFit.pan(entry: entry, delta: panDelta)
            } else { next = nil }
            if let next = next { draft = next; updateSummary(); setNeedsLayout(); onDraft?(draft) }
        }
        if [.ended, .cancelled, .failed].contains(gesture.state) { dragEntry = nil }
    }
    @objc private func saveDraft() { onSave?(draft) }
    @objc private func discardDraft() { onDiscard?() }
}
