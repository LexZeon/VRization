// Original VRization Python/native memory-order bridge, MIT. No OpenVR dependency.
// InterlockedIncrement/MemoryBarrier are Windows compiler intrinsics, not
// assumed kernel32 exports. This DLL exposes an explicit x64 ABI for ctypes.
#include <windows.h>
static_assert(sizeof(LONG)==4,"Seqlock ABI requires a 32-bit LONG");

extern "C" __declspec(dllexport) LONG VRizationSequenceIncrement(volatile LONG* sequence) {
    if(!sequence || (reinterpret_cast<ULONG_PTR>(sequence)&3U)) { SetLastError(ERROR_INVALID_PARAMETER);return 0; }
    return InterlockedIncrement(sequence);
}
extern "C" __declspec(dllexport) void VRizationMemoryBarrier() { MemoryBarrier(); }
