"""Separate preview control panel; importing it starts no capture or VR runtime."""
import argparse
from dataclasses import replace
from io import BytesIO
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
import tkinter as tk
from tkinter import messagebox,ttk
import webbrowser
from PIL import Image
from vrization_host.capture import CaptureConfig,MssCaptureSource
from vrization_host.gui import HostWindow,BG,CARD,TEXT,MUTED,ACCENT,configure_dpi_awareness,monitor_display_name
from vrization_host.i18n import load_language,save_language
from vrization_host.usb import UsbManager
from vrization_host.view_editor import HeadsetEditor
from . import __version__
from .capture import MirrorCaptureSource,overlay_config
from .host import PreviewHost
from .ipc import FrameWriter,frame_name
from .runtime import DriverManager,OwnedProcess,native_helper,diagnostics


def usb_factory(*args,**kwargs):
    return UsbManager(*args,android_video_port=18775,android_control_port=18774,
        android_component="org.vrization.steamvr/org.vrization.app.MainActivity",
        ios_video_port=18776,ios_control_port=18777,**kwargs)


class PhoneWindow(HostWindow):
    def __init__(self,root,route,monitor=None,on_close=None):
        self.route=route;self.on_close=on_close
        def factory(**kwargs):
            if route=="steamvr-phone":kwargs["capture_source"]=MirrorCaptureSource()
            return PreviewHost(route=route,**kwargs)
        super().__init__(root,initial_monitor=monitor,server_factory=factory,
                         usb_factory=usb_factory,control_port=18774)

    def words(self,en,zh):return zh if self.language=="zh" else en

    def _build(self):
        super()._build()
        self.root.title(f"VRization SteamVR · {__version__} · {self.route}")
        self.stats.configure(text=f"USB / LAN · {__version__}")
        self._log(self.words("Separate preview APK required. Stable v0.4.0 remains installed separately.",
                             "请使用独立实验版 APK；原来的 v0.4.0 可以同时保留。"))
        if self.route=="steamvr-phone":
            # Native stereo owns projection. Leave the stored direct-phone mode
            # untouched; the session descriptor selects the rendering path.
            def find_radios(parent):
                for child in parent.winfo_children():
                    if isinstance(child,ttk.Radiobutton):
                        child.pack_forget()
                        for label in child.master.winfo_children():
                            if isinstance(label,ttk.Label):label.configure(text=self.words(
                                "SteamVR stereo · independent left/right eyes", "SteamVR 双眼 · 独立左右画面"))
                    else:find_radios(child)
            find_radios(self.root)

    def _capture_tab(self,tab):
        super()._capture_tab(tab)
        if self.route!="steamvr-phone":return
        for child in tab.winfo_children():
            if isinstance(child,ttk.Label) and child.grid_info().get("row")==0:
                child.configure(text=self.words("Capture source","采集来源"))
            if isinstance(child,ttk.LabelFrame) and child.grid_info().get("row")==3:child.grid_remove()
        self.monitor.configure(values=("SteamVR Phone HMD compositor",),state="disabled")
        self.monitor.current(0);self.use_region.set(False)
        self.profile.configure(state="disabled")
        self.config=replace(self.config,width=min(1920,self.config.width),fps=max(30,self.config.fps),region=None)
        self.server.set_capture_config(self.config)
        for key in ("width","fps"):self.capture_vars[key].set(str(getattr(self.config,key)))
        for child in tab.winfo_children():
            for group in child.winfo_children():
                for widget in group.winfo_children():
                    if isinstance(widget,ttk.Combobox) and str(widget.cget("textvariable"))==str(self.capture_vars["width"]):
                        widget.configure(values=(640,960,1280,1600,1920))
                    if isinstance(widget,ttk.Combobox) and str(widget.cget("textvariable"))==str(self.capture_vars["fps"]):
                        widget.configure(values=(30,45,60))
        self._paragraph(tab,self.words(
            "Register the Phone HMD driver in the launcher first. Start SteamVR and select Phone HMD. This stream uses the compositor, regardless of desktop display selection. First preview: rotation only; no tracked controllers.",
            "先在启动器注册手机头显驱动，启动 SteamVR 并选择 Phone HMD。此路线直接读取 SteamVR 双眼画面；首版仅支持旋转，没有位置追踪或控制器。"),style="Muted.TLabel").grid(row=7,column=0,columnspan=2,sticky="w",pady=12)

    def apply_capture(self):
        if self.route!="steamvr-phone":return super().apply_capture()
        try:
            self.config=replace(self.config,region=None,width=min(1920,int(self.capture_vars["width"].get())),
                fps=max(30,int(self.capture_vars["fps"].get())),quality=int(self.capture_vars["quality"].get()))
            self.server.set_capture_config(self.config);self._save_later();return True
        except ValueError as error:
            messagebox.showerror("VRization SteamVR",str(error),parent=self.root);return False

    def _game_tab(self,tab):
        if self.route!="steamvr-phone":return super()._game_tab(tab)
        tab.columnconfigure(1,weight=1)
        ttk.Label(tab,text=self.words("Phone HMD rotation","手机头显旋转"),font=("Microsoft YaHei UI",17,"bold")).grid(row=0,column=0,columnspan=3,sticky="w")
        self._paragraph(tab,self.words(
            "Full gyro orientation drives the virtual SteamVR headset. F8, editing, Stop and disconnect invalidate tracking. Resume here to release an emergency pause. Rotation does not move the Windows mouse.",
            "完整陀螺仪姿态控制 SteamVR 虚拟头显。F8、编辑、停止及断开会停用追踪；紧急暂停后在此恢复。此路线不会移动 Windows 鼠标。"),style="Muted.TLabel").grid(row=1,column=0,columnspan=3,sticky="w",pady=15)
        self.arm_var=tk.BooleanVar(value=self.input_preferences["gyro_control_enabled"])
        self.invert=tk.BooleanVar(value=self.settings.invertY)
        self.arm_check=ttk.Checkbutton(tab,text=self.words("Enable HMD tracking","开启头显追踪"),variable=self.arm_var,command=self.toggle_arm)
        self.arm_check.grid(row=2,column=0,columnspan=3,sticky="w")
        self.arm_status=ttk.Label(tab,foreground=ACCENT);self.arm_status.grid(row=3,column=0,columnspan=3,sticky="w",pady=15)
        ttk.Button(tab,text=self.words("Recenter","重新居中"),command=self.server.recenter).grid(row=4,column=0,sticky="w")
        self.resume_button=ttk.Button(tab,text=self.words("Resume HMD tracking","恢复头显追踪"),command=self.resume_gyro_control)
        self.resume_button.grid(row=4,column=1,sticky="w")
        self._refresh_input_status()

    def _view_tab(self,tab):
        if self.route!="steamvr-phone":return super()._view_tab(tab)
        tab.columnconfigure(1,weight=1)
        for row,args in enumerate((("scale",self.words("Picture scale","画面缩放"),.5,1),
                ("offsetX",self.words("Horizontal offset","水平偏移"),-.3,.3),
                ("offsetY",self.words("Vertical offset","垂直偏移"),-.3,.3),
                ("eyeSeparation",self.words("Eye spacing","双眼间距"),-1,.2),
                ("distortion",self.words("Phone lens correction","手机镜片补偿"),0,.5))):
            self._slider(tab,*args,row)
        self._paragraph(tab,self.words("SteamVR owns perspective and per-eye aspect. The phone applies fit and one lens-correction stage; Cinema and enhanced-square projection are bypassed.",
            "透视及每眼比例由 SteamVR 决定。手机应用盒子适配和一次镜片补偿，不重复应用大屏幕或加强正方形变形。"),style="Muted.TLabel").grid(row=6,column=0,columnspan=3,sticky="w",pady=12)

    def _refresh_input_status(self):
        if self.route!="steamvr-phone":return super()._refresh_input_status()
        state=self.server.get_control_state();available=getattr(self,"hotkey_available",True)
        if not self.input_preferences["gyro_control_enabled"]:en,zh="HMD tracking disabled","头显追踪已关闭"
        elif not available:en,zh="F8 unavailable · tracking paused","F8 不可用 · 追踪暂停"
        elif state["paused"]:en,zh="Tracking paused · Resume on PC","追踪暂停 · 请在电脑恢复"
        elif state["armed"]:en,zh="HMD tracking active · F8 pauses","头显追踪中 · F8 暂停"
        else:en,zh="Waiting for phone orientation","等待手机姿态"
        self.arm_status.configure(text=self.words(en,zh))
        self.resume_button.configure(state="normal" if available and self.editor is None else "disabled")

    def open_editor(self):
        if self.route!="steamvr-phone":return super().open_editor()
        if self.editor is not None:self.editor.window.lift();return
        self.server.disarm("headset editor opened")
        self.editor=HeadsetEditor(self,self.server.get_settings_snapshot()[0],stereo=True)

    def close(self):
        super().close()
        if self.on_close:self.on_close()


