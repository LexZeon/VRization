"""Small Windows control panel; all capture and network work stays off the UI thread."""

import ctypes
import argparse
from dataclasses import replace
import os
import queue
import socket
import tkinter as tk
from tkinter import messagebox, ttk

from .capture import CaptureConfig, MssCaptureSource
from .input import EmergencyHotkey
from .protocol import Settings
from .server import HostServer
from .storage import load_preferences, save_preferences

BG, CARD, PANEL, TEXT, MUTED, ACCENT = "#0b1220", "#142136", "#1b2b43", "#e7f0fc", "#94a8c4", "#52e3bc"


def local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as route:
            route.connect(("192.0.2.1", 80))
            return route.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"


def monitor_display_name(index: int, monitor: dict) -> str:
    """Read the monitor's EDID product descriptor; never mutate Windows settings."""
    fallback = "所有显示器" if index == 0 else f"显示器 {index}"
    unique_id = monitor.get("unique_id", "")
    if os.name != "nt" or not isinstance(unique_id, str):
        return fallback
    parts = unique_id.split("#")
    if len(parts) < 3 or not parts[1] or not parts[2]:
        return fallback
    try:
        import winreg
        path = rf"SYSTEM\CurrentControlSet\Enum\DISPLAY\{parts[1]}\{parts[2]}\Device Parameters"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_READ) as key:
            edid, _ = winreg.QueryValueEx(key, "EDID")
        for offset in (54, 72, 90, 108):
            descriptor = edid[offset:offset + 18]
            if len(descriptor) == 18 and descriptor[:4] == b"\x00\x00\x00\xfc":
                name = descriptor[5:18].decode("ascii", errors="ignore").strip(" \x00\r\n")
                if name:
                    return name
    except (OSError, ValueError, TypeError):
        pass
    return fallback


