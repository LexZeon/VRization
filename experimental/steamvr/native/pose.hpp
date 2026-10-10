// Original VRization pose validation/conversion, MIT. Valve's ABI is BSD-3-Clause.
#pragma once
#include "ipc.hpp"
#include <openvr_driver.h>

namespace vrization {
inline vr::DriverPose_t driver_pose(const PoseHeader& input, std::uint64_t now) {
    vr::DriverPose_t pose{};
    pose.qWorldFromDriverRotation.w=1; pose.qDriverFromHeadRotation.w=1; pose.qRotation.w=1;
    pose.deviceIsConnected=pose_header(input) && !(input.flags & ~7U) &&
        (input.flags & kActive) && fresh(input.tickMs,now);
    pose.poseIsValid=valid_pose(input,now);
    pose.result=pose.poseIsValid?vr::TrackingResult_Running_OK:
        (pose.deviceIsConnected?vr::TrackingResult_Running_OutOfRange:vr::TrackingResult_Uninitialized);
    if (pose.poseIsValid) {
        // Both sides use OpenVR world axes (+X right, +Y up, -Z forward), XYZW on the wire.
        // Normalize the tolerated finite quantization error, not an invalid quaternion.
        double sum=0; for(double q:input.quaternionXYZW) sum+=q*q;
        const double scale=1/std::sqrt(sum);
        pose.qRotation={input.quaternionXYZW[3]*scale,input.quaternionXYZW[0]*scale,
            input.quaternionXYZW[1]*scale,input.quaternionXYZW[2]*scale};
        for(int axis=0;axis<3;++axis) pose.vecPosition[axis]=input.positionXYZ[axis];
    }
    // No synthesized velocity, prediction, positional tracking or mouse control.
    pose.willDriftInYaw=true; pose.shouldApplyHeadModel=false;
    return pose;
}
} // namespace vrization