class OverlayWindow:
    """One explicitly selected desktop display inside an existing SteamVR HMD."""
    def __init__(self,root,language,monitor=None,on_close=None):
        self.root,self.language,self.on_close=root,language,on_close
        self.thread=None;self.stop_event=threading.Event();self.events=queue.SimpleQueue();self.writer=None
        self.root.configure(bg=BG);self.root.title(f"VRization SteamVR overlay · {__version__}")
        self.root.geometry("720x490");self.root.protocol("WM_DELETE_WINDOW",self.close)
        self.monitors=MssCaptureSource.monitors()
        body=ttk.Frame(root,padding=24);body.pack(fill="both",expand=True)
        ttk.Label(body,text=self.words("Existing SteamVR headset","现有 SteamVR 头显"),font=("Microsoft YaHei UI",20,"bold")).pack(anchor="w")
        ttk.Label(body,text=self.words("Connect PC VR or a standalone headset using its existing SteamVR-compatible transport. This panel adds a desktop screen overlay; SteamVR games keep their native headset and controllers.",
            "用现有兼容方式将 PC VR 或一体机连接到 SteamVR。本面板添加桌面屏幕悬浮层；SteamVR 游戏继续使用原生头显和控制器。"),wraplength=660).pack(anchor="w",pady=16)
        self.monitor=ttk.Combobox(body,state="readonly",values=[f"{i} · {monitor_display_name(i,m,language)} {m['width']}×{m['height']}" for i,m in enumerate(self.monitors)])
        self.monitor.current(min(monitor if monitor is not None else 1,len(self.monitors)-1));self.monitor.pack(fill="x",pady=8)
        row=ttk.Frame(body);row.pack(fill="x",pady=10)
        self.fps=tk.StringVar(value="60");self.width=tk.StringVar(value="640")
        for text,var,values in ((self.words("Target FPS","目标帧率"),self.fps,(30,45,60)),(self.words("Max edge","最长边"),self.width,(640,960,1280,1600,1920))):
            ttk.Label(row,text=text).pack(side="left",padx=8);ttk.Combobox(row,textvariable=var,values=values,state="readonly",width=8).pack(side="left")
        actions=ttk.Frame(body);actions.pack(fill="x",pady=16)
        self.start_button=ttk.Button(actions,text=self.words("Start overlay","开始悬浮层"),command=self.start);self.start_button.pack(side="left")
        self.stop_button=ttk.Button(actions,text=self.words("Stop","停止"),command=self.stop,state="disabled");self.stop_button.pack(side="left",padx=8)
        self.status=ttk.Label(body,text=self.words("Ready · capture starts only after Start","就绪 · 点击开始后才采集"),wraplength=660);self.status.pack(anchor="w",pady=10)
        ttk.Label(body,text=f"{__version__} · 3 m screen · 2 m ahead · experimental",foreground=MUTED).pack(anchor="w")
        self.root.after(100,self.pump)

    def words(self,en,zh):return zh if self.language=="zh" else en
    def start(self):
        if self.thread is not None:return
        try:
            helper=native_helper("Overlay")
            config=CaptureConfig(monitor=self.monitor.current(),width=int(self.width.get()),fps=int(self.fps.get()),quality=45)
            config=overlay_config(config,self.monitors[config.monitor])
        except (OSError,ValueError) as error:messagebox.showerror("VRization",str(error),parent=self.root);return
        self.stop_event.clear();self.start_button.configure(state="disabled");self.stop_button.configure(state="normal")
        self.status.configure(text=self.words("Starting SteamVR overlay…","正在启动 SteamVR 悬浮层…"))
        def work():
            source=MssCaptureSource();child=None;writer=None
            try:
                name=frame_name();writer=FrameWriter(name)
                child=OwnedProcess(helper,["--frame-map",name],log=Path(os.environ["VRIZATION_PROFILE_DIRECTORY"])/"overlay.log")
                deadline=time.perf_counter();announced=False
                while not self.stop_event.is_set():
                    if child.poll() is not None:raise OSError("SteamVR overlay exited; check the connected headset and runtime.")
                    frame=source.read(config)
                    if frame is not None:
                        with Image.open(BytesIO(frame.jpeg)) as image:
                            if image.width>1920 or image.height>1080:raise ValueError("Overlay image exceeds the preview limits")
                            writer.publish(image.width,image.height,image.convert("RGB").tobytes("raw","BGRX"))
                        if not announced:self.events.put(("live",None));announced=True
                    deadline=max(deadline+1/config.fps,time.perf_counter())
                    self.stop_event.wait(max(0,deadline-time.perf_counter()))
            except Exception as error:self.events.put(("error",str(error)))
            finally:
                for resource in (writer,child,source):
                    if resource:
                        try:resource.close()
                        except Exception as error:self.events.put(("error",str(error)))
                self.events.put(("stopped",None))
        self.thread=threading.Thread(target=work,daemon=True,name="steamvr-overlay-capture");self.thread.start()

    def stop(self):
        self.stop_event.set();self.stop_button.configure(state="disabled")
        self.status.configure(text=self.words("Stopping; releasing overlay…","正在停止并释放悬浮层…"))
    def pump(self):
        try:
            while True:
                kind,value=self.events.get_nowait()
                if kind=="live" and not self.stop_event.is_set():self.status.configure(text=self.words("Overlay frames submitted · hardware verification pending","已提交悬浮层画面 · 实机验证待完成"))
                elif kind=="error":self.status.configure(text=value)
                elif kind=="stopped":self.thread=None;self.start_button.configure(state="normal");self.stop_button.configure(state="disabled")
        except queue.Empty:pass
        self.root.after(100,self.pump)
    def close(self):
        self.stop_event.set()
        if self.thread:
            self.status.configure(text=self.words("Waiting for owned resources to close…","等待本程序资源关闭…"))
            self.root.after(100,self.finish_close)
        else:self.finish_close()
    def finish_close(self):
        if self.thread and self.thread.is_alive():self.root.after(100,self.finish_close);return
        self.root.destroy()
        if self.on_close:self.on_close()


