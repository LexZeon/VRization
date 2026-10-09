"""Local picture-fit editor; rendering never captures or mutates the stream."""

from io import BytesIO
import math
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from .view_edit import EditTransaction, eye_bounds


class HeadsetEditor:
    def __init__(self, owner, entry):
        self.owner = owner
        self.transaction = EditTransaction(entry)
        self.gesture = None
        self.closed = False
        self.frame = None
        self.image = None
        self.photos = []
        self.job = None
        self.last_render = None
        self.window = tk.Toplevel(owner.root)
        self.window.title(owner.tr("Visual headset editor"))
        self.window.configure(bg="#0b1220")
        self.window.transient(owner.root)
        self.window.protocol("WM_DELETE_WINDOW", self.discard)
        self.window.geometry(f"960x610{owner.root.winfo_rootx():+d}{owner.root.winfo_rooty():+d}")
        self.window.minsize(620, 440)
        self.window.bind("<Escape>", lambda event: self.discard())

        heading = ttk.Frame(self.window, padding=16)
        heading.pack(fill="x")
        ttk.Label(heading, text=owner.tr("Drag corners to resize · Horizontal movement is reversed"),
                  font=("Microsoft YaHei UI", 14, "bold")).pack(anchor="w")
        ttk.Label(heading, text=owner.tr("Both eyes move together. The preview uses a flat picture; your viewing mode and lens settings are retained."),
                  wraplength=870, style="Muted.TLabel").pack(anchor="w", pady=(8, 0))
        choices = ttk.Frame(self.window, padding=(16, 0, 16, 12))
        choices.pack(fill="x")
        ttk.Label(choices, text=owner.tr("Phone preview shape")).pack(side="left", padx=(0, 12))
        self.aspect = ttk.Combobox(choices, state="readonly", width=12,
                                   values=("20:9", "16:9", "19.5:9"))
        self.aspect.current(0)
        self.aspect.pack(side="left")
        self.aspect.bind("<<ComboboxSelected>>", lambda event: self._shape_changed())
        self.values = ttk.Label(choices)
        self.values.pack(side="right")
        self.canvas = tk.Canvas(self.window, bg="#050910", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=16)
        self.canvas.bind("<Configure>", lambda event: self._shape_changed())
        self.canvas.bind("<ButtonPress-1>", self.begin)
        self.canvas.bind("<B1-Motion>", self.move)
        self.canvas.bind("<ButtonRelease-1>", lambda event: self.end())
        footer = ttk.Frame(self.window, padding=16)
        footer.pack(fill="x")
        ttk.Button(footer, text=owner.tr("Discard"), command=self.discard).pack(side="right")
        ttk.Button(footer, text=owner.tr("Save"), style="Primary.TButton",
                   command=self.save).pack(side="right", padx=(0, 12))
        ttk.Label(footer, text=owner.tr("Changes stay in this preview until you save."),
                  style="Muted.TLabel").pack(side="left")
        self.window.after_idle(self._take_grab)
        self.refresh()

    def _take_grab(self):
        if not self.closed:
            self.window.grab_set()

    @property
    def draft(self):
        return self.transaction.draft

    def _shape_changed(self):
        self.end()
        self.draw(force=True)

    def geometry(self):
        cw, ch = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        wide, high = map(float, self.aspect.get().split(":"))
        aspect = wide / high
        width = min(cw, ch * aspect)
        height = width / aspect
        return (cw - width) / 2, (ch - height) / 2, width, height

    def bounds(self, eye):
        x, y, width, height = self.geometry()
        image_aspect = self.image.width / self.image.height if self.image is not None else 16 / 9
        left, bottom, right, top = eye_bounds(self.draft, eye, image_aspect, width / 2 / height)
        return (x + eye * width / 2 + (left + 1) * width / 4,
                y + (1 - top) * height / 2,
                x + eye * width / 2 + (right + 1) * width / 4,
                y + (1 - bottom) * height / 2)

    def refresh(self):
        if self.closed:
            return
        frame = self.owner.server.get_latest_frame()
        if frame is not None and frame is not self.frame:
            self.frame = frame
            try:
                with Image.open(BytesIO(frame.jpeg)) as source:
                    self.image = source.convert("RGB")
            except (OSError, ValueError):
                self.image = None
        elif frame is None:
            self.frame = self.image = None
        self.draw()
        # Ten local preview refreshes/s; reuse the existing small stream image.
        self.job = self.window.after(100, self.refresh)

    def draw(self, force=False):
        if self.closed:
            return
        x, y, width, height = self.geometry()
        key = (self.frame, self.draft, self.aspect.get(), round(width), round(height))
        if not force and key == self.last_render:
            return
        self.last_render = key
        self.canvas.delete("all")
        self.photos = []
        for eye in (0, 1):
            left, top, right, bottom = self.bounds(eye)
            ew, eh = max(1, round(width / 2)), max(1, round(height))
            picture = Image.new("RGB", (ew, eh), "#050910")
            target_width, target_height = max(1, round(right - left)), max(1, round(bottom - top))
            if self.image is not None:
                patch = self.image.resize((target_width, target_height), Image.Resampling.BILINEAR)
            else:
                patch = Image.new("RGB", (target_width, target_height), "#142136")
                for fraction in (.25, .5, .75):
                    gx, gy = round(target_width * fraction), round(target_height * fraction)
                    patch.paste("#29435c", (gx, 0, gx + 1, target_height))
                    patch.paste("#29435c", (0, gy, target_width, gy + 1))
            picture.paste(patch, (round(left - x - eye * width / 2), round(top - y)))
            photo = ImageTk.PhotoImage(picture, master=self.window)
            self.photos.append(photo)
            self.canvas.create_image(x + eye * width / 2, y, image=photo, anchor="nw")
            self.canvas.create_rectangle(left, top, right, bottom, outline="#52e3bc", width=2)
            for px, py in ((left, top), (right, top), (left, bottom), (right, bottom)):
                self.canvas.create_rectangle(px - 7, py - 7, px + 7, py + 7,
                                             fill="#52e3bc", outline="#e7f0fc", width=2)
            self.canvas.create_text(x + (eye + .5) * width / 2, y + height + 12,
                                    text=self.owner.tr("Left eye" if eye == 0 else "Right eye"),
                                    fill="#94a8c4")
        self.canvas.create_line(x + width / 2, y, x + width / 2, y + height, fill="#94a8c4")
        self.values.configure(text=f"{self.draft.scale:.0%}  ·  X {self.draft.offsetX:+.3f}  ·  Y {self.draft.offsetY:+.3f}")

    def begin(self, event):
        x, y, width, height = self.geometry()
        if not (x <= event.x <= x + width and y <= event.y <= y + height):
            return
        eye = 0 if event.x < x + width / 2 else 1
        image_aspect = self.image.width / self.image.height if self.image is not None else 16 / 9
        left, top, right, bottom = self.bounds(eye)
        for px, py, sx, sy in ((left, top, -1, 1), (right, top, 1, 1),
                                (left, bottom, -1, -1), (right, bottom, 1, -1)):
            if math.hypot(event.x - px, event.y - py) <= 22:
                self.gesture = (self.draft, "resize", event.x, event.y, (sx, sy), width, height, image_aspect)
                return
        if left <= event.x <= right and top <= event.y <= bottom:
            self.gesture = (self.draft, "pan", event.x, event.y, (1, 1), width, height, image_aspect)

    def move(self, event):
        if self.gesture is None:
            return
        entry, kind, x, y, signs, width, height, image_aspect = self.gesture
        horizontal_direction = -1 if kind == "pan" else 1
        self.transaction.preview(kind, horizontal_direction * (event.x - x) * 4 / width,
                                 -(event.y - y) * 2 / height, image_aspect,
                                 width / 2 / height, corner_signs=signs,
                                 gesture_start=entry)
        self.draw(force=True)

    def end(self):
        self.gesture = None

    def save(self):
        if self.closed:
            return
        draft = self.transaction.commit()
        self._close()
        self.owner.commit_editor(draft)

    def discard(self):
        if not self.closed:
            self.transaction.discard()
            self._close()

    def _close(self):
        self.closed = True
        if self.job is not None:
            self.window.after_cancel(self.job)
        self.window.grab_release()
        self.window.destroy()
        self.owner.editor = None
