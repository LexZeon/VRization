// Original VRization frame timing fixtures, MIT. No graphics device, phone,
// SteamVR runtime, driver registration or global timer setting is used.
#include "timing.hpp"
#include <atomic>
#include <chrono>
#include <iostream>
#include <thread>

namespace {
int checks=0;
void require(bool condition,const char* label) {
    ++checks; if(!condition) throw std::runtime_error(label);
}
template<class Operation> void rejects(Operation operation,const char* label) {
    bool rejected=false;
    try { operation(); } catch(const std::exception&) { rejected=true; }
    require(rejected,label);
}
class Event {
    HANDLE handle_=CreateEventW(nullptr,TRUE,FALSE,nullptr);
public:
    Event() { if(!handle_) throw vrization::timing_error("CreateEventW fixture"); }
    ~Event() { CloseHandle(handle_); }
    HANDLE get() const { return handle_; }
};
class JoiningThread {
    std::thread thread_;
public:
    template<class Operation> explicit JoiningThread(Operation operation):thread_(operation) {}
    ~JoiningThread() { if(thread_.joinable()) thread_.join(); }
};
void exact_schedule_tests() {
    // 6000 deadlines cover 100 seconds. A truncated 16-tick interval would
    // drift by four seconds; the absolute rational schedule must not drift.
    vrization::FrameCadence schedule(1000,60,7);
    bool exact=true;
    for(std::int64_t frame=1;frame<=6000;++frame) {
        exact=exact && schedule.deadline()==7+frame*1000/60;
        schedule.advance(schedule.deadline());
    }
    require(exact,"6000 non-divisible-frequency deadlines have no accumulated truncation drift");
    vrization::FrameCadence slow(1000000,60,0);
    slow.advance(17000);
    require(slow.deadline()==33333,"17ms work skips missed target without an extra whole-period sleep");
    slow.advance(34000);
    require(slow.deadline()==50000,"repeated slow work stays on the original 60Hz time axis");
    slow.advance(3017000);
    require(slow.deadline()==3033333,"long pause skips all missed frames instead of catch-up replay");
    rejects([&]{ slow.advance(3017001); },"second immediate catch-up frame is not permitted");
    require(slow.deadline()==3033333,"catch-up rejection leaves the future deadline intact");
    vrization::FrameCadence boundary(1000,60,0);
    boundary.advance(1000);
    require(boundary.deadline()==1016,"exact second boundary advances strictly into the future");
    vrization::FrameCadence one(1000,1,900);
    require(one.deadline()==1900,"1FPS cadence remains supported");
    one.advance(3900); require(one.deadline()==4900,"1FPS overrun skips expired seconds");
    vrization::FrameCadence fast(1000,120,0);
    require(fast.deadline()==8,"120FPS cadence remains supported");
    rejects([]{ vrization::FrameCadence value(1000,0,0); },"zero FPS rejected");
    rejects([]{ vrization::FrameCadence value(1000,121,0); },"FPS above native contract rejected");
    rejects([]{ vrization::FrameCadence value(0,60,0); },"zero frequency rejected");
    rejects([]{ vrization::FrameCadence value(59,60,0); },"sub-tick cadence rejected");
    rejects([]{ vrization::FrameCadence value(1000,60,-1); },"negative counter epoch rejected");
    const auto maximum=(std::numeric_limits<std::int64_t>::max)();
    rejects([&]{ vrization::FrameCadence value(1000,60,maximum); },"deadline overflow rejected before timer use");
    vrization::FrameCadence wide(maximum,120,0);
    require(wide.deadline()==maximum/120,"large frequency calculation avoids product overflow");
}
void timer_tests() {
    vrization::LocalFrameTimer normal(false);
    require(!normal.high_resolution(),"explicit standard timer exercises owned fallback without global settings");
    normal.arm(1000,1000000);
    require(WaitForSingleObject(normal.handle(),1000)==WAIT_OBJECT_0,"owned standard timer is a working one-shot wait");
    require(WaitForSingleObject(normal.handle(),0)==WAIT_TIMEOUT,"synchronization timer signal is consumed once");
    rejects([&]{ normal.arm(0,1000); },"zero relative duration rejected");
    rejects([&]{ normal.arm(-1,1000); },"negative relative duration rejected");
    rejects([&]{ normal.arm(1001,1000); },"unexpected oversized timer slice rejected");
    rejects([&]{ normal.arm(1,0); },"invalid timer frequency rejected");
    vrization::FramePacer pacer(60);
    std::cout<<"timer: "<<(pacer.high_resolution()?"owned high-resolution":"owned standard fallback")<<"\n";
    for(int frame=0;frame<3;++frame) {
        const auto target=pacer.deadline();
        require(pacer.wait_next(nullptr,[]{ return false; }),"QPC-paced frame is released");
        const auto observed=vrization::qpc_ticks();
        require(observed>=target,"timer never releases a frame before its QPC deadline");
        require(pacer.deadline()>target,"next deadline advances after one released frame");
    }
}
void cancellation_tests() {
    const auto frequency=vrization::qpc_frequency();
    Event alreadyStopped; require(SetEvent(alreadyStopped.get())!=0,"fixture Stop event signals");
    vrization::FramePacer immediate(1);
    const auto before=vrization::qpc_ticks();
    require(!immediate.wait_next(alreadyStopped.get(),[]{ return false; }),"pre-signaled Stop cancels before a frame");
    require(vrization::qpc_ticks()-before<frequency/2,"pre-signaled Stop does not wait the 1-second frame period");
    Event stop;
    vrization::FramePacer waiting(1);
    std::atomic<bool> signaled{false};
    const auto start=vrization::qpc_ticks();
    {
        JoiningThread trigger([&]{ std::this_thread::sleep_for(std::chrono::milliseconds(20)); signaled=SetEvent(stop.get())!=0; });
        require(!waiting.wait_next(stop.get(),[]{ return false; }),"host Stop interrupts a blocked frame timer");
    }
    require(signaled.load(),"fixture Stop signal succeeds");
    require(vrization::qpc_ticks()-start<frequency/2,"host Stop interrupts well before a low-FPS frame deadline");
    vrization::FramePacer console(1);
    std::atomic<bool> cancel{false};
    const auto consoleStart=vrization::qpc_ticks();
    {
        JoiningThread trigger([&]{ std::this_thread::sleep_for(std::chrono::milliseconds(20)); cancel=true; });
        require(!console.wait_next(nullptr,[&]{ return cancel.load(); }),"console atomic stop cancels without a host event");
    }
    require(vrization::qpc_ticks()-consoleStart<frequency/2,"bounded timer slices do not delay console Stop for one second");
    vrization::FramePacer latched(120);
    require(!latched.wait_next(nullptr,[]{ return true; }),"latched cancellation releases no new frame");
}
void handle_tests() {
    // Warm timer allocation before comparing handles; no other worker exists.
    { vrization::LocalFrameTimer warm; }
    DWORD before=0,after=0;
    require(GetProcessHandleCount(GetCurrentProcess(),&before)!=0,"fixture reads initial process handles");
    for(int count=0;count<32;++count) { vrization::LocalFrameTimer timer; timer.arm(1,1000); }
    require(GetProcessHandleCount(GetCurrentProcess(),&after)!=0,"fixture reads final process handles");
    require(after==before,"timer teardown cancels and closes every owned handle");
}
}
int main() {
    try {
        // Test the early-use invariant separately without advancing the clock.
        vrization::FrameCadence initial(1000,60,100);
        require(initial.deadline()==116,"first deadline includes the original epoch");
        rejects([&]{ initial.advance(115); },"early frame cannot consume a deadline");
        require(initial.deadline()==116,"early rejection keeps the existing schedule");
        exact_schedule_tests();timer_tests();cancellation_tests();handle_tests();
        std::cout<<checks<<" frame cadence checks passed; no SteamVR/device/global timer action\n";
        return 0;
    } catch(const std::exception& error) { std::cerr<<"failed: "<<error.what()<<"\n"; return 1; }
}
