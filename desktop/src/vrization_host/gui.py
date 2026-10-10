"""Small Windows control panel; all capture and network work stays off the UI thread."""

import ctypes
import argparse
from dataclasses import replace
import os
from pathlib import Path
import queue
import socket
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser

from ._version import __version__
from .capture import CaptureConfig, MssCaptureSource
from .connection import ConnectionCoordinator, UsbConnectService
from .input import EmergencyHotkey
from .i18n import load_language, save_language, translate
from .protocol import Settings
from .profiles import PROFILES, CUSTOM, apply_profile, capture_profile, initial_capture
from .server import HostServer
from .storage import (load_preferences, save_preferences, preference_path,
                      load_usb_preferences, save_usb_preferences, default_preferences,
                      load_input_preferences, save_input_preferences)
from .usb import UsbManager
from .usb_tools import (OFFICIAL_DOWNLOAD_PAGE, UsbToolsError, default_tools_directory,
                        import_platform_tools)
from .view_editor import HeadsetEditor

BG, CARD, PANEL, TEXT, MUTED, ACCENT = "#0b1220", "#142136", "#1b2b43", "#e7f0fc", "#94a8c4", "#52e3bc"


def configure_dpi_awareness(load_library=None) -> str:
    """Call before Tk on Windows; older Windows 10 needs the earlier APIs.

    A caller-supplied DLL loader allows testing without changing process DPI
    or creating a window. Existing manifest/DPI settings are left intact when
    Windows refuses a second change.
    """
    load_library = load_library or ctypes.WinDLL
    attempts = (
        ("user32", "SetProcessDpiAwarenessContext", [ctypes.c_void_p],
         (ctypes.c_void_p(-4),), False, "per-monitor-v2"),
        ("shcore", "SetProcessDpiAwareness", [ctypes.c_int],
         (2,), True, "per-monitor"),
        ("user32", "SetProcessDPIAware", [], (), False, "system"),
    )
    for library, name, argtypes, args, hresult, mode in attempts:
        try:
            function = getattr(load_library(library), name)
            function.argtypes, function.restype = argtypes, ctypes.c_int
            result = function(*args)
            succeeded = result == 0 if hresult else bool(result)
            if succeeded:
                return mode
        except (OSError, AttributeError):
            continue
    return "unchanged"


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


