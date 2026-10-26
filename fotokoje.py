#!/usr/bin/env python3
"""Foto Koje - schlanker Bildeditor mit RAW- und CRAW-Unterstützung (CR2/CR3/NEF/ARW/DNG ...)."""
import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageTk

try:
    import rawpy  # LibRaw: liest u. a. Canon CR3 inkl. C-RAW
except ImportError:
    rawpy = None

HERE = os.path.dirname(os.path.abspath(__file__))
RAW_EXT = {".cr2", ".cr3", ".crw", ".nef", ".nrw", ".arw", ".srf", ".sr2", ".dng", ".orf",
           ".rw2", ".raf", ".pef", ".srw", ".3fr", ".erf", ".kdc", ".mrw"}
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".gif"}
FORMAT_BY_EXT = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".webp": "WEBP",
                 ".bmp": "BMP", ".tif": "TIFF", ".tiff": "TIFF", ".gif": "GIF"}
SAVE_TYPES = [("PNG", "*.png"), ("JPEG", "*.jpg"), ("WebP", "*.webp"), ("TIFF", "*.tiff"), ("BMP", "*.bmp")]
SLIDERS = [("exposure", "Belichtung (EV)", -3, 3, 0.1), ("brightness", "Helligkeit", -100, 100, 1),
           ("contrast", "Kontrast", -100, 100, 1), ("saturation", "Sättigung", -100, 100, 1),
           ("sharpness", "Schärfe", -100, 300, 1), ("warmth", "Farbtemperatur", -100, 100, 1),
           ("blur", "Weichzeichner", 0, 10, 0.1)]
BG, PANEL, FG, ACCENT = "#16161d", "#1f1f2b", "#e8e8f0", "#ff9f1c"


def adjust(img, p, blur_scale=1.0):
    """Wendet alle Regler auf ein Bild an (Vorschau und Export nutzen dieselbe Funktion)."""
    alpha = None
    if img.mode == "RGBA":
        alpha, img = img.getchannel("A"), img.convert("RGB")
    if p["exposure"]:
        f = 2 ** p["exposure"]
        img = img.point([min(255, int(i * f)) for i in range(256)] * 3)
    if p["warmth"]:
        k = p["warmth"] / 100 * 0.3
        r, g, b = img.split()
        r = r.point(lambda v: min(255, int(v * (1 + k))))
        b = b.point(lambda v: min(255, int(v * (1 - k))))
        img = Image.merge("RGB", (r, g, b))
    for key, cls in (("brightness", ImageEnhance.Brightness), ("contrast", ImageEnhance.Contrast),
                     ("saturation", ImageEnhance.Color), ("sharpness", ImageEnhance.Sharpness)):
        if p[key]:
            img = cls(img).enhance(1 + p[key] / 100)
    if p["blur"]:
        img = img.filter(ImageFilter.GaussianBlur(p["blur"] * blur_scale))
    if alpha is not None:
        img.putalpha(alpha)
    return img


def on_rgb(img, fn):
    if img.mode == "RGBA":
        a = img.getchannel("A")
        out = fn(img.convert("RGB")).convert("RGB")
        out.putalpha(a)
        return out
    return fn(img)


