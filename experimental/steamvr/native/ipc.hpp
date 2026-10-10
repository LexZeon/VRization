// Original VRization IPC implementation, MIT. Valve interfaces are credited separately.
#pragma once
#include <windows.h>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace vrization {
constexpr wchar_t kPoseMapName[] = L"Local\\VRizationPhonePoseV1";
constexpr std::uint32_t kActive = 1, kTrackingValid = 2, kPaused = 4;
constexpr std::uint64_t kStaleMs = 500;
constexpr std::size_t kMaxFrameBytes = 1920ULL * 1080 * 4;
constexpr std::size_t kFrameMapBytes = 64 + kMaxFrameBytes;
#pragma pack(push, 1)
struct PoseHeader {
    char magic[4]; std::uint32_t version, headerSize, seqlock;
    std::uint64_t tickMs, poseSequence;
    double quaternionXYZW[4], positionXYZ[3];
    std::uint32_t flags; std::uint8_t reserved[36];
};
struct FrameHeader {
    char magic[4]; std::uint32_t version, headerSize, seqlock;
    std::uint32_t width, height, stride, flags;
    std::uint64_t tickMs; std::uint8_t reserved[24];
};
#pragma pack(pop)
static_assert(sizeof(PoseHeader) == 128 && offsetof(PoseHeader, seqlock) == 12);
static_assert(offsetof(PoseHeader, tickMs) == 16 && offsetof(PoseHeader, poseSequence) == 24);
static_assert(offsetof(PoseHeader, quaternionXYZW) == 32 && offsetof(PoseHeader, positionXYZ) == 64);
static_assert(offsetof(PoseHeader, flags) == 88);
static_assert(sizeof(FrameHeader) == 64 && offsetof(FrameHeader, seqlock) == 12);
static_assert(offsetof(FrameHeader, width) == 16 && offsetof(FrameHeader, height) == 20);
static_assert(offsetof(FrameHeader, stride) == 24 && offsetof(FrameHeader, flags) == 28);
static_assert(offsetof(FrameHeader, tickMs) == 32);

inline bool local_map_name(const std::wstring& name) {
    if (name.rfind(L"Local\\", 0) != 0 || name.size() < 8 || name.size() > 200) return false;
    for (std::size_t i = 6; i < name.size(); ++i) {
        const auto c = name[i];
        if (!(c >= L'0' && c <= L'9') && !(c >= L'a' && c <= L'z') &&
            !(c >= L'A' && c <= L'Z') && c != L'_' && c != L'-' && c != L'.') return false;
    }
    return true;
}
// Aligned 32-bit volatile read + acquire barrier. Interlocked operations are only
// used by the writer: readers must not write to a FILE_MAP_READ view.
inline std::uint32_t sequence(const void* memory) {
    auto value = *reinterpret_cast<const volatile LONG*>(static_cast<const std::uint8_t*>(memory) + 12);
    MemoryBarrier(); return static_cast<std::uint32_t>(value);
}
template<class Header> bool snapshot_header(const void* memory, Header& output) {
    if (!memory) return false;
    for (int retry = 0; retry < 4; ++retry) {
        const auto before = sequence(memory);
        if (before & 1U) { std::this_thread::yield(); continue; }
        Header copy{}; std::memcpy(&copy, memory, sizeof(copy)); MemoryBarrier();
        if (sequence(memory) == before && copy.seqlock == before) { output = copy; return true; }
    }
    return false;
}
inline bool pose_header(const PoseHeader& p) {
    return std::memcmp(p.magic, "VRP1", 4) == 0 && p.version == 1 && p.headerSize == 128 && !(p.seqlock & 1U);
}
inline bool fresh(std::uint64_t timestamp, std::uint64_t now) {
    return timestamp != 0 && timestamp <= now && now - timestamp <= kStaleMs;
}
inline bool valid_pose(const PoseHeader& p, std::uint64_t now) {
    if (!pose_header(p) || (p.flags & ~7U) || (p.flags & 3U) != 3U ||
        (p.flags & kPaused) || !fresh(p.tickMs, now)) return false;
    double length = 0;
    for (double q : p.quaternionXYZW) { if (!std::isfinite(q)) return false; length += q*q; }
    if (!std::isfinite(length) || std::abs(length - 1.0) > .02) return false;
    for (double x : p.positionXYZ) if (!std::isfinite(x) || std::abs(x) > 100.0) return false;
    return true;
}
inline bool frame_header(const FrameHeader& f) {
    return std::memcmp(f.magic, "VRF1", 4) == 0 && f.version == 1 && f.headerSize == 64 &&
        !(f.seqlock & 1U) && !(f.flags & ~kActive);
}
inline bool frame_dimensions(const FrameHeader& f) {
    return f.width >= 1 && f.width <= 1920 && f.height >= 1 && f.height <= 1080 &&
        f.stride == f.width * 4 && static_cast<std::size_t>(f.stride)*f.height <= kMaxFrameBytes;
}
inline bool snapshot_frame(const void* memory, FrameHeader& output, std::vector<std::uint8_t>& pixels) {
    if (!memory) return false;
    for (int retry = 0; retry < 4; ++retry) {
        const auto before = sequence(memory);
        if (before & 1U) { std::this_thread::yield(); continue; }
        FrameHeader copy{}; std::memcpy(&copy, memory, sizeof(copy));
        if (!frame_header(copy)) return false;
        if (copy.flags & kActive) {
            if (!frame_dimensions(copy)) return false;
            pixels.resize(static_cast<std::size_t>(copy.stride)*copy.height);
            std::memcpy(pixels.data(), static_cast<const std::uint8_t*>(memory)+64, pixels.size());
        } else pixels.clear();
        MemoryBarrier();
        if (sequence(memory) == before && copy.seqlock == before) { output = copy; return true; }
    }
    pixels.clear(); return false;
}

