import CoreMotion
import UIKit
import VRizationCore
#if STEAMVR_PREVIEW
import VRizationSteamVRCore
#endif

final class MotionSource {
    var onPose: ((Pose) -> Void)?
    var onUnavailable: (() -> Void)?
    var orientation: (() -> UIInterfaceOrientation)?
    private let manager = CMMotionManager()
    private var center = RotationCenter()
#if STEAMVR_PREVIEW
    var onQuaternion: ((HMDQuaternion?) -> Void)?
    private var hmdCenter = HMDQuaternionCenter()
#endif
    private var epoch: UInt64 = 0
    private var failed = false
    private var lastLandscapeLeft: Bool?
    var available: Bool { manager.isDeviceMotionAvailable && !failed }
    var running: Bool { manager.isDeviceMotionActive }

    func recenter() {
        center.recenter()
#if STEAMVR_PREVIEW
        hmdCenter.recenter()
#endif
    }
    func start() {
        guard available, !running else { return }
        epoch &+= 1
        let current = epoch
        recenter(); lastLandscapeLeft = nil
        manager.deviceMotionUpdateInterval = 1.0 / 60.0
        manager.startDeviceMotionUpdates(using: .xArbitraryZVertical, to: .main) { [weak self] motion, error in
            guard let self = self, self.epoch == current else { return }
            guard error == nil, let motion = motion else {
                self.failed = true; self.stop(); self.onUnavailable?(); return
            }
            let left = self.orientation?() == .landscapeLeft
            if self.lastLandscapeLeft != left { self.recenter(); self.lastLandscapeLeft = left }
            let r = motion.attitude.rotationMatrix
            // Core Motion is reference-to-device; the core transposes and remaps to landscape.
            guard let matrix = try? PoseMath.screenToWorld(referenceToDevice:
                [r.m11,r.m12,r.m13,r.m21,r.m22,r.m23,r.m31,r.m32,r.m33], landscapeLeft: left) else {
#if STEAMVR_PREVIEW
                self.onQuaternion?(nil)
#endif
                return
            }
#if STEAMVR_PREVIEW
            self.onQuaternion?(try? self.hmdCenter.sample(screenToWorld: matrix))
#endif
            guard let pose = try? self.center.sample(screenToWorld: matrix) else { return }
            self.onPose?(pose)
        }
    }
    func stop() { epoch &+= 1; manager.stopDeviceMotionUpdates() }
    deinit { manager.stopDeviceMotionUpdates() }
}