class Launcher:
    def __init__(self,root,monitor=None):
        self.root,self.monitor=root,monitor;self.child=None
        self.profile=Path(os.environ.get("VRIZATION_PROFILE_DIRECTORY") or
            str(Path(os.environ.get("LOCALAPPDATA",str(Path.home())))/"VRizationSteamVR/Windows"))
        os.environ["VRIZATION_PROFILE_DIRECTORY"]=str(self.profile)
        self.language=load_language();self.root.configure(bg=BG)
        self.root.title(f"VRization SteamVR · {__version__}");self.root.geometry("850x690")
        self.root.protocol("WM_DELETE_WINDOW",self.close);self.build()
        if monitor is not None:
            monitors=MssCaptureSource.monitors()
            if 0<=monitor<len(monitors):
                m=monitors[monitor];self.root.geometry(f"850x690{m['left']+80:+d}{m['top']+80:+d}")
    def words(self,en,zh):return zh if self.language=="zh" else en
    def build(self):
        for child in self.root.winfo_children():child.destroy()
        body=ttk.Frame(self.root,padding=26);body.pack(fill="both",expand=True)
        ttk.Label(body,text="VRization SteamVR 🧪",font=("Microsoft YaHei UI",24,"bold")).pack(anchor="w")
        language=ttk.Combobox(body,values=("English","简体中文"),state="readonly",width=12);language.set("简体中文" if self.language=="zh" else "English");language.pack(anchor="e")
        language.bind("<<ComboboxSelected>>",lambda event:self.change_language(language.get()))
        ttk.Label(body,text=self.words("Choose your connection route","选择连接路线"),font=("Microsoft YaHei UI",16,"bold")).pack(anchor="w",pady=14)
        self.buttons=[]
        for route,en,zh,detail_en,detail_zh in (
            ("direct-phone","📱 Direct phone · original features","📱 直接连接手机 · 原来的功能","USB default; desktop streaming and gyro mouse without SteamVR.","默认 USB；无需 SteamVR 的桌面串流和陀螺仪鼠标。"),
            ("steamvr-phone","🥽 Phone as SteamVR HMD","🥽 手机作为 SteamVR 头显","Independent stereo eyes + 3DOF gyro rotation. Separate preview app required.","独立双眼画面及三自由度旋转；需要独立实验版手机应用。"),
            ("steamvr-headset","🎮 Existing SteamVR headset","🎮 使用现有 SteamVR 头显","PC VR or a connected standalone headset; desktop overlay + native SteamVR games.","PC VR 或已连接的一体机；桌面悬浮层及原生 SteamVR 游戏。")):
            button=ttk.Button(body,text=self.words(en,zh),command=lambda selected=route:self.open_route(selected));button.pack(fill="x",pady=(8,4));self.buttons.append(button)
            ttk.Label(body,text=self.words(detail_en,detail_zh),wraplength=780,foreground=MUTED).pack(anchor="w",pady=(0,7))
        native=ttk.Frame(body);native.pack(fill="x",pady=18)
        for en,zh,action in (("Register Phone HMD","注册手机头显",lambda:self.driver(True)),("Remove this driver","移除此驱动",lambda:self.driver(False)),("Open SteamVR","打开 SteamVR",lambda:webbrowser.open("steam://run/250820"))):
            ttk.Button(native,text=self.words(en,zh),command=action).pack(side="left",padx=(0,8))
        ttk.Label(body,text=self.words("Driver registration changes only this preview's path. Keep the extracted folder in place. Switching between Phone HMD and physical HMD may require restarting SteamVR. No positional tracking or controllers in the phone preview.",
            "驱动注册仅添加本实验版路径；请保留解压文件夹。手机头显与真实头显切换可能需要重启 SteamVR。手机首版没有位置追踪或控制器。"),wraplength=780).pack(anchor="w",pady=6)
        self.status=ttk.Label(body,text=self.words("Hardware tests deferred to the next session.","实机测试留到下次。"),foreground=MUTED,wraplength=780);self.status.pack(anchor="w",pady=10)
        ttk.Label(body,text=f"{__version__} · English default · separate ports and preferences",foreground=MUTED).pack(anchor="w")
    def change_language(self,value):
        self.language="zh" if value=="简体中文" else "en";save_language(self.language);self.build()
    def driver(self,register):
        try:
            result=DriverManager().change(register)
            self.status.configure(text=result or self.words("Driver path updated. Restart SteamVR if already running.","驱动路径已更新；如果 SteamVR 已运行，请重启它。"))
        except (OSError,subprocess.TimeoutExpired) as error:messagebox.showerror("VRization SteamVR",str(error),parent=self.root)
    def open_route(self,route):
        if self.child is not None:return
        os.environ["VRIZATION_PROFILE_DIRECTORY"]=str(self.profile/route)
        save_language(self.language)
        target=tk.Toplevel(self.root)
        try:
            if route=="steamvr-headset":self.child=OverlayWindow(target,self.language,self.monitor,self.closed_route)
            else:self.child=PhoneWindow(target,route,self.monitor,self.closed_route)
        except Exception as error:
            target.destroy();os.environ["VRIZATION_PROFILE_DIRECTORY"]=str(self.profile)
            messagebox.showerror("VRization SteamVR",str(error),parent=self.root);return
        for button in self.buttons:button.configure(state="disabled")
    def closed_route(self):
        self.child=None;os.environ["VRIZATION_PROFILE_DIRECTORY"]=str(self.profile)
        for button in self.buttons:button.configure(state="normal")
    def close(self):
        if self.child:
            self.child.on_close=self.root.destroy;self.child.close()
        else:self.root.destroy()


def main():
    parser=argparse.ArgumentParser(description="VRization isolated SteamVR preview")
    parser.add_argument("--monitor",type=int)
    parser.add_argument("--diagnostics",action="store_true")
    parser.add_argument("--diagnostics-output",type=Path)
    args=parser.parse_args()
    if args.diagnostics or args.diagnostics_output:
        report=json.dumps(diagnostics(),indent=2)
        if args.diagnostics_output:args.diagnostics_output.write_text(report,encoding="utf-8")
        elif __import__("sys").stdout is not None:print(report)
        return
    if os.name!="nt":raise SystemExit("The SteamVR desktop preview requires Windows 10/11 x64.")
    configure_dpi_awareness();root=tk.Tk();root.withdraw();Launcher(root,args.monitor)
    root.update_idletasks();root.deiconify();root.mainloop()