class Mapping {
    HANDLE handle_ = nullptr; void* view_ = nullptr;
public:
    Mapping() = default; Mapping(const Mapping&) = delete; Mapping& operator=(const Mapping&) = delete;
    ~Mapping() { close(); }
    void close() { if (view_) UnmapViewOfFile(view_); if (handle_) CloseHandle(handle_); view_=nullptr; handle_=nullptr; }
    bool open(const std::wstring& name, std::size_t bytes) {
        if (view_) return true;
        if (!local_map_name(name)) return false;
        handle_ = OpenFileMappingW(FILE_MAP_READ, FALSE, name.c_str());
        if (!handle_) return false;
        view_ = MapViewOfFile(handle_, FILE_MAP_READ, 0, 0, bytes);
        if (!view_) { close(); return false; } return true;
    }
    void create(const std::wstring& name, std::size_t bytes) {
        if (!local_map_name(name)) throw std::runtime_error("Invalid Local frame map name");
        handle_ = CreateFileMappingW(INVALID_HANDLE_VALUE, nullptr, PAGE_READWRITE, 0, static_cast<DWORD>(bytes), name.c_str());
        if (!handle_) throw std::runtime_error("Cannot create frame mapping");
        if (GetLastError() == ERROR_ALREADY_EXISTS) { close(); throw std::runtime_error("Frame mapping already has an owner"); }
        view_ = MapViewOfFile(handle_, FILE_MAP_ALL_ACCESS, 0, 0, bytes);
        if (!view_) { close(); throw std::runtime_error("Cannot map frame writer"); }
        std::memset(view_, 0, bytes);
    }
    void* data() { return view_; } const void* data() const { return view_; }
};
class FrameWriter {
    Mapping mapping_;
public:
    explicit FrameWriter(const std::wstring& name) { mapping_.create(name, kFrameMapBytes); publish(nullptr,0,0,false); }
    ~FrameWriter() { if (mapping_.data()) publish(nullptr,0,0,false); }
    void publish(const std::uint8_t* pixels, std::uint32_t width, std::uint32_t height, bool active=true) {
        FrameHeader header{}; std::memcpy(header.magic,"VRF1",4); header.version=1; header.headerSize=64;
        header.width=width; header.height=height; header.stride=width*4; header.flags=active?kActive:0;
        header.tickMs=GetTickCount64();
        if (active && (!pixels || !frame_dimensions(header))) throw std::runtime_error("Invalid BGRA frame dimensions");
        auto base=static_cast<std::uint8_t*>(mapping_.data()); auto lock=reinterpret_cast<volatile LONG*>(base+12);
        InterlockedIncrement(lock); MemoryBarrier();
        // Keep the live seqlock untouched while copying all other header bytes.
        std::memcpy(base,&header,12); std::memcpy(base+16,reinterpret_cast<const std::uint8_t*>(&header)+16,48);
        if (active) std::memcpy(base+64,pixels,static_cast<std::size_t>(header.stride)*height);
        MemoryBarrier(); InterlockedIncrement(lock);
    }
    const void* data() const { return mapping_.data(); }
};
} // namespace vrization