class HostWindow:
    def __init__(self, root: tk.Tk, initial_monitor: int | None = None):
        self.root = root
        self.events = queue.SimpleQueue()
        self.settings, self.config = load_preferences()
        if initial_monitor is not None:
            self.config = replace(self.config, monitor=initial_monitor, region=None)
        self.server = HostServer(settings=self.settings, capture_config=self.config,
                                 on_event=self.events.put)
        self.root.title("VRization · 桌面 VR 串流")
        self.root.configure(bg=BG)
        self.root.geometry("1060x830")
        self.root.minsize(900, 740)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.ip = local_ip()
        self.syncing = False
        self.save_job = None
        self.last_error = None
        self._style()
        self._build()
        if initial_monitor is not None and 0 <= initial_monitor < len(self.monitors):
            monitor = self.monitors[initial_monitor]
            x, y = monitor["left"] + 100, monitor["top"] + 100
            self.root.geometry(f"1060x980{x:+d}{y:+d}")
        self.hotkey = EmergencyHotkey(lambda: self.server.disarm("F8 emergency stop"),
                                      lambda error: self.events.put({"event": "hotkey_error", "message": error}))
        self.hotkey_available = self.hotkey.start()
        self.root.after(100, self._pump)

    def _style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background=CARD, foreground=TEXT, font=("Microsoft YaHei UI", 10))
        style.configure("TFrame", background=CARD)
        style.configure("TLabel", background=CARD, foreground=TEXT)
        style.configure("Muted.TLabel", foreground=MUTED)
        style.configure("TButton", background=PANEL, foreground=TEXT, borderwidth=0, padding=(12, 9))
        style.map("TButton", background=[("active", "#294260"), ("disabled", "#172336")],
                  foreground=[("disabled", "#62738d")])
        style.configure("Primary.TButton", background=ACCENT, foreground="#062b23", font=("Microsoft YaHei UI", 10, "bold"))
        style.map("Primary.TButton", background=[("active", "#89f3d5"), ("disabled", "#263c49")])
        style.configure("Danger.TButton", background="#4b2333", foreground="#ffbacb")
        style.map("Danger.TButton", background=[("active", "#6a2e44")])
        style.configure("TEntry", fieldbackground=BG, foreground=TEXT, insertcolor=TEXT, padding=6)
        style.configure("TCombobox", fieldbackground=BG, foreground=TEXT, padding=6)
        style.map("TCombobox", fieldbackground=[("readonly", BG)], foreground=[("readonly", TEXT)])
        style.configure("TCheckbutton", background=CARD, foreground=TEXT, padding=3)
        style.map("TCheckbutton", background=[("active", CARD)])
        style.configure("TRadiobutton", background=CARD, foreground=TEXT, padding=5)
        style.map("TRadiobutton", background=[("active", PANEL)])
        style.configure("TNotebook", background=CARD, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED, padding=(16, 10))
        style.map("TNotebook.Tab", background=[("selected", CARD)], foreground=[("selected", ACCENT)])
        style.configure("Horizontal.TScale", background=CARD, troughcolor=BG)
        style.configure("TLabelframe", background=CARD, bordercolor=PANEL)
        style.configure("TLabelframe.Label", foreground=MUTED, background=CARD)
        self.root.option_add("*TCombobox*Listbox.background", CARD)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT)

    def _label(self, parent, text, size=10, color=TEXT, **kwargs):
        label = tk.Label(parent, text=text, bg=parent.cget("bg") if isinstance(parent, tk.Frame) else CARD,
                         fg=color, font=("Microsoft YaHei UI", size), **kwargs)
        return label

    def _build(self):
        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill="both", expand=True, padx=24, pady=20)
        header = tk.Frame(outer, bg=BG)
        header.pack(fill="x", pady=(0, 16))
        brand = tk.Frame(header, bg=BG)
        brand.pack(side="left")
        self._label(brand, "VRization", 27, ACCENT).pack(anchor="w")
        self._label(brand, "把桌面带入你的视野  /  DESKTOP → POCKET VR", 10, MUTED).pack(anchor="w")
        ttk.Button(header, text="F8  紧急停止控制", style="Danger.TButton",
                   command=lambda: self.server.disarm("desktop emergency stop")).pack(side="right", pady=8)

        hero = tk.Frame(outer, bg=CARD, padx=20, pady=16)
        hero.pack(fill="x", pady=(0, 14))
        left = tk.Frame(hero, bg=CARD)
        left.pack(side="left", fill="x", expand=True)
        self._label(left, "01   连接手机", 11, MUTED).pack(anchor="w")
        self.code_label = self._label(left, "— — — — — —", 32, ACCENT)
        self.code_label.pack(anchor="w", pady=(4, 0))
        self.address_label = self._label(left, f"电脑地址  {self.ip} : 8765", 11)
        self.address_label.pack(anchor="w")
        self._label(left, "手机与电脑连接同一个可信 Wi-Fi，输入地址和六位配对码。", 9, MUTED).pack(anchor="w", pady=(5, 0))
        actions = tk.Frame(hero, bg=CARD)
        actions.pack(side="right", padx=(15, 0))
        self.start_button = ttk.Button(actions, text="开始串流  /  START", style="Primary.TButton", command=self.start)
        self.start_button.pack(fill="x", pady=(0, 8))
        row = tk.Frame(actions, bg=CARD)
        row.pack(fill="x")
        self.stop_button = ttk.Button(row, text="停止", command=self.stop, state="disabled")
        self.stop_button.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(row, text="复制连接", command=self.copy_link).pack(side="left", fill="x", expand=True)

        modes = ttk.Frame(outer, padding=(16, 10))
        modes.pack(fill="x", pady=(0, 12))
        ttk.Label(modes, text="02   选择模式", style="Muted.TLabel").pack(side="left", padx=(0, 15))
        self.mode = tk.StringVar(value=self.settings.mode)
        for text, value in [("全屏  Full", "full"), ("大屏幕  Cinema", "cinema"), ("FPS 游戏", "fps")]:
            ttk.Radiobutton(modes, text=text, variable=self.mode, value=value,
                            command=lambda: self.change_setting("mode", self.mode.get())).pack(side="left", padx=8)

        self.notebook = ttk.Notebook(outer, height=330)
        capture = self._scroll_tab("串流设置  /  STREAM")
        view = self._scroll_tab("VR 画面  /  VIEW")
        game = self._scroll_tab("游戏控制  /  INPUT")
        self._capture_tab(capture)
        self.setting_vars = {}
        self._view_tab(view)
        self._game_tab(game)

        footer = tk.Frame(outer, bg=BG)
        footer.pack(side="bottom", fill="x")
        bottom = tk.Frame(footer, bg=BG)
        bottom.pack(fill="x", pady=(12, 0))
        self.status = self._label(bottom, "●  尚未启动  /  READY", 10, MUTED)
        self.status.pack(side="left")
        self.stats = self._label(bottom, "JPEG · 局域网 · v0.1.0", 9, MUTED)
        self.stats.pack(side="right")
        self.log = tk.Text(footer, height=3, bg=BG, fg=MUTED, bd=0, highlightthickness=0,
                           font=("Microsoft YaHei UI", 9), state="disabled", wrap="word")
        self.log.pack(fill="x", pady=(6, 0))
        self.notebook.pack(fill="both", expand=True)
        self._log("就绪。全屏不跟随转头；大屏幕在虚拟空间中显示；FPS 可在桌面授权后控制鼠标。")

    def _scroll_tab(self, title):
        wrapper = ttk.Frame(self.notebook)
        self.notebook.add(wrapper, text=title)
        canvas = tk.Canvas(wrapper, bg=CARD, highlightthickness=0, bd=0)
        scroll = ttk.Scrollbar(wrapper, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        interior = ttk.Frame(canvas, padding=20)
        item = canvas.create_window(0, 0, window=interior, anchor="nw")
        interior.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(item, width=event.width))
        canvas.bind("<MouseWheel>", lambda event: canvas.yview_scroll(-int(event.delta / 120), "units"))
        return interior

    def _capture_tab(self, tab):
        tab.columnconfigure(1, weight=1)
        try:
            self.monitors = MssCaptureSource.monitors()
        except Exception:
            self.monitors = [{"left": 0, "top": 0, "width": self.root.winfo_screenwidth(),
                              "height": self.root.winfo_screenheight()}]
        names = [f"{i} · {monitor_display_name(i, m)}  {m['width']} × {m['height']}"
                 for i, m in enumerate(self.monitors)]
        ttk.Label(tab, text="捕获显示器").grid(row=0, column=0, sticky="w", padx=(0, 24), pady=6)
        self.monitor = ttk.Combobox(tab, values=names, state="readonly")
        self.monitor.current(min(self.config.monitor, len(names) - 1))
        self.monitor.grid(row=0, column=1, sticky="ew", pady=6)
        self.monitor.bind("<<ComboboxSelected>>", lambda event: self.apply_capture())
        quality = ttk.Frame(tab)
        quality.grid(row=1, column=0, columnspan=2, sticky="ew", pady=14)
        self.capture_vars = {}
        for label, key, values, current in [
                ("最长输出边", "width", (640, 960, 1280, 1600, 1920, 2560, 3840), self.config.width),
                ("目标帧率", "fps", (15, 24, 30, 45, 60), self.config.fps),
                ("JPEG 质量", "quality", (45, 60, 75, 85, 95), self.config.quality)]:
            group = ttk.Frame(quality)
            group.pack(side="left", fill="x", expand=True, padx=(0, 18))
            ttk.Label(group, text=label, style="Muted.TLabel").pack(anchor="w", pady=(0, 5))
            variable = tk.StringVar(value=str(current))
            self.capture_vars[key] = variable
            box = ttk.Combobox(group, textvariable=variable, values=values, width=12, state="readonly")
            box.pack(fill="x")
            box.bind("<<ComboboxSelected>>", lambda event: self.apply_capture())
        region = ttk.LabelFrame(tab, text=" 选区捕获 · 物理像素坐标 ", padding=12)
        region.grid(row=2, column=0, columnspan=2, sticky="ew", pady=6)
        self.use_region = tk.BooleanVar(value=self.config.region is not None)
        ttk.Checkbutton(region, text="启用选区", variable=self.use_region,
                        command=self.apply_capture).pack(anchor="w")
        values = self.config.region or (0, 0, 1280, 720)
        self.region_vars = []
        row = ttk.Frame(region)
        row.pack(fill="x", pady=(8, 0))
        for label, current in zip(("左 X", "上 Y", "宽", "高"), values):
            ttk.Label(row, text=label, style="Muted.TLabel").pack(side="left", padx=(0, 4))
            variable = tk.StringVar(value=str(current))
            self.region_vars.append(variable)
            ttk.Entry(row, textvariable=variable, width=7).pack(side="left", padx=(0, 10))
        ttk.Button(row, text="应用", command=self.apply_capture).pack(side="right")
        ttk.Button(region, text="拖动框选屏幕区域", command=self.select_region).pack(anchor="w", pady=(10, 0))
        ttk.Label(tab, text="建议先使用 1280 / 30 FPS / 75 质量。降低宽度和质量可减少网络延迟。\n"
                           "若游戏呈现黑屏，请切换为无边框窗口模式。声音暂不串流。",
                  style="Muted.TLabel", justify="left").grid(row=3, column=0, columnspan=2, sticky="w", pady=15)

    def _slider(self, parent, key, label, low, high, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 14), pady=9)
        variable = tk.DoubleVar(value=getattr(self.settings, key))
        self.setting_vars[key] = variable
        value_label = ttk.Label(parent, text=f"{variable.get():.2f}", width=6, style="Muted.TLabel")
        value_label.grid(row=row, column=2, sticky="e", padx=(12, 0))

        def change(value):
            value_label.configure(text=f"{float(value):.2f}")
            if not self.syncing:
                self.change_setting(key, round(float(value), 4))

        scale = ttk.Scale(parent, from_=low, to=high, variable=variable, command=change)
        scale.grid(row=row, column=1, sticky="ew", pady=9)
        variable.trace_add("write", lambda *_: value_label.configure(text=f"{variable.get():.2f}"))

    def _view_tab(self, tab):
        tab.columnconfigure(1, weight=1)
        for row, args in enumerate([
                ("scale", "手机盒子适配 · 画面缩放", .5, 1),
                ("offsetX", "画面水平位置", -.3, .3), ("offsetY", "画面垂直位置", -.3, .3),
                ("eyeSeparation", "双眼画面间距", 0, .2), ("fov", "视野角度", 50, 110),
                ("distance", "大屏幕距离", 1, 8), ("distortion", "镜片畸变补偿", 0, .5)]):
            self._slider(tab, *args, row)
        buttons = ttk.Frame(tab)
        buttons.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        ttk.Button(buttons, text="恢复画面默认", command=self.reset_view).pack(side="left")
        ttk.Label(buttons, text="设置会同步到已连接的手机，并自动保存。",
                  style="Muted.TLabel").pack(side="right")

    def _game_tab(self, tab):
        tab.columnconfigure(1, weight=1)
        ttk.Label(tab, text="手机转头 → 游戏视角", font=("Microsoft YaHei UI", 17, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        ttk.Label(tab, text="1  在手机选择 FPS 模式，保持手机传感器运行。\n"
                           "2  在下方勾选允许控制，然后在 5 秒内切换到游戏窗口。\n"
                           "3  按 F8 随时停止。切换窗口、断线或传感器超时也会自动停止。",
                  justify="left", style="Muted.TLabel").grid(row=1, column=0, columnspan=3, sticky="w", pady=10)
        self._slider(tab, "sensitivity", "转头灵敏度 · 像素 / 弧度", 100, 3000, 2)
        self.invert = tk.BooleanVar(value=self.settings.invertY)
        ttk.Checkbutton(tab, text="反转垂直方向", variable=self.invert,
                        command=lambda: self.change_setting("invertY", self.invert.get())).grid(
            row=3, column=0, columnspan=3, sticky="w", pady=7)
        self.arm_var = tk.BooleanVar(value=False)
        self.arm_check = ttk.Checkbutton(tab, text="允许手机陀螺仪控制当前游戏鼠标", variable=self.arm_var,
                                        command=self.toggle_arm)
        self.arm_check.grid(row=4, column=0, columnspan=3, sticky="w", pady=15)
        self.arm_status = ttk.Label(tab, text="控制已停止 / DISARMED", foreground=ACCENT)
        self.arm_status.grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 12))
        ttk.Button(tab, text="重新居中 / RECENTER", command=self.server.recenter).grid(row=6, column=0, sticky="w")
        ttk.Label(tab, text="仅在可信局域网使用。部分使用原始输入、管理员权限或反作弊保护的游戏\n"
                           "可能忽略系统鼠标输入。此软件不绕过游戏保护。",
                  justify="left", style="Muted.TLabel").grid(row=7, column=0, columnspan=3, sticky="w", pady=18)

    def change_setting(self, key, value):
        try:
            self.settings = self.server.update_settings({key: value})
            self._save_later()
        except ValueError as exc:
            self._log(str(exc))

    def reset_view(self):
        defaults = Settings().to_dict()
        self.settings = self.server.update_settings({key: defaults[key] for key in
            ("scale", "offsetX", "offsetY", "eyeSeparation", "fov", "distance", "distortion")})
        self._save_later()

    def apply_capture(self):
        try:
            region = tuple(int(variable.get()) for variable in self.region_vars) if self.use_region.get() else None
            config = CaptureConfig(monitor=self.monitor.current(), region=region,
                                   **{key: int(value.get()) for key, value in self.capture_vars.items()})
            if region:
                desktop = self.monitors[0]
                x, y, width, height = region
                if (x < desktop["left"] or y < desktop["top"]
                        or x + width > desktop["left"] + desktop["width"]
                        or y + height > desktop["top"] + desktop["height"]):
                    raise ValueError("选区超出桌面范围 / Region is outside the desktop")
            self.config = config
            self.server.set_capture_config(config)
            self._save_later()
            return True
        except ValueError as exc:
            messagebox.showerror("检查串流设置", str(exc), parent=self.root)
            return False

    def select_region(self):
        self.server.disarm("selecting capture region")
        desktop = self.monitors[0]
        overlay = tk.Toplevel(self.root)
        overlay.overrideredirect(True)
        overlay.attributes("-topmost", True)
        overlay.attributes("-alpha", .38)
        overlay.configure(bg="black", cursor="crosshair")
        overlay.geometry(f"{desktop['width']}x{desktop['height']}+0+0")
        overlay.update_idletasks()
        if os.name == "nt":
            user32 = ctypes.WinDLL("user32")
            user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                                           ctypes.c_int, ctypes.c_int, ctypes.c_uint]
            user32.GetParent.argtypes = [ctypes.c_void_p]
            user32.GetParent.restype = ctypes.c_void_p
            hwnd = user32.GetParent(overlay.winfo_id())
            user32.SetWindowPos(hwnd, None, desktop["left"], desktop["top"],
                                desktop["width"], desktop["height"], 0x0010)
        canvas = tk.Canvas(overlay, bg="#081322", highlightthickness=0, cursor="crosshair")
        canvas.pack(fill="both", expand=True)
        canvas.create_text(30, 30, anchor="nw", text="拖动选择区域 · Esc 取消", fill="white",
                           font=("Microsoft YaHei UI", 20))
        start = []
        rect = [None]

        def down(event):
            start[:] = [event.x_root, event.y_root]
            if rect[0]:
                canvas.delete(rect[0])
            rect[0] = canvas.create_rectangle(event.x, event.y, event.x, event.y, outline=ACCENT, width=4)

        def drag(event):
            if start:
                canvas.coords(rect[0], start[0] - desktop["left"], start[1] - desktop["top"], event.x, event.y)

        def up(event):
            selected = False
            if start:
                x, y = min(start[0], event.x_root), min(start[1], event.y_root)
                width, height = abs(start[0] - event.x_root), abs(start[1] - event.y_root)
                if width >= 16 and height >= 16:
                    for variable, value in zip(self.region_vars, (x, y, width, height)):
                        variable.set(value)
                    self.use_region.set(True)
                    selected = True
            overlay.destroy()
            if selected:
                self.apply_capture()

        canvas.bind("<ButtonPress-1>", down)
        canvas.bind("<B1-Motion>", drag)
        canvas.bind("<ButtonRelease-1>", up)
        overlay.bind("<Escape>", lambda event: overlay.destroy())
        overlay.focus_force()
        overlay.grab_set()

    def start(self):
        try:
            if not self.apply_capture():
                return
            self.server.start()
            self.code_label.configure(text=" ".join(self.server.token))
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            self.status.configure(text="●  等待手机连接  /  WAITING", fg=ACCENT)
            self._log("串流服务已启动。如 Windows 询问防火墙，请只允许专用网络。")
        except (RuntimeError, OSError, TimeoutError) as exc:
            messagebox.showerror("无法启动", str(exc), parent=self.root)

    def stop(self):
        self.server.stop()
        self.code_label.configure(text="— — — — — —")
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.status.configure(text="●  已停止  /  STOPPED", fg=MUTED)

    def copy_link(self):
        if not self.server.running:
            self._log("请先开始串流，再复制连接地址。")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(f"ws://{self.ip}:8765/ws?token={self.server.token}")
        self._log("连接地址已复制，请只分享给自己的手机。")

    def toggle_arm(self):
        if self.arm_var.get():
            if not self.hotkey_available:
                self.arm_var.set(False)
                self._log("F8 热键不可用，暂不能启用游戏控制。")
                return
            success, reason = self.server.arm()
            self.arm_var.set(success)
            self.arm_status.configure(text=reason)
            self._log(reason)
        else:
            self.server.disarm("desktop control disabled")

    def _save_later(self):
        if self.save_job:
            self.root.after_cancel(self.save_job)
        self.save_job = self.root.after(500, self._save)

    def _save(self):
        self.save_job = None
        try:
            save_preferences(self.settings, self.config)
        except OSError as exc:
            self._log(f"设置未保存: {exc}")

    def _log(self, message):
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n")
        if int(self.log.index("end-1c").split(".")[0]) > 200:
            self.log.delete("1.0", "2.0")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _pump(self):
        for _ in range(100):
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            kind = event["event"]
            if kind == "settings":
                self.settings = Settings().update(event["settings"])
                self.syncing = True
                self.mode.set(self.settings.mode)
                self.invert.set(self.settings.invertY)
                for key, variable in self.setting_vars.items():
                    variable.set(getattr(self.settings, key))
                self.syncing = False
                self._save_later()
            elif kind == "connection":
                self.status.configure(text="●  手机已连接  /  LIVE" if event["connected"] else "●  等待手机连接  /  WAITING", fg=ACCENT)
                self._log("手机已连接。" if event["connected"] else "手机已断开，控制已停止。")
            elif kind == "input":
                self.arm_var.set(event["armed"])
                self.arm_status.configure(text="控制已启用 / ARMED" if event["armed"] else "控制已停止 / DISARMED")
                self._log(event["reason"])
            elif kind == "stats":
                self.stats.configure(text=f"{event['width']} × {event['height']}  ·  {event['fps']:.0f} FPS  ·  {event['mbps']:.1f} Mbps")
            elif kind in ("error", "hotkey_error"):
                if kind == "hotkey_error":
                    self.hotkey_available = False
                    self.server.disarm("global F8 unavailable")
                if event["message"] != self.last_error:
                    self.last_error = event["message"]
                    self._log(event["message"])
            elif kind == "server" and not event["running"]:
                self.start_button.configure(state="normal")
                self.stop_button.configure(state="disabled")
                self.status.configure(text="●  已停止  /  STOPPED", fg=MUTED)
        self.root.after(100, self._pump)

    def close(self):
        self.server.stop()
        self.hotkey.stop()
        self._save()
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description="VRization Windows desktop streaming host")
    parser.add_argument("--monitor", type=int, help="Initial MSS capture/display index (for example 2)")
    args = parser.parse_args()
    if os.name == "nt":
        with __import__("contextlib").suppress(OSError, AttributeError):
            ctypes.WinDLL("user32").SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    root = tk.Tk()
    root.withdraw()
    HostWindow(root, initial_monitor=args.monitor)
    restore_style = None
    if os.name == "nt" and args.monitor is not None:
        # A directed launch can be used on a second display while another person
        # keeps using the foreground application. Don't activate on first show.
        root.update_idletasks()
        user32 = ctypes.WinDLL("user32")
        user32.GetParent.argtypes = [ctypes.c_void_p]
        user32.GetParent.restype = ctypes.c_void_p
        get_style = user32.GetWindowLongPtrW
        set_style = user32.SetWindowLongPtrW
        get_style.argtypes, get_style.restype = [ctypes.c_void_p, ctypes.c_int], ctypes.c_ssize_t
        set_style.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]
        set_style.restype = ctypes.c_ssize_t
        hwnd = user32.GetParent(root.winfo_id())
        original = get_style(hwnd, -20)
        set_style(hwnd, -20, original | 0x08000000)  # WS_EX_NOACTIVATE during initial mapping only.
        restore_style = lambda: set_style(hwnd, -20, original)
    root.deiconify()
    if restore_style:
        root.after(1000, restore_style)
    root.mainloop()