def monitor_display_name(index: int, monitor: dict, language: str = "en") -> str:
    """Read the monitor's EDID product descriptor; never mutate Windows settings."""
    fallback = ("所有显示器" if index == 0 else f"显示器 {index}") if language == "zh" else (
        "All displays" if index == 0 else f"Display {index}")
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
        self.language = load_language()
        self.events = queue.SimpleQueue()
        self.settings, self.config = load_preferences()
        self.config = initial_capture(self.config, preference_path().exists())
        self.usb_preferences = load_usb_preferences()
        self.input_preferences = load_input_preferences()
        self.usb_status = ("USB waiting: install Android Platform Tools or Apple Devices; LAN is available", {})
        self.usb_serials = ()
        self.usb_import_active = False
        self.usb_import_dialog = None
        self.settings_revision = 0
        if initial_monitor is not None:
            self.config = replace(self.config, monitor=initial_monitor, region=None)
        self.server = HostServer(settings=self.settings, capture_config=self.config,
                                 on_event=self.events.put)
        self._stop_in_progress = False
        self._stop_generation = 0
        self.connection = ConnectionCoordinator(self.events.put, lambda: self.server.running,
                                                 lambda: self._stop_in_progress)
        self.usb = UsbManager(self.server, self.events.put, adb_path=self.usb_preferences["adb_path"],
                              preferred_serial=self.usb_preferences["preferred_serial"],
                              start_request=self.connection.request)
        self.control = UsbConnectService(self.connection, self.usb.control_authorized.is_set)
        self.server.usb_authorized = self.usb.authorized.is_set
        self.root.title(self.tr("VRization · 桌面 VR 串流"))
        self.root.configure(bg=BG)
        self.root.geometry(f"{min(1060, self.root.winfo_screenwidth() - 80)}x"
                           f"{min(830, self.root.winfo_screenheight() - 80)}")
        self.root.minsize(min(900, self.root.winfo_screenwidth() - 80),
                          min(650, self.root.winfo_screenheight() - 80))
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.ip = local_ip()
        self.syncing = False
        self.save_job = None
        self.last_error = None
        self.editor = None
        self._style()
        self._build()
        if initial_monitor is not None and 0 <= initial_monitor < len(self.monitors):
            monitor = self.monitors[initial_monitor]
            x, y = monitor["left"] + 100, monitor["top"] + 100
            width, height = min(1060, monitor["width"] - 120), min(980, monitor["height"] - 120)
            self.root.minsize(min(900, width), min(650, height))
            self.root.geometry(f"{width}x{height}{x:+d}{y:+d}")
        self.hotkey = EmergencyHotkey(lambda: self.server.disarm("F8 emergency stop"),
                                      lambda error: self.events.put({"event": "hotkey_error", "message": error}))
        self.hotkey_available = self.hotkey.start()
        self.server.set_auto_control(self.input_preferences["gyro_control_enabled"] and self.hotkey_available)
        self._refresh_input_status()
        self.root.after(100, self._pump)
        self.usb.start(self.usb_preferences["enabled"])
        try:
            self.control.start()
        except (OSError, TimeoutError):
            self._log(self.tr("USB connection control is unavailable; start streaming on this PC"))

    def tr(self, text, **values):
        return translate(text, self.language, **values)

    def change_language(self, event=None):
        language = "zh" if self.language_choice.get() == "简体中文" else "en"
        if language == self.language:
            return
        self.language = language
        try:
            save_language(language)
        except OSError as exc:
            self._log(self.tr("语言设置未保存: {error}", error=exc))
        selected_tab = self.notebook.index("current")
        if self.editor is not None:
            self.editor.discard()
        self._rebuild(selected_tab)

    def _rebuild(self, selected_tab=0):
        self.settings, self.settings_revision = self.server.get_settings_snapshot()
        self.config = self.server.get_capture_config()
        for widget in self.root.winfo_children():
            widget.destroy()
        self.root.title(self.tr("VRization · 桌面 VR 串流"))
        self._build()
        self.notebook.select(min(selected_tab, self.notebook.index("end") - 1))
        if self._stop_in_progress:
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="disabled")
            self.code_label.configure(text="— — — — — —")
            self.status.configure(text=self.tr("Stopping streaming; waiting for cleanup"), fg=MUTED)
            self.stats.configure(text="—")
        elif self.server.running:
            self.code_label.configure(text=" ".join(self.server.token))
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="normal")
            self.status.configure(text=self.tr("●  手机已连接  /  LIVE" if self.server.controller.connected
                                               else "●  等待手机连接  /  WAITING"), fg=ACCENT)

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

    def _paragraph(self, parent, text, **kwargs):
        label = ttk.Label(parent, text=text, wraplength=600, justify="left", **kwargs)
        parent.bind("<Configure>", lambda event: label.configure(
            wraplength=max(160, event.width - 40)), add="+")
        return label

    def _build(self):
        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill="both", expand=True, padx=24, pady=20)
        header = tk.Frame(outer, bg=BG)
        header.pack(fill="x", pady=(0, 16))
        brand = tk.Frame(header, bg=BG)
        brand.pack(side="left")
        self._label(brand, "VRization", 27, ACCENT).pack(anchor="w")
        self._label(brand, self.tr("把桌面带入你的视野  /  DESKTOP → POCKET VR"), 10, MUTED).pack(anchor="w")
        ttk.Button(header, text=self.tr("F8  紧急停止控制"), style="Danger.TButton",
                   command=lambda: self.server.disarm("desktop emergency stop")).pack(side="right", pady=8)
        self.language_choice = ttk.Combobox(header, values=("English", "简体中文"),
                                           state="readonly", width=11)
        self.language_choice.set("简体中文" if self.language == "zh" else "English")
        self.language_choice.pack(side="right", padx=(8, 12))
        self.language_choice.bind("<<ComboboxSelected>>", self.change_language)

        hero = tk.Frame(outer, bg=CARD, padx=20, pady=16)
        hero.pack(fill="x", pady=(0, 14))
        left = tk.Frame(hero, bg=CARD)
        left.pack(side="left", fill="x", expand=True)
        self._label(left, self.tr("01   连接手机"), 11, MUTED).pack(anchor="w")
        self.code_label = self._label(left, "— — — — — —", 32, ACCENT)
        self.code_label.pack(anchor="w", pady=(4, 0))
        self.address_label = self._label(left, self.tr("电脑地址  {ip} : 8765", ip=self.ip), 11)
        self.address_label.pack(anchor="w")
        hint = self._label(left, self.tr("USB: tap Connect on either device. Automatic detection does not start streaming. LAN: start on this PC, then use the address and code above."),
                           9, MUTED, justify="left", anchor="w", wraplength=550)
        hint.pack(fill="x", pady=(5, 0))
        self.usb_label = self._label(left, self.tr(self.usb_status[0], **self.usb_status[1]), 9, MUTED,
                                     justify="left", wraplength=550)
        self.usb_label.pack(fill="x", pady=(4, 0))
        left.bind("<Configure>", lambda event: (
            hint.configure(wraplength=max(160, event.width)),
            self.usb_label.configure(wraplength=max(160, event.width))))
        actions = tk.Frame(hero, bg=CARD)
        actions.pack(side="right", padx=(15, 0))
        left.pack_forget()
        left.pack(side="left", fill="x", expand=True)
        self.start_button = ttk.Button(actions, text=self.tr("Connect / Start streaming"), style="Primary.TButton", command=self.start)
        self.start_button.pack(fill="x", pady=(0, 8))
        row = tk.Frame(actions, bg=CARD)
        row.pack(fill="x")
        self.stop_button = ttk.Button(row, text=self.tr("停止"), command=self.stop, state="disabled")
        self.stop_button.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(row, text=self.tr("复制连接"), command=self.copy_link).pack(side="left", fill="x", expand=True)
        ttk.Button(actions, text=self.tr("USB connection…"),
                   command=self.show_usb_settings).pack(fill="x", pady=(8, 0))

        modes = ttk.Frame(outer, padding=(16, 10))
        modes.pack(fill="x", pady=(0, 12))
        ttk.Label(modes, text=self.tr("02   选择模式"), style="Muted.TLabel").pack(side="left", padx=(0, 15))
        self.mode = tk.StringVar(value=self.settings.mode)
        for text, value in [(self.tr("全屏  Full"), "full"), (self.tr("大屏幕  Cinema"), "cinema"), (self.tr("First-person"), "fps")]:
            ttk.Radiobutton(modes, text=text, variable=self.mode, value=value,
                            command=lambda: self.change_setting("mode", self.mode.get())).pack(side="left", padx=8)

        self.notebook = ttk.Notebook(outer, height=330)
        fit = self._scroll_tab(self.tr("Headset editor"))
        capture = self._scroll_tab(self.tr("串流设置  /  STREAM"))
        view = self._scroll_tab(self.tr("VR 画面  /  VIEW"))
        game = self._scroll_tab(self.tr("游戏控制  /  INPUT"))
        self._capture_tab(capture)
        self._fit_tab(fit)
        self.setting_vars = {}
        self._view_tab(view)
        self._game_tab(game)

        footer = tk.Frame(outer, bg=BG)
        footer.pack(side="bottom", fill="x")
        bottom = tk.Frame(footer, bg=BG)
        bottom.pack(fill="x", pady=(12, 0))
        self.status = self._label(bottom, self.tr("●  尚未启动  /  READY"), 10, MUTED)
        self.status.pack(side="left")
        self.stats = self._label(bottom, self.tr("JPEG · USB / LAN · v{version}", version=__version__), 9, MUTED)
        self.stats.pack(side="right")
        self.log = tk.Text(footer, height=3, bg=BG, fg=MUTED, bd=0, highlightthickness=0,
                           font=("Microsoft YaHei UI", 9), state="disabled", wrap="word")
        self.log.pack(fill="x", pady=(6, 0))
        self.notebook.pack(fill="both", expand=True)
        self._log(self.tr("Ready. First-person gyro mouse control is on by default for the desktop and games; F8 pauses it."))

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
        self.usb_settings_canvas = tab.master
        tab.columnconfigure(1, weight=1)
        try:
            self.monitors = MssCaptureSource.monitors()
        except Exception:
            self.monitors = [{"left": 0, "top": 0, "width": self.root.winfo_screenwidth(),
                              "height": self.root.winfo_screenheight()}]
        names = [f"{i} · {monitor_display_name(i, m, self.language)}  {m['width']} × {m['height']}"
                 for i, m in enumerate(self.monitors)]
        ttk.Label(tab, text=self.tr("捕获显示器")).grid(row=0, column=0, sticky="w", padx=(0, 24), pady=6)
        self.monitor = ttk.Combobox(tab, values=names, state="readonly")
        self.monitor.current(min(self.config.monitor, len(names) - 1))
        self.monitor.grid(row=0, column=1, sticky="ew", pady=6)
        self.monitor.bind("<<ComboboxSelected>>", lambda event: self.apply_capture())
        preset = ttk.Frame(tab)
        preset.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        ttk.Label(preset, text=self.tr("Performance profile")).pack(side="left", padx=(0, 12))
        self.profile_names = list(PROFILES) + [CUSTOM]
        self.profile = ttk.Combobox(preset, values=[self.tr(name) for name in self.profile_names],
                                    state="readonly", width=39)
        self.profile.current(self.profile_names.index(capture_profile(self.config)))
        self.profile.pack(side="left", fill="x", expand=True)
        self.profile.bind("<<ComboboxSelected>>", self.change_profile)
        quality = ttk.Frame(tab)
        quality.grid(row=2, column=0, columnspan=2, sticky="ew", pady=14)
        self.capture_vars = {}
        for label, key, values, current in [
                (self.tr("最长输出边"), "width", (640, 960, 1280, 1600, 1920, 2560, 3840), self.config.width),
                (self.tr("目标帧率"), "fps", (15, 24, 30, 45, 60), self.config.fps),
                (self.tr("JPEG 质量"), "quality", (45, 60, 65, 75, 80, 85, 95), self.config.quality)]:
            group = ttk.Frame(quality)
            group.pack(side="left", fill="x", expand=True, padx=(0, 18))
            ttk.Label(group, text=label, style="Muted.TLabel").pack(anchor="w", pady=(0, 5))
            variable = tk.StringVar(value=str(current))
            self.capture_vars[key] = variable
            box = ttk.Combobox(group, textvariable=variable, values=values, width=12, state="readonly")
            box.pack(fill="x")
            box.bind("<<ComboboxSelected>>", lambda event: self.apply_capture())
        region = ttk.LabelFrame(tab, text=self.tr(" 选区捕获 · 物理像素坐标 "), padding=12)
        region.grid(row=3, column=0, columnspan=2, sticky="ew", pady=6)
        self.use_region = tk.BooleanVar(value=self.config.region is not None)
        ttk.Checkbutton(region, text=self.tr("启用选区"), variable=self.use_region,
                        command=self.apply_capture).pack(anchor="w")
        values = self.config.region or (0, 0, 1280, 720)
        self.region_vars = []
        row = ttk.Frame(region)
        row.pack(fill="x", pady=(8, 0))
        for label, current in zip((self.tr("左 X"), self.tr("上 Y"), self.tr("宽"), self.tr("高")), values):
            ttk.Label(row, text=label, style="Muted.TLabel").pack(side="left", padx=(0, 4))
            variable = tk.StringVar(value=str(current))
            self.region_vars.append(variable)
            ttk.Entry(row, textvariable=variable, width=7).pack(side="left", padx=(0, 10))
        ttk.Button(row, text=self.tr("应用"), command=self.apply_capture).pack(side="right")
        ttk.Button(region, text=self.tr("拖动框选屏幕区域"), command=self.select_region).pack(anchor="w", pady=(10, 0))
        self._paragraph(tab, text=self.tr("Low latency is the default for new users. FPS is a capture target; actual latency depends on the phone and connection. Try borderless mode for black games. Audio is not streamed."),
                  style="Muted.TLabel").grid(row=4, column=0, columnspan=2, sticky="w", pady=15)
        usb = ttk.LabelFrame(tab, text=self.tr("USB connection"), padding=12)
        usb.grid(row=5, column=0, columnspan=2, sticky="ew", pady=6)
        self.usb_enabled = tk.BooleanVar(value=self.usb_preferences["enabled"])
        ttk.Checkbutton(usb, text=self.tr("Detect authorized USB phones automatically (recommended)"),
                        variable=self.usb_enabled, command=self.change_usb).pack(anchor="w")
        self.usb_device = ttk.Combobox(usb, state="readonly", values=[self.tr("Automatic (one Android device)")]+list(self.usb_serials))
        self.usb_device.set(self.usb_preferences["preferred_serial"] or self.tr("Automatic (one Android device)"))
        self.usb_device.pack(fill="x", pady=(8, 4))
        self.usb_device.bind("<<ComboboxSelected>>", self.change_usb)
        ttk.Button(usb, text=self.tr("Download official Android USB tools…"),
                   command=self.download_usb_tools).pack(anchor="w", pady=(6, 0))
        self.usb_import_button = ttk.Button(usb, text=self.tr("Import downloaded USB tools ZIP…"),
                                           command=self.import_usb_tools,
                                           state="disabled" if self.usb_import_active else "normal")
        self.usb_import_button.pack(anchor="w", pady=6)
        self._paragraph(usb, self.tr("For Android, download Windows Platform Tools 37.0.1 from Google, read and accept Google's terms, then import the ZIP. VRization does not download or bundle these tools. Existing installations are kept."),
                        style="Muted.TLabel").pack(fill="x", pady=4)
        ttk.Button(usb, text=self.tr("Choose official SDK adb.exe…"), command=self.choose_adb).pack(anchor="w", pady=6)
        self.usb_path_label = self._paragraph(usb, self.tr("Android USB tool: {path}",
                                                        path=self.usb_preferences["adb_path"] or self.tr("Automatic detection")),
                                             style="Muted.TLabel")
        self.usb_path_label.pack(fill="x", pady=4)
        self._paragraph(usb, self.tr("Android needs USB debugging and this computer's approval. iPhone needs Apple Devices and Trust This Computer. USB does not need a LAN firewall rule. Existing USB mappings are never replaced."),
                        style="Muted.TLabel").pack(fill="x", pady=4)

    def change_profile(self, event=None):
        selected = self.profile_names[self.profile.current()]
        config = apply_profile(self.config, selected)
        for key in ("width", "fps", "quality"):
            self.capture_vars[key].set(str(getattr(config, key)))
        self.apply_capture()

    def show_usb_settings(self):
        canvas = self.usb_settings_canvas
        self.notebook.select(canvas.master)
        self.root.update_idletasks()
        canvas.yview_moveto(1)

    def change_usb(self, event=None):
        selected = self.usb_device.get()
        self.usb_preferences["preferred_serial"] = selected if selected in self.usb_serials else ""
        self.usb_preferences["enabled"] = self.usb_enabled.get()
        self.usb.preferred_serial = self.usb_preferences["preferred_serial"]
        self.usb.set_enabled(self.usb_preferences["enabled"])
        self._save_usb()

    def choose_adb(self):
        path = filedialog.askopenfilename(parent=self.root, title=self.tr("Choose adb.exe from official Android Platform Tools"),
                                          filetypes=[("Android Debug Bridge", "adb.exe")])
        if path:
            self._select_adb_path(path)

    def _select_adb_path(self, path):
        self.usb_preferences["adb_path"] = str(path)
        self.usb.adb_path = str(path)
        self.usb_path_label.configure(text=self.tr("Android USB tool: {path}", path=path))
        self._save_usb()

    def download_usb_tools(self):
        try:
            webbrowser.open(OFFICIAL_DOWNLOAD_PAGE)
        except OSError:
            self._log(self.tr("Could not open the download page. Visit developer.android.com/tools/releases/platform-tools."))

    def import_usb_tools(self):
        if self.usb_import_active:
            return
        if self.usb_import_dialog is not None and self.usb_import_dialog.winfo_exists():
            self.usb_import_dialog.lift()
            return
        package = filedialog.askopenfilename(parent=self.root, title=self.tr("Select Google's downloaded Windows Platform Tools 37.0.1 ZIP"),
                                              filetypes=[("ZIP", "*.zip")])
        if not package:
            return
        dialog = self.usb_import_dialog = tk.Toplevel(self.root)
        dialog.title(self.tr("Import downloaded USB tools ZIP…"))
        dialog.configure(bg=CARD)
        dialog.transient(self.root)
        body = ttk.Frame(dialog, padding=20)
        body.pack(fill="both", expand=True)
        self._paragraph(body, self.tr("Choose an installation folder. A platform-tools subfolder will be added; existing files will not be replaced.")).pack(fill="x")
        folder = tk.StringVar(value=str(default_tools_directory()))
        entry = ttk.Entry(body, textvariable=folder, width=65)
        entry.pack(fill="x", pady=(12, 8))

        def browse():
            initial = Path(folder.get()).expanduser()
            while not initial.is_dir() and initial != initial.parent:
                initial = initial.parent
            selected = filedialog.askdirectory(parent=dialog, initialdir=str(initial),
                                               title=self.tr("Choose USB tools installation folder"), mustexist=False)
            if selected:
                folder.set(selected)

        actions = ttk.Frame(body)
        actions.pack(fill="x")
        ttk.Button(actions, text=self.tr("Choose folder…"), command=browse).pack(side="left")
        ttk.Button(actions, text=self.tr("Cancel"), command=dialog.destroy).pack(side="right")

        def start_import():
            destination = folder.get().strip()
            dialog.destroy()
            self.usb_import_dialog = None
            self._start_usb_import(package, destination)

        ttk.Button(actions, text=self.tr("Import USB tools"), command=start_import,
                   style="Primary.TButton").pack(side="right", padx=8)

    def _start_usb_import(self, package, destination):
        if self.usb_import_active:
            return
        self.usb_import_active = True
        self.usb_import_button.configure(state="disabled")
        self._log(self.tr("Checking and importing USB tools…"))

        def import_worker():
            try:
                adb = import_platform_tools(package, destination)
                event = {"event": "usb_tools_import", "path": str(adb)}
            except UsbToolsError as exc:
                event = {"event": "usb_tools_import", "error": exc.code}
            except Exception:
                event = {"event": "usb_tools_import", "error": "write_failed"}
            self.events.put(event)

        threading.Thread(target=import_worker, name="vrization-usb-tools-import", daemon=True).start()

    def _finish_usb_import(self, event):
        self.usb_import_active = False
        self.usb_import_button.configure(state="normal")
        if "path" in event:
            self._select_adb_path(event["path"])
            self._log(self.tr("USB tools imported. Unlock the phone, allow USB debugging, then start streaming."))
            return
        messages = {
            "wrong_hash": "This ZIP is not the verified Windows Platform Tools 37.0.1 package. Download it from Google's official page.",
            "wrong_version": "This package has a different version. Use official Windows Platform Tools 37.0.1.",
            "invalid_archive": "The ZIP is incomplete or unsafe. Download the official Windows package again.",
            "unsafe_destination": "Choose a full folder path without shortcuts, links or junctions.",
            "destination_conflict": "This folder contains a different Platform Tools installation. It was kept unchanged; choose a new folder.",
            "busy": "An import is already using this folder. Wait for it to finish or choose another folder.",
            "write_failed": "Could not import USB tools. Check folder permissions and free space, then try another folder.",
        }
        self._log(self.tr(messages.get(event.get("error"), messages["write_failed"])))

    def _save_usb(self):
        try:
            save_usb_preferences(self.usb_preferences)
        except OSError as exc:
            self._log(self.tr("设置未保存: {error}", error=exc))

    def _slider(self, parent, key, label, low, high, row, format_value=None):
        format_value = format_value or (lambda value: f"{value:.2f}")
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 14), pady=9)
        variable = tk.DoubleVar(value=getattr(self.settings, key))
        self.setting_vars[key] = variable
        value_label = ttk.Label(parent, text=format_value(variable.get()), width=6, style="Muted.TLabel")
        value_label.grid(row=row, column=2, sticky="e", padx=(12, 0))

        def change(value):
            value_label.configure(text=format_value(float(value)))
            if not self.syncing:
                self.change_setting(key, round(float(value), 4))

        scale = ttk.Scale(parent, from_=low, to=high, variable=variable, command=change)
        scale.grid(row=row, column=1, sticky="ew", pady=9)
        variable.trace_add("write", lambda *_: value_label.configure(text=format_value(variable.get())))

    def _view_tab(self, tab):
        tab.columnconfigure(1, weight=1)
        for row, args in enumerate([
                ("scale", self.tr("手机盒子适配 · 画面缩放"), .5, 1),
                ("offsetX", self.tr("画面水平位置"), -.3, .3), ("offsetY", self.tr("画面垂直位置"), -.3, .3),
                ("eyeSeparation", self.tr("双眼画面间距"), -1, .2), ("fov", self.tr("视野角度"), 50, 110),
                ("distance", self.tr("大屏幕距离"), 1, 8), ("distortion", self.tr("镜片畸变补偿"), 0, .5)]):
            self._slider(tab, *args, row)
        buttons = ttk.Frame(tab)
        buttons.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        ttk.Button(buttons, text=self.tr("恢复画面默认"), command=self.reset_view).pack(side="left")
        ttk.Label(buttons, text=self.tr("设置会同步到已连接的手机，并自动保存。"),
                  style="Muted.TLabel").pack(side="right")

    def _fit_tab(self, tab):
        ttk.Label(tab, text=self.tr("Fit the picture by dragging"),
                  font=("Microsoft YaHei UI", 18, "bold")).pack(anchor="w", pady=(0, 10))
        self._paragraph(tab, self.tr("Drag one eye sideways to adjust eye spacing: that eye follows your drag and the other moves oppositely. Drag vertically to move both, or drag a corner to resize. Save syncs the fit; Discard keeps your previous fit."),
                        style="Muted.TLabel").pack(fill="x", pady=(0, 14))
        ttk.Button(tab, text=self.tr("Open visual headset editor"), style="Primary.TButton",
                   command=self.open_editor).pack(fill="x", pady=(0, 14))
        ttk.Button(tab, text=self.tr("Reset all settings to defaults"),
                   command=self.reset_all).pack(anchor="w", pady=(0, 8))
        self._paragraph(tab, self.tr("Reset restores the default picture, low latency, English, automatic USB and enabled gyro mouse. Your selected display/region and installed ADB path stay selected."),
                        style="Muted.TLabel").pack(fill="x")

    def open_editor(self):
        if self.editor is not None:
            self.editor.window.lift()
            return
        self.server.disarm("headset editor opened")
        settings, _ = self.server.get_settings_snapshot()
        self.editor = HeadsetEditor(self, settings)

    def commit_editor(self, draft):
        # Only the editor's four fit fields change; preserve any other settings
        # committed by the phone while the local preview was open.
        self.server.disarm("headset fit saved")
        self.server.update_settings({key: getattr(draft, key)
                                     for key in ("scale", "offsetX", "offsetY", "eyeSeparation")})
        self.server.recenter()
        self._save()

    def reset_all(self):
        if self.editor is not None:
            self.editor.discard()
        self.server.disarm("settings reset")
        defaults, self.config = default_preferences(self.server.get_capture_config())
        self.server.set_capture_config(self.config)
        self.server.update_settings(defaults.to_dict())
        self.server.recenter()
        self.usb_preferences.update(enabled=True, preferred_serial="")
        self.usb.preferred_serial = ""
        self.usb.set_enabled(True)
        self._save_usb()
        self.input_preferences = {"gyro_control_enabled": True}
        self.server.set_auto_control(bool(getattr(self, "hotkey_available", False)))
        self._save_input()
        self.language = "en"
        try:
            save_language("en")
        except OSError as exc:
            self._log(self.tr("语言设置未保存: {error}", error=exc))
        self._save()
        self._rebuild(0)
        self._log(self.tr("Default settings restored."))

    def _game_tab(self, tab):
        tab.columnconfigure(1, weight=1)
        ttk.Label(tab, text=self.tr("Gyro mouse · desktop and games"), font=("Microsoft YaHei UI", 17, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        self._paragraph(tab, text=self.tr("1  Connect your phone and select First-person. Gyro mouse is enabled by default.\n"
                                         "2  Move the mouse on the desktop, in apps or games; no game window is required.\n"
                                         "3  F8 pauses control. Click Resume gyro control to continue."),
                  style="Muted.TLabel").grid(row=1, column=0, columnspan=3, sticky="w", pady=10)
        self._slider(tab, "sensitivity", self.tr("转头灵敏度 · 像素 / 弧度"), 100, 3000, 2)
        self._slider(tab, "stabilization", self.tr("First-person stabilization strength"), 0, 1, 3,
                     format_value=lambda value: f"{value * 100:.0f}%")
        self._paragraph(tab, text=self.tr("0% keeps the current response. Increase it to reduce small shakes. Stronger stabilization can slow fine aiming. It applies only to First-person mouse control."),
                        style="Muted.TLabel").grid(row=4, column=0, columnspan=3, sticky="w", pady=7)
        self.invert = tk.BooleanVar(value=self.settings.invertY)
        ttk.Checkbutton(tab, text=self.tr("反转垂直方向"), variable=self.invert,
                        command=lambda: self.change_setting("invertY", self.invert.get())).grid(
            row=5, column=0, columnspan=3, sticky="w", pady=7)
        self.arm_var = tk.BooleanVar(value=self.input_preferences["gyro_control_enabled"])
        self.arm_check = ttk.Checkbutton(tab, text=self.tr("Gyro mouse control in First-person (default on)"), variable=self.arm_var,
                                        command=self.toggle_arm)
        self.arm_check.grid(row=6, column=0, columnspan=3, sticky="w", pady=15)
        self.arm_status = ttk.Label(tab, text=self.tr("控制已停止 / DISARMED"), foreground=ACCENT)
        self.arm_status.grid(row=7, column=0, columnspan=3, sticky="w", pady=(0, 12))
        ttk.Button(tab, text=self.tr("重新居中 / RECENTER"), command=self.server.recenter).grid(row=8, column=0, sticky="w")
        self.resume_button = ttk.Button(tab, text=self.tr("Resume gyro control"), command=self.resume_gyro_control)
        self.resume_button.grid(row=8, column=1, columnspan=2, sticky="w")
        self._refresh_input_status()
        self._paragraph(tab, text=self.tr("仅在可信局域网使用。部分使用原始输入、管理员权限或反作弊保护的游戏\n"
                           "可能忽略系统鼠标输入。此软件不绕过游戏保护。"),
                  style="Muted.TLabel").grid(row=9, column=0, columnspan=3, sticky="w", pady=18)

    def change_setting(self, key, value):
        try:
            # Apply the ordered server event below; a concurrent phone update can
            # already be newer than this call's returned settings snapshot.
            self.server.update_settings({key: value})
        except ValueError as exc:
            self._log(str(exc))

    def reset_view(self):
        defaults = Settings().to_dict()
        self.server.update_settings({key: defaults[key] for key in
            ("scale", "offsetX", "offsetY", "eyeSeparation", "fov", "distance", "distortion")})

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
                    raise ValueError(self.tr("选区超出桌面范围 / Region is outside the desktop"))
            self.config = config
            self.server.set_capture_config(config)
            self.profile.current(self.profile_names.index(capture_profile(config)))
            self._save_later()
            return True
        except ValueError as exc:
            messagebox.showerror(self.tr("检查串流设置"), str(exc), parent=self.root)
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
        canvas.create_text(30, 30, anchor="nw", text=self.tr("拖动选择区域 · Esc 取消"), fill="white",
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

    def start(self, *, notify_phone=True):
        if self._stop_in_progress:
            return False
        if self.server.running:
            if notify_phone:
                self.usb.request_connect()
            return True
        try:
            if not self.apply_capture():
                return False
            self.server.start()
            self.code_label.configure(text=" ".join(self.server.token))
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="normal")
            self.status.configure(text=self.tr("●  等待手机连接  /  WAITING"), fg=ACCENT)
            self._log(self.tr("串流服务已启动。如 Windows 询问防火墙，请只允许专用网络。"))
            if notify_phone:
                self.usb.request_connect()
            return True
        except (RuntimeError, OSError, TimeoutError) as exc:
            messagebox.showerror(self.tr("无法启动"), str(exc), parent=self.root)
            return False

    def stop(self):
        if self._stop_in_progress:
            return
        self._stop_in_progress = True
        self._stop_generation += 1
        generation = self._stop_generation
        self.server.request_stop()
        self.usb.request_stop_phone()
        self.connection.cancel()
        self.code_label.configure(text="— — — — — —")
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="disabled")
        self.status.configure(text=self.tr("Stopping streaming; waiting for cleanup"), fg=MUTED)
        self.stats.configure(text="—")

        def finish():
            try:
                self.usb.relay.stop()
                complete = self.server.stop()
                self.events.put({"event": "stop_result", "complete": complete, "generation": generation})
            except Exception:
                self.events.put({"event": "stop_result", "complete": False, "generation": generation})
        threading.Thread(target=finish, name="vr-stop", daemon=True).start()

    def copy_link(self):
        if not self.server.running:
            self._log(self.tr("请先开始串流，再复制连接地址。"))
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(f"ws://{self.ip}:8765/ws?token={self.server.token}")
        self._log(self.tr("连接地址已复制，请只分享给自己的手机。"))

    def toggle_arm(self):
        enabled = bool(self.arm_var.get())
        if enabled and self.editor is not None:
            self.arm_var.set(self.input_preferences["gyro_control_enabled"])
            self.server.disarm("headset editor opened")
            self._log(self.tr("Close the headset editor before resuming gyro control"))
            self._refresh_input_status()
            return
        self.input_preferences["gyro_control_enabled"] = enabled
        self.server.set_auto_control(enabled and self.hotkey_available)
        if enabled and self.hotkey_available:
            _, reason = self.server.resume_control()
            self._log(reason)
        elif enabled:
            self._log(self.tr("F8 is unavailable; gyro mouse is paused"))
        self._save_input()
        self._refresh_input_status()

    def resume_gyro_control(self):
        if self.editor is not None:
            self._log(self.tr("Close the headset editor before resuming gyro control"))
            return False
        if not self.hotkey_available:
            self._log(self.tr("F8 is unavailable; gyro mouse is paused"))
            return False
        self.input_preferences["gyro_control_enabled"] = True
        self.arm_var.set(True)
        self.server.set_auto_control(True)
        success, reason = self.server.resume_control()
        self._save_input()
        self._log(reason)
        self._refresh_input_status()
        return success

    def _save_input(self):
        try:
            save_input_preferences(self.input_preferences)
        except OSError as exc:
            self._log(self.tr("设置未保存: {error}", error=exc))

    def _refresh_input_status(self):
        state = self.server.get_control_state()
        enabled = self.input_preferences["gyro_control_enabled"]
        available = getattr(self, "hotkey_available", True)
        if not enabled:
            text = "Gyro mouse disabled"
        elif not available:
            text = "F8 is unavailable; gyro mouse is paused"
        elif state["paused"]:
            text = "Gyro mouse paused · click Resume gyro control"
        elif state["armed"]:
            text = "Gyro mouse active · F8 pauses"
        elif not state["connected"]:
            text = "Gyro mouse enabled · waiting for phone"
        elif state["mode"] != "fps":
            text = "Gyro mouse enabled · select First-person"
        else:
            text = "Gyro mouse enabled · waiting for fresh sensor data"
        self.arm_status.configure(text=self.tr(text))
        self.resume_button.configure(state="normal" if available and self.editor is None else "disabled")

    def _save_later(self):
        if self.save_job:
            self.root.after_cancel(self.save_job)
        self.save_job = self.root.after(500, self._save)

    def _save(self):
        self.save_job = None
        try:
            current_settings, _ = self.server.get_settings_snapshot()
            save_preferences(current_settings, self.config)
        except OSError as exc:
            self._log(self.tr("设置未保存: {error}", error=exc))

    def _log(self, message):
        message = self.tr(message)
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n")
        if int(self.log.index("end-1c").split(".")[0]) > 200:
            self.log.delete("1.0", "2.0")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _apply_settings_event(self, event):
        revision = event["revision"]
        if revision <= self.settings_revision:
            return False
        self.settings_revision = revision
        self.settings = Settings().update(event["settings"])
        self.syncing = True
        self.mode.set(self.settings.mode)
        self.invert.set(self.settings.invertY)
        for key, variable in self.setting_vars.items():
            variable.set(getattr(self.settings, key))
        self.syncing = False
        self._save_later()
        return True

    def _pump(self):
        for _ in range(100):
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            kind = event["event"]
            if kind == "stop_result" and (not self._stop_in_progress or
                                           event.get("generation") != self._stop_generation):
                continue
            if kind == "settings":
                self._apply_settings_event(event)
            elif kind == "connect_request":
                request = event["request"]
                if self.connection.accept(request):
                    self.connection.complete(request, self.start(notify_phone=False))
            elif kind == "connection":
                if event.get("session", self.server.session_generation) != self.server.session_generation:
                    continue
                if not event["connected"]:
                    self.stats.configure(text="—")
                if not self._stop_in_progress and self.server.running:
                    self.status.configure(text=self.tr("●  手机已连接  /  LIVE") if event["connected"] else self.tr("●  等待手机连接  /  WAITING"), fg=ACCENT)
                self._log(self.tr("手机已连接。") if event["connected"] else self.tr("手机已断开，控制已停止。"))
            elif kind == "input":
                self._log(event["reason"])
            elif kind == "stats":
                if (self.server.running and not self._stop_in_progress and self.server.controller.connected
                        and event.get("session", self.server.session_generation) == self.server.session_generation):
                    self.stats.configure(text=f"{event['width']} × {event['height']}  ·  {event['fps']:.0f} FPS  ·  {event['mbps']:.1f} Mbps")
            elif kind == "capture_masked":
                if (self.server.running and not self._stop_in_progress
                        and event.get("session") == self.server.session_generation):
                    self._log(self.tr(event["message"]))
            elif kind == "usb":
                self.usb_status = (event["message"], event["values"])
                self.usb_label.configure(text=self.tr(event["message"], **event["values"]))
                self._log(self.tr(event["message"], **event["values"]))
            elif kind == "usb_devices":
                self.usb_serials = event["serials"]
                self.usb_device.configure(values=[self.tr("Automatic (one Android device)")] + list(self.usb_serials))
            elif kind == "usb_tools_import":
                self._finish_usb_import(event)
            elif kind in ("error", "hotkey_error"):
                if kind == "hotkey_error":
                    self.hotkey_available = False
                    self.server.set_auto_control(False)
                    self.server.disarm("global F8 unavailable")
                if event["message"] != self.last_error:
                    self.last_error = event["message"]
                    self._log(event["message"])
            elif kind == "stop_result" and not event["complete"]:
                self.status.configure(text=self.tr("Stopping streaming; waiting for cleanup"), fg=MUTED)
                self._log(self.tr("Streaming cleanup is still in progress; Start stays disabled"))
            elif (kind == "server" and not event["running"]) or (kind == "stop_result" and event["complete"]):
                self._stop_in_progress = False
                self.start_button.configure(state="normal")
                self.stop_button.configure(state="disabled")
                self.status.configure(text=self.tr("●  已停止  /  STOPPED"), fg=MUTED)
                self.stats.configure(text="—")
        self._refresh_input_status()
        self.root.after(100, self._pump)

    def close(self):
        if self.editor is not None:
            self.editor.discard()
        self.connection.cancel(close=True)
        self.usb.cancel_connect()
        self.control.stop()
        self.usb.stop()
        self.server.stop()
        self.hotkey.stop()
        self._save()
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description="VRization Windows desktop streaming host")
    parser.add_argument("--monitor", type=int, help="Initial MSS capture/display index (for example 2)")
    args = parser.parse_args()
    if os.name == "nt":
        configure_dpi_awareness()
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
