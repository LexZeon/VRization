// Original VRization owned-process cooperative Stop boundary, MIT.
#pragma once
#include "ipc.hpp"
#include <atomic>

namespace vrization {
inline std::atomic<bool> stopping{false};
inline HANDLE stopHandle=nullptr;
inline bool should_stop() {
    if(stopHandle && WaitForSingleObject(stopHandle,0)==WAIT_OBJECT_0) stopping=true;
    return stopping.load();
}
class StopEvent {
    HANDLE handle_=nullptr;
public:
    StopEvent(const StopEvent&)=delete;StopEvent& operator=(const StopEvent&)=delete;
    explicit StopEvent(const std::wstring& name) {
        if(name.empty()) return;
        if(!local_map_name(name)) throw std::runtime_error("Invalid Local stop event name");
        if(stopHandle) throw std::runtime_error("Stop event already owned in this process");
        handle_=OpenEventW(SYNCHRONIZE,FALSE,name.c_str());
        if(!handle_) throw std::runtime_error("Host stop event unavailable");
        stopHandle=handle_;
    }
    ~StopEvent() { if(handle_) { if(stopHandle==handle_) stopHandle=nullptr;CloseHandle(handle_); } }
};
inline BOOL WINAPI console_control(DWORD event) {
    if(event==CTRL_C_EVENT || event==CTRL_BREAK_EVENT || event==CTRL_CLOSE_EVENT || event==CTRL_SHUTDOWN_EVENT) {
        stopping=true; return TRUE;
    }
    return FALSE;
}
} // namespace vrization