def load_image(path, half=False):
    ext = os.path.splitext(path)[1].lower()
    if ext in RAW_EXT:
        if rawpy is None:
            raise RuntimeError("Für RAW wird 'rawpy' benötigt:  pip install rawpy")
        with rawpy.imread(path) as raw:
            rgb = raw.postprocess(use_camera_wb=True, half_size=half, output_bps=8)
        return Image.fromarray(rgb), True
    img = ImageOps.exif_transpose(Image.open(path))
    img.load()
    img = img.convert("RGBA" if ("transparency" in img.info or "A" in img.mode) else "RGB")
    return img, False


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Foto Koje")
        self.geometry("1280x800")
        self.configure(bg=BG)
        self.base = self.prev = None
        self.pf = 1.0
        self.src_path, self.is_raw = None, False
        self.history, self.hpos = [], -1
        self.params = {k: 0 for k, *_ in SLIDERS}
        self.scales = {}
        self.tkimg, self.ds, self.off = None, 1.0, (0, 0)
        self.crop_mode, self.sel, self.start = False, None, None
        self.half = tk.BooleanVar(value=False)
        self._job = None
        self._style()
        self._icon()
        self._menu()
        self._ui()
        self._keys()

    # ---------- Aufbau ----------
    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TFrame", background=PANEL)
        s.configure("TLabel", background=PANEL, foreground=FG)
        s.configure("TButton", background="#2d2d3d", foreground=FG, borderwidth=0, padding=6)
        s.map("TButton", background=[("active", ACCENT)], foreground=[("active", "#111")])
        s.configure("Accent.TButton", background=ACCENT, foreground="#111")
        s.configure("Status.TLabel", background=BG, foreground="#9a9ab0")

    def _icon(self):
        try:
            self._ico = ImageTk.PhotoImage(Image.open(os.path.join(HERE, "icon.png")))
            self.iconphoto(True, self._ico)
            if os.name == "nt":
                self.iconbitmap(os.path.join(HERE, "icon.ico"))
        except Exception:
            pass

    def _menu(self):
        m = tk.Menu(self)
        f = tk.Menu(m, tearoff=0)
        f.add_command(label="Öffnen…", accelerator="Strg+O", command=self.open_file)
        f.add_command(label="Speichern unter… (PNG/JPG/…)", accelerator="Strg+S", command=self.save_as)
        f.add_command(label="Im Originalformat speichern…", accelerator="Strg+Umschalt+S", command=self.save_original)
        f.add_separator()
        f.add_checkbutton(label="RAW schnell laden (halbe Auflösung)", variable=self.half)
        f.add_separator()
        f.add_command(label="Beenden", command=self.destroy)
        e = tk.Menu(m, tearoff=0)
        e.add_command(label="Rückgängig", accelerator="Strg+Z", command=self.undo)
        e.add_command(label="Wiederholen", accelerator="Strg+Y", command=self.redo)
        m.add_cascade(label="Datei", menu=f)
        m.add_cascade(label="Bearbeiten", menu=e)
        self.config(menu=m)

    def _ui(self):
        panel = ttk.Frame(self, width=300)
        panel.pack(side="right", fill="y")
        panel.pack_propagate(False)
        self.canvas = tk.Canvas(self, bg="#0e0e13", highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.status = ttk.Label(self, text="Datei → Öffnen (Strg+O)", style="Status.TLabel")
        self.status.pack(side="bottom", fill="x", before=self.canvas)
        for key, label, lo, hi, res in SLIDERS:
            ttk.Label(panel, text=label).pack(anchor="w", padx=12, pady=(8, 0))
            sc = tk.Scale(panel, from_=lo, to=hi, resolution=res, orient="horizontal", bg=PANEL, fg=FG,
                          troughcolor="#2d2d3d", highlightthickness=0, activebackground=ACCENT,
                          command=lambda v, k=key: self.on_slide(k, v))
            sc.pack(fill="x", padx=12)
            self.scales[key] = sc
        row = ttk.Frame(panel)
        row.pack(fill="x", padx=12, pady=10)
        ttk.Button(row, text="Anwenden", style="Accent.TButton", command=self.apply_sliders).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ttk.Button(row, text="Reset", command=self.reset_sliders).pack(side="left", expand=True, fill="x")
        grid = ttk.Frame(panel)
        grid.pack(fill="x", padx=12)
        tools = [("⟲ 90°", lambda: self.geo(lambda i: i.transpose(Image.Transpose.ROTATE_90))),
                 ("⟳ 90°", lambda: self.geo(lambda i: i.transpose(Image.Transpose.ROTATE_270))),
                 ("↔ Spiegeln", lambda: self.geo(ImageOps.mirror)),
                 ("↕ Kippen", lambda: self.geo(ImageOps.flip)),
                 ("✂ Zuschneiden", self.crop_btn), ("⤢ Größe", self.resize),
                 ("S/W", lambda: self.geo(lambda i: on_rgb(i, lambda x: ImageOps.grayscale(x).convert("RGB")))),
                 ("Invertieren", lambda: self.geo(lambda i: on_rgb(i, ImageOps.invert))),
                 ("Auto-Kontrast", lambda: self.geo(lambda i: on_rgb(i, ImageOps.autocontrast))),
                 ("↶ Zurück", self.undo)]
        for n, (t, c) in enumerate(tools):
            ttk.Button(grid, text=t, command=c).grid(row=n // 2, column=n % 2, sticky="ew", padx=2, pady=2)
        grid.columnconfigure((0, 1), weight=1)
        c = self.canvas
        c.bind("<Configure>", lambda e: self.schedule())
        c.bind("<ButtonPress-1>", self.m_down)
        c.bind("<B1-Motion>", self.m_drag)
        c.bind("<ButtonRelease-1>", self.m_up)

    def _keys(self):
        self.bind("<Control-o>", lambda e: self.open_file())
        self.bind("<Control-s>", lambda e: self.save_as())
        self.bind("<Control-S>", lambda e: self.save_original())
        self.bind("<Control-z>", lambda e: self.undo())
        self.bind("<Control-y>", lambda e: self.redo())
        self.bind("<Return>", lambda e: self.crop_mode and self.crop_btn())
        self.bind("<Escape>", lambda e: self.cancel_crop())

    # ---------- Laden / Historie ----------
    def open_file(self):
        pats = tuple(sorted({"*" + e for e in IMG_EXT | RAW_EXT} | {"*" + e.upper() for e in IMG_EXT | RAW_EXT}))
        path = filedialog.askopenfilename(title="Bild oder RAW öffnen",
                                          filetypes=[("Bilder & RAW", pats), ("Alle Dateien", "*.*")])
        if not path:
            return
        self.config(cursor="watch")
        self.status.config(text="Lade …")
        self.update_idletasks()
        try:
            img, raw = load_image(path, self.half.get())
        except Exception as e:
            messagebox.showerror("Fehler beim Öffnen", str(e))
            return
        finally:
            self.config(cursor="")
        self.src_path, self.is_raw = path, raw
        self.history, self.hpos = [img], 0
        self.reset_sliders(render=False)
        self.set_base(img)
        self.title(f"Foto Koje – {os.path.basename(path)}")

    def set_base(self, img):
        self.base = img
        f = min(1.0, 1600 / max(img.size))
        self.pf = f
        self.prev = img if f == 1 else img.resize((max(1, int(img.width * f)), max(1, int(img.height * f))),
                                                  Image.LANCZOS, reducing_gap=3.0)
        self.sel = None
        self.render()

    def push(self, img):
        del self.history[self.hpos + 1:]
        self.history = (self.history + [img])[-12:]
        self.hpos = len(self.history) - 1
        self.set_base(img)

    def undo(self):
        if self.hpos > 0:
            self.hpos -= 1
            self.set_base(self.history[self.hpos])

    def redo(self):
        if self.hpos < len(self.history) - 1:
            self.hpos += 1
            self.set_base(self.history[self.hpos])

    # ---------- Vorschau ----------
    def on_slide(self, key, value):
        self.params[key] = float(value)
        self.schedule()

    def schedule(self):
        if self._job is None:
            self._job = self.after(40, self.render)

    def render(self):
        self._job = None
        if self.prev is None:
            return
        img = adjust(self.prev, self.params, self.pf)
        cw, ch = max(self.canvas.winfo_width(), 50), max(self.canvas.winfo_height(), 50)
        s = min(cw / img.width, ch / img.height)
        w, h = max(1, int(img.width * s)), max(1, int(img.height * s))
        self.tkimg = ImageTk.PhotoImage(img.resize((w, h), Image.BILINEAR))
        self.off = ((cw - w) // 2, (ch - h) // 2)
        self.ds = w / self.base.width
        self.canvas.delete("all")
        self.canvas.create_image(*self.off, anchor="nw", image=self.tkimg)
        if self.sel:
            self.canvas.create_rectangle(*self.sel, outline=ACCENT, width=2, dash=(5, 3))
        self.status.config(text=f"{self.base.width} × {self.base.height} px   |   "
                                f"{'RAW' if self.is_raw else 'Bild'}: {os.path.basename(self.src_path or '')}")

    def apply_sliders(self):
        if self.base is not None:
            self.push(adjust(self.base, self.params))
            self.reset_sliders()

    def reset_sliders(self, render=True):
        for k, sc in self.scales.items():
            self.params[k] = 0
            sc.set(0)
        if render:
            self.schedule()

    # ---------- Werkzeuge ----------
    def geo(self, fn):
        if self.base is not None:
            self.push(fn(self.base))

    def resize(self):
        if self.base is None:
            return
        w = simpledialog.askinteger("Größe ändern", f"Neue Breite in Pixel (aktuell {self.base.width}):",
                                    minvalue=1, maxvalue=30000, parent=self)
        if w:
            h = max(1, round(self.base.height * w / self.base.width))
            self.push(self.base.resize((w, h), Image.LANCZOS))

    def crop_btn(self):
        if self.base is None:
            return
        if not self.crop_mode:
            self.crop_mode, self.sel = True, None
            self.canvas.config(cursor="crosshair")
            self.status.config(text="Rahmen aufziehen, dann erneut ‚Zuschneiden‘ oder Enter (Esc = Abbruch)")
            return
        if self.sel:
            x0, y0, x1, y1 = self.sel
            ox, oy = self.off
            box = [int((x0 - ox) / self.ds), int((y0 - oy) / self.ds), int((x1 - ox) / self.ds), int((y1 - oy) / self.ds)]
            box = [max(0, box[0]), max(0, box[1]), min(self.base.width, box[2]), min(self.base.height, box[3])]
            if box[2] - box[0] > 1 and box[3] - box[1] > 1:
                self.cancel_crop()
                self.push(self.base.crop(box))
                return
        self.cancel_crop()

    def cancel_crop(self):
        self.crop_mode, self.sel = False, None
        self.canvas.config(cursor="")
        self.render()

    def m_down(self, e):
        if self.crop_mode:
            self.start, self.sel = (e.x, e.y), None
            self.canvas.delete("sel")

    def m_drag(self, e):
        if self.crop_mode and self.start:
            self.canvas.delete("sel")
            self.canvas.create_rectangle(*self.start, e.x, e.y, outline=ACCENT, width=2, dash=(5, 3), tags="sel")

    def m_up(self, e):
        if self.crop_mode and self.start:
            x0, y0 = self.start
            self.sel = (min(x0, e.x), min(y0, e.y), max(x0, e.x), max(y0, e.y))
            self.start = None

    # ---------- Speichern ----------
    def final(self):
        return adjust(self.base, self.params)

    def _stem(self):
        return os.path.splitext(os.path.basename(self.src_path))[0]

    def save_as(self):
        if self.base is None:
            return
        path = filedialog.asksaveasfilename(title="Speichern unter", initialfile=self._stem() + "_bearbeitet",
                                            defaultextension=".png", filetypes=SAVE_TYPES)
        if path:
            self.write(path)

    def save_original(self):
        if self.base is None:
            return
        ext = os.path.splitext(self.src_path)[1].lower()
        if self.is_raw:
            if messagebox.askyesno("RAW-Datei", "Bearbeitete Pixel lassen sich nicht in eine RAW-Datei zurückschreiben.\n\n"
                                   "Ja = unveränderte Original-RAW-Datei kopieren\n"
                                   "Nein = bearbeitetes Bild verlustfrei als TIFF speichern"):
                dest = filedialog.asksaveasfilename(initialfile=os.path.basename(self.src_path), defaultextension=ext)
                if dest:
                    shutil.copy2(self.src_path, dest)
                    self.status.config(text=f"RAW kopiert: {dest}")
            else:
                dest = filedialog.asksaveasfilename(initialfile=self._stem() + "_bearbeitet.tiff",
                                                    defaultextension=".tiff", filetypes=[("TIFF", "*.tiff")])
                if dest:
                    self.write(dest)
            return
        dest = filedialog.asksaveasfilename(initialfile=os.path.basename(self.src_path), defaultextension=ext,
                                            filetypes=[(ext[1:].upper(), "*" + ext)])
        if dest:
            self.write(dest)

    def write(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext not in FORMAT_BY_EXT:
            path, ext = path + ".png", ".png"
        fmt, kw = FORMAT_BY_EXT[ext], {}
        try:
            img = self.final()
            if fmt in ("JPEG", "BMP", "GIF"):
                img = img.convert("RGB")
            if fmt == "JPEG":
                kw = dict(quality=95, subsampling=0)
            elif fmt == "WEBP":
                kw = dict(quality=95)
            img.save(path, fmt, **kw)
        except Exception as e:
            messagebox.showerror("Fehler beim Speichern", str(e))
        else:
            self.status.config(text=f"Gespeichert: {path}")


if __name__ == "__main__":
    App().mainloop()
