// Original VRization local frame pacing, MIT. Microsoft API contract references
// are recorded in licenses/README.md; no upstream implementation is copied.
#pragma once
#include <Windows.h>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <string>

namespace vrization {
inline std::runtime_error timing_error(const char* operation, DWORD error=GetLastError()) {
    return std::runtime_error(std::string(operation)+" failed (Windows error "+std::to_string(error)+")");
}
inline std::int64_t qpc_frequency() {
    LARGE_INTEGER value{};
    if(!QueryPerformanceFrequency(&value) || value.QuadPart<=0)
        throw timing_error("QueryPerformanceFrequency");
    return value.QuadPart;
}
inline std::int64_t qpc_ticks() {
    LARGE_INTEGER value{};
    if(!QueryPerformanceCounter(&value) || value.QuadPart<0)
        throw timing_error("QueryPerformanceCounter");
    return value.QuadPart;
}

// Every deadline is derived from the original epoch, including the fractional
// QPC tick. Work and wake-up lateness cannot accumulate into the next interval.
class FrameCadence {
    std::int64_t frequency_, epoch_, next_;
    unsigned fps_;
    std::int64_t fractional_ticks(unsigned slot) const {
        // slot <= fps; split the product to avoid frequency*slot overflow.
        return (frequency_/fps_)*slot+((frequency_%fps_)*slot)/fps_;
    }
    std::int64_t first_after(std::int64_t now) const {
        if(now<epoch_) throw std::invalid_argument("Frame clock moved before its epoch");
        const auto elapsed=now-epoch_;
        const auto seconds=elapsed/frequency_;
        const auto remainder=elapsed%frequency_;
        unsigned lower=1, upper=fps_;
        while(lower<upper) {
            const auto middle=lower+(upper-lower)/2;
            if(fractional_ticks(middle)>remainder) upper=middle;
            else lower=middle+1;
        }
        const auto fraction=fractional_ticks(lower);
        const auto limit=(std::numeric_limits<std::int64_t>::max)();
        if(seconds>(limit-fraction)/frequency_) throw std::overflow_error("Frame deadline overflow");
        const auto offset=seconds*frequency_+fraction;
        if(epoch_>limit-offset) throw std::overflow_error("Frame deadline overflow");
        return epoch_+offset;
    }
public:
    FrameCadence(std::int64_t frequency,unsigned fps,std::int64_t epoch)
        :frequency_(frequency),epoch_(epoch),next_(0),fps_(fps) {
        if(fps<1 || fps>120 || frequency<static_cast<std::int64_t>(fps) || epoch<0)
            throw std::invalid_argument("Invalid frame cadence");
        next_=first_after(epoch);
    }
    std::int64_t deadline() const { return next_; }
    void advance(std::int64_t now) {
        if(now<next_) throw std::invalid_argument("Cannot consume an early frame deadline");
        // Permit one next frame immediately when late, then skip all missed
        // deadlines. There is never a burst replaying frames that were missed.
        next_=first_after(now);
    }
};

class LocalFrameTimer {
    HANDLE handle_=nullptr;
    bool highResolution_=false;
public:
    LocalFrameTimer(const LocalFrameTimer&)=delete;
    LocalFrameTimer& operator=(const LocalFrameTimer&)=delete;
    explicit LocalFrameTimer(bool preferHighResolution=true) {
        // CREATE_WAITABLE_TIMER_HIGH_RESOLUTION (0x2) needs Windows 10 1803+.
        // The explicit value also builds with SDKs predating the named flag.
        constexpr DWORD highResolutionFlag=0x00000002;
        if(preferHighResolution) {
            handle_=CreateWaitableTimerExW(nullptr,nullptr,highResolutionFlag,TIMER_MODIFY_STATE|SYNCHRONIZE);
            if(handle_) highResolution_=true;
            else {
                const auto error=GetLastError();
                if(error!=ERROR_INVALID_PARAMETER && error!=ERROR_NOT_SUPPORTED)
                    throw timing_error("CreateWaitableTimerExW high-resolution",error);
            }
        }
        if(!handle_) handle_=CreateWaitableTimerExW(nullptr,nullptr,0,TIMER_MODIFY_STATE|SYNCHRONIZE);
        if(!handle_) throw timing_error("CreateWaitableTimerExW");
    }
    ~LocalFrameTimer() {
        if(handle_) { CancelWaitableTimer(handle_); CloseHandle(handle_); }
    }
    bool high_resolution() const { return highResolution_; }
    HANDLE handle() const { return handle_; }
    void cancel() { CancelWaitableTimer(handle_); }
    void arm(std::int64_t ticks,std::int64_t frequency) {
        if(ticks<=0 || frequency<=0 || ticks>frequency)
            throw std::invalid_argument("Invalid relative frame timer duration");
        // Round relative time up. QPC is rechecked after each wake-up, so timer
        // granularity or an early wake cannot release an early frame.
        const auto units=static_cast<LONGLONG>(std::ceil(static_cast<long double>(ticks)*10000000.0L/frequency));
        LARGE_INTEGER due{}; due.QuadPart=-(std::max)(LONGLONG{1},units);
        if(!SetWaitableTimer(handle_,&due,0,nullptr,nullptr,FALSE))
            throw timing_error("SetWaitableTimer");
    }
};

class FramePacer {
    std::int64_t frequency_;
    FrameCadence cadence_;
    LocalFrameTimer timer_;
public:
    explicit FramePacer(unsigned fps)
        :frequency_(qpc_frequency()),cadence_(frequency_,fps,qpc_ticks()) {}
    bool high_resolution() const { return timer_.high_resolution(); }
    std::int64_t deadline() const { return cadence_.deadline(); }
    template<class StopRequested>
    bool wait_next(HANDLE stopEvent,StopRequested stopRequested) {
        for(;;) {
            if(stopRequested()) { timer_.cancel(); return false; }
            if(stopEvent) {
                const auto state=WaitForSingleObject(stopEvent,0);
                if(state==WAIT_OBJECT_0) { timer_.cancel(); return false; }
                if(state!=WAIT_TIMEOUT) throw timing_error("WaitForSingleObject stop event");
            }
            const auto now=qpc_ticks();
            if(now>=cadence_.deadline()) { cadence_.advance(now); return !stopRequested(); }
            // Host Stop wakes this wait directly. Console signals only set an
            // atomic flag, so slice long periods to bound that cancellation.
            const auto slice=(std::max)(std::int64_t{1},frequency_/20);
            timer_.arm((std::min)(cadence_.deadline()-now,slice),frequency_);
            HANDLE handles[2]={stopEvent,timer_.handle()};
            const auto result=WaitForMultipleObjects(stopEvent?2:1,stopEvent?handles:handles+1,FALSE,INFINITE);
            // Stop is index zero: cancellation wins if both objects signaled.
            if(stopEvent && result==WAIT_OBJECT_0) { timer_.cancel(); return false; }
            if(result==WAIT_OBJECT_0+(stopEvent?1:0)) continue;
            if(result==WAIT_FAILED) throw timing_error("WaitForMultipleObjects frame timer");
            throw std::runtime_error("Unexpected frame timer wait result");
        }
    }
};
}
