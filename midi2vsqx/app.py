"""MIDI -> VSQX lyric tool — a small desktop app (CustomTkinter UI).

Workflow: in FL Studio, export your melody as a MIDI file. Open it here, type one
syllable per note (Enter jumps to the next note), then Export VSQX and import that
into Piapro Studio (File > Import > VSQX). You can also re-lyric a tuned .vsqx.

Run:  python app.py      (needs Python 3.9+ and `pip install -r requirements.txt`)
"""
from __future__ import annotations

import copy
import json
import os
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import customtkinter as ctk

from midi_reader import read_midi, midi_note_name, Song, Note, VSQ_RESOLUTION
from vsqx_writer import write_vsqx, ticks_per_measure
from vsqx_reader import (read_clips, moras_of, relyric_clip, read_vsqx,
                         is_continuation, unmapped_moras, split_kana_moras)

try:
    import mido                       # MIDI playback (needs the python-rtmidi backend)
except Exception:                      # noqa: BLE001 - app still runs without playback
    mido = None

# A few General-MIDI instruments to choose from (name -> program number).
GM_INSTRUMENTS = [
    ("Grand Piano", 0), ("Electric Piano", 4), ("Music Box", 10), ("Vibraphone", 11),
    ("Church Organ", 19), ("Nylon Guitar", 24), ("Strings", 48), ("Choir Aahs", 52),
    ("Synth Voice", 54), ("Trumpet", 56), ("Flute", 73), ("Square Lead", 80),
    ("Saw Lead", 81), ("Warm Pad", 89),
]

# --- Ninomae Ina'nis colour scheme ------------------------------------------
# Branding palette (#000000 / #575068 / #f29a30 / #e1d8ef) + official purples
# (#62567E, #9575E2), with a few derived dark plums for a modern "glass" look.
INK = "#000000"        # piano-roll base
ABYSS = "#1b1822"      # table / input background
PLUM = "#575068"       # mid plum
PURPLE = "#62567E"     # secondary buttons, gridlines
LILAC = "#9575E2"      # continuation notes, hover
ORANGE = "#f29a30"     # primary accent
PAPER = "#e1d8ef"      # text
GLOW = "#ffce8a"       # lighter orange (hover)
BG_WIN = "#15121c"     # window background (deep)
BG_CARD = "#221d2e"    # rounded cards / panels
BG_INPUT = "#2d2740"   # dropdowns / inputs
NIGHT = "#241f30"      # top of the piano-roll gradient
EMBER = "#3a2f2a"      # warm tint at the right of the header gradient
EMPTY_BG = "#2a2030"   # row tint for a note still missing a lyric
ROW_ALT = "#1f1b29"    # zebra-stripe row (alternates with ABYSS)
# Extra shades of purple (all in Ina's family) for the geometric decoration.
PLUM_DK = "#463d63"    # deep muted violet
VIOLET = "#6e5ca6"     # mid violet (between PURPLE and LILAC)
VIOLET_HI = "#8064c8"  # vivid violet
LILAC_HI = "#c4b0f5"   # light lilac (highlights / "all lyrics filled")
DONE = LILAC_HI        # "all lyrics filled" tint (kept on-palette, not green)
# decorative accent cycle for the banner's low-poly field + chevron rule:
# a dark → bright ramp of purples, so the header stays mainly purple.
GEO_ACCENTS = (PLUM_DK, PURPLE, VIOLET, VIOLET_HI, LILAC, LILAC_HI)

# Selectable UI font families (display name -> family). Tk falls back if missing.
FONT_THEMES = {
    "Segoe UI · clean": "Segoe UI",
    "Bahnschrift · tech": "Bahnschrift",
    "Consolas · mono": "Consolas",
    "Verdana · rounded": "Verdana",
    "Yu Gothic · modern": "Yu Gothic UI",
}

ctk.set_appearance_mode("dark")


def _lerp(c1, c2, t):
    """Blend two #rrggbb hex colours; t clamped to [0, 1]."""
    t = max(0.0, min(1.0, t))
    a = (int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16))
    b = (int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16))
    return "#%02x%02x%02x" % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _clamp01(x):
    return max(0.0, min(1.0, x))


def _ease(t):
    """Ease-out cubic — fast then gentle, for smooth slide-ins."""
    t = _clamp01(t)
    return 1 - (1 - t) ** 3


class App(ctk.CTk):
    _PPT = 0.06       # default piano-roll zoom: pixels per tick (~115 px per 4/4 bar)
    _PPT_MIN = 0.015  # horizontal zoom-out / zoom-in bounds
    _PPT_MAX = 0.40
    _VZOOM_MAX = 5.0  # vertical zoom-in bound (1.0 = fit all pitches in view)
    _GRID = 120       # note-edit time snap (1/16 note, in ticks)
    _DEFAULT_DUR = VSQ_RESOLUTION   # new note length when added (one beat = 480 ticks)
    _UNDO_MAX = 100   # how many edit steps we remember

    def __init__(self):
        super().__init__()
        self._settings = self._load_settings()      # remembered prefs (font/port/etc.)
        self.title("Made by M. Y.")
        self.geometry(self._settings.get("geometry") or "1200x820")
        self.minsize(960, 600)
        self.configure(fg_color=BG_WIN)

        self._intro_running = False     # opening animation state
        self._intro_p = 1.0             # progress 0→1 (1 = settled / no animation)
        try:
            self.attributes("-alpha", 0.0)   # stay hidden until the intro fades us in
        except tk.TclError:
            pass

        self.song = None        # Song (from a MIDI import, or moras of a tuned .vsqx)
        self.midi_path = None
        self.export_mode = "midi"   # "midi" = build new .vsqx; "relyric" = edit a tuned one
        self.vsqx_path = None       # the tuned source file, in re-lyric mode
        self.clip = None            # the chosen Clip (one vocal line) in re-lyric mode
        self.baseline_path = None   # optional un-tuned version, for exact syllable splits
        self.baseline_starts = None # its chosen clip's syllable start ticks
        self.draw_notes = []        # raw notes drawn in the piano-roll
        self._note_items = []       # (canvas_id, note, is_lead) for highlight
        self._ppt = self._PPT       # current horizontal zoom (pixels per tick)
        self._vzoom = 1.0           # vertical zoom (1.0 = fit all pitches; >1 = taller + scroll)
        self._roll_t0 = 0           # tick at the left edge of the piano-roll
        self._pad = 16              # piano-roll inner padding
        self._row_h = 8.0           # piano-roll pixels per semitone (set when drawn)
        self._kmax = 84             # top pitch on the roll (set when drawn)
        self._drag = None           # active note drag {note, mode, item, ...}
        self._roll_redraw_job = None    # debounce handle for roll <Configure> redraws
        self._banner_redraw_job = None  # debounce handle for banner <Configure> redraws
        self._editor = None         # (Entry, row_iid) while editing a lyric cell
        self._undo = []             # snapshots of song.notes before each structural edit
        self._redo = []
        self._play_thread = None    # background MIDI playback thread
        self._stop = threading.Event()

        self._info_prefix = "No file loaded."   # file details; progress is appended live
        self.font_name = self._settings.get("font", "Verdana · rounded")
        if self.font_name not in FONT_THEMES:
            self.font_name = "Verdana · rounded"
        self.fonts = self._fonts_for(self.font_name)         # tuples for canvas + ttk
        fam = FONT_THEMES.get(self.font_name, "Segoe UI")
        self.cf_body = ctk.CTkFont(family=fam, size=13)
        self.cf_bold = ctk.CTkFont(family=fam, size=13, weight="bold")
        self.cf_title = ctk.CTkFont(family=fam, size=22, weight="bold")
        self.cf_mono = ctk.CTkFont(family="Consolas", size=12)
        self.cf_small = ctk.CTkFont(family=fam, size=11)

        self._build_ui()
        self._bind_keys()
        self._apply_saved_selections()
        self.after(20, self._start_intro)

    # ---- settings (remembered between runs) --------------------------------
    @staticmethod
    def _settings_path():
        env = os.environ.get("MADEBYMY_SETTINGS")        # tests point this elsewhere
        if env:
            return env
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "MadeByMY-LyricTool", "settings.json")

    def _load_settings(self) -> dict:
        try:
            with open(self._settings_path(), encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
        except Exception:  # noqa: BLE001 - missing/corrupt config -> defaults
            return {}

    def _apply_saved_selections(self):
        """Restore the last instrument + MIDI port once the menus exist."""
        inst = self._settings.get("instrument")
        if inst in dict(GM_INSTRUMENTS):
            self.sound_cb.set(inst)
        port = self._settings.get("port")
        if port and not port.startswith("(") and port in getattr(self, "_port_names", []):
            self.port_cb.set(port)

    def _save_settings(self):
        port = self.port_cb.get()
        self._settings.update({
            "font": self.font_name,
            "instrument": self.sound_cb.get(),
            "port": port if port and not port.startswith("(") else self._settings.get("port", ""),
            "geometry": self.geometry(),
        })
        try:
            path = self._settings_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(self._settings, fh, indent=2)
        except Exception:  # noqa: BLE001 - never let a save failure crash the app
            pass

    def _dir(self) -> str:
        """Folder the file dialogs open in (the last one used)."""
        return self._settings.get("last_dir", "")

    def _remember_dir(self, path):
        if path:
            self._settings["last_dir"] = os.path.dirname(path)

    # ---- fonts / theme -----------------------------------------------------
    @staticmethod
    def _fonts_for(name):
        fam = FONT_THEMES.get(name, "Segoe UI")
        return {"body": (fam, 11), "bold": (fam, 11, "bold"),
                "title": (fam, 18, "bold"), "sub": ("Consolas", 10), "small": (fam, 9)}

    def _style_tree(self):
        """Dark style for the one ttk widget we keep (the lyric table)."""
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview", background=ABYSS, fieldbackground=ABYSS, foreground=PAPER,
                        rowheight=30, borderwidth=0, font=self.fonts["body"])
        style.configure("Treeview.Heading", background=PURPLE, foreground=PAPER,
                        relief="flat", font=self.fonts["bold"])
        style.map("Treeview.Heading", background=[("active", PLUM)])
        style.map("Treeview", background=[("selected", ORANGE)], foreground=[("selected", INK)])

    def _set_font_theme(self, name):
        """Switch the whole UI font family live."""
        self.font_name = name
        self.fonts = self._fonts_for(name)
        fam = FONT_THEMES.get(name, "Segoe UI")
        for cf in (self.cf_body, self.cf_bold, self.cf_title, self.cf_small):
            cf.configure(family=fam)
        self._style_tree()
        self._draw_banner()
        self._draw_piano_roll()

    def _draw_banner(self):
        """Geometric hero header: a tessellated low-poly triangle field (dark on the
        left so the title pops, vivid accents to the right) + a chevron accent rule.

        Doubles as the opening animation: with `_intro_p` < 1 the triangle columns
        drop in (staggered left→right), the title slides in from the left, the
        subtitle fades up, and the chevron rule sweeps across."""
        c = getattr(self, "banner", None)
        if c is None:
            return
        c.delete("all")
        w, h = max(c.winfo_width(), 1), int(c.cget("height"))
        fam = self.fonts["body"][0]
        p = self._intro_p if self._intro_running else 1.0
        c.create_rectangle(0, 0, w, h, fill=BG_WIN, outline="")

        cols = 16                                     # low-poly triangle field
        cw = w / cols
        for i in range(cols):
            colp = _ease(_clamp01((p - (i / cols) * 0.45) / 0.55))   # staggered drop-in
            dy = -(1.0 - colp) * (h * 1.5)
            x0, x1 = i * cw, (i + 1) * cw
            t = i / (cols - 1)                        # 0 (left, dark) → 1 (right, vivid)
            depth = (0.10 + 0.55 * t) * colp
            a = _lerp(BG_WIN, GEO_ACCENTS[i % len(GEO_ACCENTS)], depth)
            b = _lerp(BG_WIN, GEO_ACCENTS[(i + 2) % len(GEO_ACCENTS)], depth * 0.7)
            c.create_polygon(x0, dy, x1, dy, x0, h + dy, fill=a, outline="")
            c.create_polygon(x1, dy, x1, h + dy, x0, h + dy, fill=b, outline="")

        tp = _ease(_clamp01((p - 0.12) / 0.6))        # title slides in from the left
        tx = 24 - (1.0 - tp) * 380
        tcol = _lerp(BG_WIN, ORANGE, _clamp01((p - 0.12) / 0.45))
        c.create_text(tx, h * 0.40, anchor="w", text="MADE BY M. Y.",
                      fill=tcol, font=(fam, 26, "bold"))
        sp = _clamp01((p - 0.45) / 0.5)               # subtitle fades + slides slightly later
        sx = 26 - (1.0 - _ease(sp)) * 140
        c.create_text(sx, h * 0.74, anchor="w", fill=_lerp(BG_WIN, PAPER, sp), font=(fam, 12),
                      text="midi → vsqx   ·   re-lyric   ·   keep your tuning")

        n = 30                                        # chevron accent rule sweeps in L→R
        cwn = w / n
        reveal = _ease(p) * (n + 4)
        for i in range(n):
            if i > reveal:
                break
            x0, xm, x1 = i * cwn, (i + 0.5) * cwn, (i + 1) * cwn
            c.create_polygon(x0, h, xm, h - 8, x1, h,
                             fill=GEO_ACCENTS[i % len(GEO_ACCENTS)], outline="")

    # ---- opening animation -------------------------------------------------
    _INTRO_DUR = 1.0       # seconds

    def _start_intro(self):
        """Kick off the opening animation (header assembles + window fades up)."""
        self._intro_running = True
        self._intro_p = 0.0
        self._intro_t0 = time.perf_counter()
        self.after(1800, self._finish_intro)      # safety net: never stay hidden
        self._intro_tick()

    def _intro_tick(self):
        if not self._intro_running:
            return
        p = min(1.0, (time.perf_counter() - self._intro_t0) / self._INTRO_DUR)
        self._intro_p = p
        try:
            self.attributes("-alpha", _clamp01(0.12 + p * 1.3))   # fade the window up
        except tk.TclError:
            pass
        self._draw_banner()
        if p < 1.0:
            self.after(16, self._intro_tick)       # ~60 fps
        else:
            self._finish_intro()

    def _finish_intro(self):
        if not self._intro_running:
            return
        self._intro_running = False
        self._intro_p = 1.0
        try:
            self.attributes("-alpha", 1.0)
        except tk.TclError:
            pass
        self._draw_banner()

    # ---- UI construction ---------------------------------------------------
    def _btn(self, master, text, cmd, kind="secondary", **kw):
        styles = {
            "primary": dict(fg_color=ORANGE, hover_color=GLOW, text_color=INK),
            "secondary": dict(fg_color=PURPLE, hover_color=LILAC, text_color=PAPER),
            "ghost": dict(fg_color="transparent", hover_color=BG_INPUT, text_color=LILAC),
        }[kind]
        return ctk.CTkButton(master, text=text, command=cmd, corner_radius=10, height=34,
                             font=self.cf_bold, **styles, **kw)

    def _menu(self, master, values, width, command=None):
        return ctk.CTkOptionMenu(master, values=values, command=command, width=width, height=34,
                                 corner_radius=10, font=self.cf_body, fg_color=BG_INPUT,
                                 button_color=PURPLE, button_hover_color=LILAC, text_color=PAPER,
                                 dropdown_fg_color=BG_CARD, dropdown_hover_color=PURPLE,
                                 dropdown_text_color=PAPER, dropdown_font=self.cf_body)

    def _build_ui(self):
        # gradient banner (decorative header)
        self.banner = tk.Canvas(self, height=80, bg=BG_WIN, highlightthickness=0)
        self.banner.pack(side="top", fill="x")
        self.banner.bind("<Configure>", lambda e: self._schedule_banner_redraw())

        # toolbar card — file actions + font / help
        bar = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=14)
        bar.pack(side="top", fill="x", padx=12, pady=(12, 6))
        left = ctk.CTkFrame(bar, fg_color="transparent")
        left.pack(side="left", padx=8, pady=8)
        for text, cmd in (("Open MIDI (Ctrl+O)", self.open_midi),
                          ("Import VSQx (Ctrl+R)", self.open_tuned_vsqx),
                          ("Import Untuned Reference VSQx", self.open_baseline),
                          ("Batch lyrics", self.batch_lyrics)):
            self._btn(left, text, cmd).pack(side="left", padx=4)
        self._btn(left, "Export VSQX (Ctrl+S)", self.export_vsqx, kind="primary").pack(side="left", padx=4)
        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.pack(side="right", padx=8, pady=8)
        self._btn(right, "?  Help", self._show_help, kind="ghost", width=72).pack(side="right", padx=4)
        self.font_cb = self._menu(right, list(FONT_THEMES), 160, command=self._set_font_theme)
        self.font_cb.set(self.font_name)
        self.font_cb.pack(side="right", padx=4)
        ctk.CTkLabel(right, text="Font", font=self.cf_body, text_color=LILAC).pack(side="right", padx=(4, 2))

        # playback card
        play = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=14)
        play.pack(side="top", fill="x", padx=12, pady=6)
        pin = ctk.CTkFrame(play, fg_color="transparent")
        pin.pack(fill="x", padx=8, pady=8)
        self.play_btn = self._btn(pin, "▶  Play", self.toggle_play, kind="primary", width=96)
        self.play_btn.pack(side="left", padx=(0, 12))
        ctk.CTkLabel(pin, text="Out", font=self.cf_body, text_color=LILAC).pack(side="left", padx=(0, 4))
        self.port_cb = self._menu(pin, ["—"], 250)
        self.port_cb.pack(side="left", padx=(0, 14))
        ctk.CTkLabel(pin, text="Sound", font=self.cf_body, text_color=LILAC).pack(side="left", padx=(0, 4))
        self.sound_cb = self._menu(pin, [n for n, _ in GM_INSTRUMENTS], 150)
        self.sound_cb.set("Grand Piano")
        self.sound_cb.pack(side="left", padx=(0, 14))
        self._btn(pin, "↻", self._refresh_ports, kind="ghost", width=36).pack(side="left")
        self.info = ctk.CTkLabel(pin, text="No file loaded.", font=self.cf_bold, text_color=ORANGE)
        self.info.pack(side="right", padx=8)
        self._refresh_ports()

        # piano-roll card (grows with the window; the visualizer is the centrepiece)
        rollcard = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=14)
        rollcard.pack(side="top", fill="both", expand=True, padx=12, pady=6)
        rollwrap = ctk.CTkFrame(rollcard, fg_color="transparent")
        rollwrap.pack(side="top", fill="both", expand=True, padx=10, pady=(10, 4))
        self.canvas = tk.Canvas(rollwrap, height=300, bg=INK, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.roll_vsb = ctk.CTkScrollbar(rollwrap, orientation="vertical", command=self.canvas.yview,
                                         button_color=PURPLE, button_hover_color=LILAC)
        self.canvas.configure(yscrollcommand=self.roll_vsb.set)   # vsb is packed on demand
        hsb = ctk.CTkScrollbar(rollcard, orientation="horizontal", command=self.canvas.xview,
                               button_color=PURPLE, button_hover_color=LILAC)
        self.canvas.configure(xscrollcommand=hsb.set)
        hsb.pack(side="top", fill="x", padx=10, pady=(0, 4))
        self.canvas.bind("<Configure>", lambda e: self._schedule_roll_redraw())
        self.canvas.bind("<Button-1>", self._roll_press)
        self.canvas.bind("<B1-Motion>", self._roll_drag)
        self.canvas.bind("<ButtonRelease-1>", self._roll_release)
        self.canvas.bind("<Double-Button-1>", self._roll_add)
        self.canvas.bind("<Control-MouseWheel>", self._roll_zoom_wheel)   # horizontal zoom
        self.canvas.bind("<Alt-MouseWheel>", self._roll_vzoom_wheel)      # vertical zoom (FL parity)
        self.canvas.bind("<MouseWheel>", self._roll_scroll_wheel)         # vertical scroll
        self.canvas.bind("<Shift-MouseWheel>", self._roll_hscroll_wheel)  # horizontal scroll

        # edit bar — undo/redo + transpose + a hint (MIDI mode only)
        edit = ctk.CTkFrame(rollcard, fg_color="transparent")
        edit.pack(side="top", fill="x", padx=10, pady=(0, 10))
        self.undo_btn = self._btn(edit, "↶ Undo", self.undo, kind="ghost", width=80)
        self.undo_btn.pack(side="left", padx=(0, 4))
        self.redo_btn = self._btn(edit, "↷ Redo", self.redo, kind="ghost", width=80)
        self.redo_btn.pack(side="left", padx=(0, 14))
        ctk.CTkLabel(edit, text="Transpose all", font=self.cf_body,
                     text_color=LILAC).pack(side="left", padx=(0, 6))
        self._transpose_btns = []
        for label, semis in (("−8va", -12), ("−1", -1), ("+1", 1), ("+8va", 12)):
            b = self._btn(edit, label, lambda s=semis: self.transpose(s), width=58)
            b.pack(side="left", padx=2)
            self._transpose_btns.append(b)
        self.edit_hint = ctk.CTkLabel(edit, text="", font=self.cf_small, text_color=PURPLE)
        self.edit_hint.pack(side="right", padx=(10, 4))
        # zoom controls (always active — view, not editing). Also Ctrl/Alt+wheel on the roll.
        # H = horizontal (time), V = vertical (pitch).
        self._btn(edit, "＋", lambda: self.zoom_roll_v(1.3), kind="ghost", width=30).pack(side="right", padx=1)
        self._btn(edit, "－", lambda: self.zoom_roll_v(1 / 1.3), kind="ghost", width=30).pack(side="right", padx=1)
        ctk.CTkLabel(edit, text="V", font=self.cf_bold, text_color=LILAC).pack(side="right", padx=(8, 2))
        self._btn(edit, "＋", lambda: self.zoom_roll(1.25), kind="ghost", width=30).pack(side="right", padx=1)
        self._btn(edit, "－", lambda: self.zoom_roll(1 / 1.25), kind="ghost", width=30).pack(side="right", padx=1)
        ctk.CTkLabel(edit, text="Zoom  H", font=self.cf_body, text_color=LILAC).pack(side="right", padx=(0, 2))

        # status (bottom) then the table fills the middle
        self.status = ctk.CTkLabel(self, text="› open a MIDI, or Import VSQx to re-lyric — "
                                   "press “?  Help” for a guide", font=self.cf_mono,
                                   text_color=LILAC, anchor="w")
        self.status.pack(side="bottom", fill="x", padx=18, pady=(2, 10))

        tablecard = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=14)
        tablecard.pack(side="top", fill="both", expand=True, padx=12, pady=6)
        self._style_tree()
        cols = ("idx", "bar", "pitch", "dur", "lyric")
        self.tree = ttk.Treeview(tablecard, columns=cols, show="headings", selectmode="browse")
        widths = {"idx": 48, "bar": 90, "pitch": 90, "dur": 100, "lyric": 520}
        heads = {"idx": "#", "bar": "Bar.Beat", "pitch": "Pitch", "dur": "Dur (ticks)", "lyric": "Lyric"}
        for c in cols:
            self.tree.heading(c, text=heads[c])
            self.tree.column(c, width=widths[c], anchor=("w" if c == "lyric" else "center"))
        self.tree.tag_configure("odd", background=ABYSS)
        self.tree.tag_configure("even", background=ROW_ALT)     # zebra striping
        self.tree.tag_configure("empty", background=EMPTY_BG, foreground=PLUM)
        vsb = ctk.CTkScrollbar(tablecard, command=self.tree.yview,
                               button_color=PURPLE, button_hover_color=LILAC)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        vsb.pack(side="right", fill="y", padx=(2, 10), pady=10)
        self.tree.bind("<Double-1>", lambda e: self._edit_selected())
        self.tree.bind("<Return>", lambda e: self._edit_selected())
        self.tree.bind("<Delete>", lambda e: self._delete_note())
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._highlight_selection())

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._draw_banner()
        self._draw_piano_roll()
        self._sync_edit_bar()

    def _bind_keys(self):
        self.bind("<Control-o>", lambda e: self.open_midi())
        self.bind("<Control-r>", lambda e: self.open_tuned_vsqx())
        self.bind("<Control-s>", lambda e: self.export_vsqx())
        self.bind("<Control-z>", lambda e: self.undo())
        self.bind("<Control-y>", lambda e: self.redo())
        self.bind("<Control-Shift-Z>", lambda e: self.redo())
        self.bind("<Shift-Up>", lambda e: self.transpose(1))
        self.bind("<Shift-Down>", lambda e: self.transpose(-1))
        self.bind("<Control-Up>", lambda e: self.transpose(12))
        self.bind("<Control-Down>", lambda e: self.transpose(-12))

    # ---- piano-roll visualizer --------------------------------------------
    def _lead_flags(self, notes):
        """Which notes start a syllable (drawn orange) vs. hold the previous one (lilac).
        In MIDI mode every note is its own syllable — only a tuned/re-lyric clip has the
        'ー'/bare-vowel continuation tails that the heuristic looks for."""
        if self.export_mode == "midi":
            return [True] * len(notes)
        flags, have = [], False
        for n in notes:
            flags.append(not (have and is_continuation(n.lyric)))
            have = True
        return flags

    def _schedule_roll_redraw(self):
        """Coalesce rapid <Configure> events (window resize) into a single redraw, so
        dragging the window edge doesn't fire a heavy full redraw on every pixel."""
        if self._roll_redraw_job is not None:
            self.after_cancel(self._roll_redraw_job)
        self._roll_redraw_job = self.after(33, self._do_roll_redraw)

    def _do_roll_redraw(self):
        self._roll_redraw_job = None
        self._draw_piano_roll()

    def _schedule_banner_redraw(self):
        if self._banner_redraw_job is not None:
            self.after_cancel(self._banner_redraw_job)
        self._banner_redraw_job = self.after(33, self._do_banner_redraw)

    def _do_banner_redraw(self):
        self._banner_redraw_job = None
        self._draw_banner()

    def _roll_view_h(self):
        """Current visible height of the roll canvas (falls back to its requested
        height before the window is laid out / in headless tests)."""
        h = self.canvas.winfo_height()
        return h if h > 20 else int(self.canvas.cget("height"))

    def _draw_piano_roll(self):
        c = self.canvas
        c.delete("all")
        self._note_items = []
        notes = self.draw_notes
        H, pad = self._roll_view_h(), self._pad
        W = max(c.winfo_width(), 1)
        if not notes:
            c.configure(scrollregion=(0, 0, W, H))
            self._sync_roll_vscroll(False)
            self._draw_roll_backdrop(c, W, H)
            self._draw_empty_roll(c, W, H)
            return
        keys = [n.key for n in notes]
        kmin, kmax = min(keys), max(keys)
        keyspan = kmax - kmin + 1
        fit = (H - 2 * pad) / keyspan if keyspan else (H - 2 * pad)
        base = min(max(fit, 5.0), 26.0)              # row height that fits all pitches in view
        row_h = base * self._vzoom                    # vertical zoom scales it up (then we scroll)
        t0 = min(n.start for n in notes)
        tpm = ticks_per_measure(self.song.numerator, self.song.denominator) if self.song else 1920
        t0 = (t0 // tpm) * tpm if tpm else t0
        end = max(n.start + n.dur for n in notes)
        width = int((end - t0) * self._ppt) + 2 * pad
        full = max(width, W)
        Hc = int(2 * pad + keyspan * row_h)           # full content height
        Hv = max(H, Hc)                               # scroll height
        self._roll_t0, self._row_h, self._kmax = t0, row_h, kmax
        c.configure(scrollregion=(0, 0, full, Hv))
        self._sync_roll_vscroll(Hc > H + 1)

        self._draw_roll_backdrop(c, full, Hv)

        def px(t):
            return pad + (t - t0) * self._ppt

        def py(k):
            return pad + (kmax - k) * row_h

        bar = t0
        while tpm and px(bar) <= width:
            c.create_line(px(bar), 0, px(bar), Hv, fill=PURPLE)
            bar += tpm

        show_labels = row_h >= 9                       # don't cram labels when rows are tiny
        for i, lead in enumerate(self._lead_flags(notes)):
            n = notes[i]
            x0, x1, y0 = px(n.start), px(n.start + n.dur), py(n.key)
            item = c.create_rectangle(x0, y0, max(x0 + 2, x1), y0 + row_h,
                                      fill=(ORANGE if lead else LILAC), outline=INK)
            self._note_items.append((item, n, lead))
            if lead and n.lyric and show_labels:
                c.create_text(x0 + 1, y0 - 1, anchor="sw", fill=PAPER,
                              font=self.fonts["small"], text=n.lyric)
        self._draw_legend(c)

    _FACET_SHADES = ("#0c0a12", "#161320", "#201b2e", "#2a2440")   # subtle dark-plum ramp

    def _draw_roll_backdrop(self, c, w, h):
        """Low-poly faceted backdrop: a tessellation of triangles in close dark-plum
        shades (texture, not noise) plus two faint accent facets in the corners. Kept
        deliberately low-contrast so the orange/lilac notes and labels stay legible."""
        c.create_rectangle(0, 0, w, h, fill=INK, outline="")
        cell = 160.0                                  # capped so a long/tall roll stays cheap
        cols = max(1, min(12, int(w // cell) + 1))
        rows = max(2, min(6, int(h // cell) + 1))
        cw, ch = w / cols, h / rows
        shades = self._FACET_SHADES
        for r in range(rows):
            for k in range(cols):
                x0, x1, y0, y1 = k * cw, (k + 1) * cw, r * ch, (r + 1) * ch
                c.create_polygon(x0, y0, x1, y0, x0, y1,
                                 fill=shades[(r + k) % len(shades)], outline="")
                c.create_polygon(x1, y0, x1, y1, x0, y1,
                                 fill=shades[(r + k + 1) % len(shades)], outline="")
        # faint accent facets in opposite corners (both in the purple family)
        c.create_polygon(0, 0, w * 0.16, 0, 0, h * 0.55,
                         fill=_lerp(INK, PURPLE, 0.22), outline="")
        c.create_polygon(w, h, w - min(260, w * 0.16), h, w, h * 0.45,
                         fill=_lerp(INK, LILAC, 0.16), outline="")

    def _draw_empty_roll(self, c, w, h):
        c.create_text(20, 18, anchor="nw", fill=LILAC, font=self.fonts["bold"], text="♪  piano-roll")
        c.create_text(20, 40, anchor="nw", fill=PURPLE, font=self.fonts["body"],
                      text="open a MIDI, or Import VSQx to re-lyric")

    def _draw_legend(self, c):
        lx = self._pad
        for color, label in ((ORANGE, "syllable"), (LILAC, "held note")):
            c.create_rectangle(lx, 2, lx + 11, 11, fill=color, outline=INK)
            t = c.create_text(lx + 15, 1, anchor="nw", fill=PAPER,
                              font=self.fonts["small"], text=label)
            lx = c.bbox(t)[2] + 12

    def _sync_roll_vscroll(self, show):
        """Show the roll's vertical scrollbar only when the notes overflow the view."""
        vsb = getattr(self, "roll_vsb", None)
        if vsb is None:
            return
        mapped = bool(vsb.winfo_ismapped())
        if show and not mapped:
            vsb.pack(side="right", fill="y")
        elif not show and mapped:
            vsb.pack_forget()

    def zoom_roll(self, factor):
        """Zoom the piano-roll horizontally, keeping the left-edge position stable.
        (Ctrl+wheel mirrors FL Studio's horizontal-zoom gesture — see the hotkeys tool.)"""
        new = max(self._PPT_MIN, min(self._PPT_MAX, self._ppt * factor))
        if abs(new - self._ppt) < 1e-9 or not self.draw_notes:
            return
        left_tick = self._roll_t0 + (self.canvas.canvasx(0) - self._pad) / self._ppt
        self._ppt = new
        self._draw_piano_roll()
        sr = self.canvas.cget("scrollregion").split()
        full = float(sr[2]) if len(sr) == 4 else 0.0
        if full > 0:
            x = self._pad + (left_tick - self._roll_t0) * self._ppt
            self.canvas.xview_moveto(max(0.0, min(1.0, x / full)))

    def _roll_zoom_wheel(self, e):
        self.zoom_roll(1.15 if e.delta > 0 else 1 / 1.15)
        return "break"

    def zoom_roll_v(self, factor):
        """Zoom the piano-roll vertically (taller notes + a scrollbar), keeping the pitch
        at the top of the view stable. (Alt+wheel mirrors FL Studio's vertical-zoom gesture.)"""
        new = max(1.0, min(self._VZOOM_MAX, self._vzoom * factor))
        if abs(new - self._vzoom) < 1e-9 or not self.draw_notes:
            return
        c = self.canvas
        top_key = self._kmax - (c.canvasy(0) - self._pad) / self._row_h if self._row_h else self._kmax
        self._vzoom = new
        self._draw_piano_roll()
        sr = c.cget("scrollregion").split()
        hv = float(sr[3]) if len(sr) == 4 else 0.0
        if hv > 0:
            y = self._pad + (self._kmax - top_key) * self._row_h
            c.yview_moveto(max(0.0, min(1.0, y / hv)))

    def _roll_vzoom_wheel(self, e):
        self.zoom_roll_v(1.15 if e.delta > 0 else 1 / 1.15)
        return "break"

    def _roll_scroll_wheel(self, e):
        self.canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")
        return "break"

    def _roll_hscroll_wheel(self, e):
        self.canvas.xview_scroll(-1 if e.delta > 0 else 1, "units")
        return "break"

    def _highlight_selection(self):
        sel = self.tree.selection()
        if not sel or not self.song or not self._note_items:
            return
        i = self.tree.get_children().index(sel[0])
        notes = self.song.notes
        t0 = notes[i].start
        t1 = notes[i + 1].start if i + 1 < len(notes) else 1 << 30
        for item, n, lead in self._note_items:
            inside = t0 <= n.start < t1
            self.canvas.itemconfigure(item, fill=(PAPER if inside else (ORANGE if lead else LILAC)))
        sr = self.canvas.cget("scrollregion").split()
        if len(sr) == 4 and float(sr[2]) > 0:
            self.canvas.xview_moveto(max(0.0, ((t0 - self._roll_t0) * self._ppt - 40) / float(sr[2])))

    # ---- undo / redo (structural note edits in MIDI mode) ------------------
    def _snapshot(self):
        """A copy of the current notes (Note fields are all immutable scalars)."""
        return [copy.copy(n) for n in self.song.notes] if self.song else []

    def _push_undo(self):
        """Call BEFORE a structural change so it can be undone."""
        if self.song is None:
            return
        self._undo.append(self._snapshot())
        del self._undo[:-self._UNDO_MAX]
        self._redo.clear()

    def _restore(self, notes):
        self.song.notes = notes
        self.draw_notes = self.song.notes
        self._populate()

    def undo(self):
        if not self._undo or self.song is None:
            return
        self._redo.append(self._snapshot())
        self._restore(self._undo.pop())
        self.status.configure(text="↶ undid an edit  ·  %d step(s) left" % len(self._undo))
        self._sync_edit_bar()

    def redo(self):
        if not self._redo or self.song is None:
            return
        self._undo.append(self._snapshot())
        self._restore(self._redo.pop())
        self.status.configure(text="↷ redid an edit  ·  %d step(s) left" % len(self._redo))
        self._sync_edit_bar()

    def _sync_edit_bar(self):
        """Enable/disable the edit-bar controls for the current mode + history."""
        midi = self._editable()
        self.undo_btn.configure(state=("normal" if self._undo else "disabled"))
        self.redo_btn.configure(state=("normal" if self._redo else "disabled"))
        for b in self._transpose_btns:
            b.configure(state=("normal" if midi else "disabled"))
        self.edit_hint.configure(
            text=("double-click to add · drag to move · drag right edge to resize · Delete to remove"
                  if midi else "re-lyric mode · tuning is locked"))

    # ---- note editing (MIDI mode only; re-lyric never alters tuning) -------
    def _editable(self):
        return self.export_mode == "midi" and bool(self.draw_notes)

    def _hit_note(self, cx, cy):
        for item, n, _lead in reversed(self._note_items):
            x0, y0, x1, y1 = self.canvas.coords(item)
            if x0 - 2 <= cx <= x1 + 2 and y0 - 2 <= cy <= y1 + 2:
                return n, ("resize" if (x1 - cx) <= 6 and (x1 - x0) > 12 else "move")
        return None

    def _select_note_row(self, n):
        """Select the table row for a note clicked on the roll. Works in both modes —
        clicking a tuning tail selects its syllable's row."""
        di = next((i for i, (_it, nn, _l) in enumerate(self._note_items) if nn is n), None)
        if di is None:
            return
        flags = self._lead_flags(self.draw_notes)
        row = sum(1 for f in flags[:di + 1] if f) - 1
        kids = self.tree.get_children()
        if 0 <= row < len(kids):
            self.tree.selection_set(kids[row])
            self.tree.focus(kids[row])
            self.tree.see(kids[row])

    def _roll_press(self, e):
        self._drag = None
        cx, cy = self.canvas.canvasx(e.x), self.canvas.canvasy(e.y)
        hit = self._hit_note(cx, cy)
        if not hit:
            return
        n, mode = hit
        self._select_note_row(n)                 # click-to-select in any mode
        if not self._editable():
            return
        item = next((it for it, nn, _l in self._note_items if nn is n), None)
        self._drag = {"note": n, "mode": mode, "item": item, "cx": cx, "cy": cy,
                      "start0": n.start, "key0": n.key, "dur0": n.dur,
                      "pre": self._snapshot()}

    def _roll_drag(self, e):
        d = self._drag
        if not d:
            return
        cx, cy = self.canvas.canvasx(e.x), self.canvas.canvasy(e.y)
        dtick = round((cx - d["cx"]) / self._ppt / self._GRID) * self._GRID
        n = d["note"]
        if d["mode"] == "resize":
            n.dur = max(self._GRID, d["dur0"] + dtick)
        else:
            n.start = max(0, d["start0"] + dtick)
            n.key = max(0, min(127, d["key0"] - int(round((cy - d["cy"]) / self._row_h))))
        # Move just the dragged rectangle (cheap) instead of redrawing the whole roll
        # every motion event; the full redraw happens once on release.
        if d.get("item") is not None:
            x0 = self._pad + (n.start - self._roll_t0) * self._ppt
            x1 = self._pad + (n.start + n.dur - self._roll_t0) * self._ppt
            y0 = self._pad + (self._kmax - n.key) * self._row_h
            self.canvas.coords(d["item"], x0, y0, max(x0 + 2, x1), y0 + self._row_h)
        else:
            self._draw_piano_roll()

    def _roll_release(self, _e):
        d = self._drag
        self._drag = None
        if not d:
            return
        n = d["note"]
        if (n.start, n.key, n.dur) != (d["start0"], d["key0"], d["dur0"]):
            self._undo.append(d["pre"])          # one undo step per effective drag
            del self._undo[:-self._UNDO_MAX]
            self._redo.clear()
        self._populate()
        self._sync_edit_bar()

    def _roll_add(self, e):
        """Double-click empty roll space to add a note there (MIDI mode)."""
        if not self._editable():
            return
        cx, cy = self.canvas.canvasx(e.x), self.canvas.canvasy(e.y)
        if self._hit_note(cx, cy):               # double-clicked a note -> ignore
            return
        tick = self._roll_t0 + round((cx - self._pad) / self._ppt / self._GRID) * self._GRID
        key = int(round(self._kmax - (cy - self._pad) / self._row_h))
        tick, key = max(0, tick), max(0, min(127, key))
        self._push_undo()
        new = Note(start=tick, dur=self._DEFAULT_DUR, key=key, velocity=96, lyric="")
        self.song.notes.append(new)
        self.song.notes.sort(key=lambda nn: (nn.start, nn.key))
        self.draw_notes = self.song.notes
        self._populate()
        i = self.song.notes.index(new)
        kids = self.tree.get_children()
        if i < len(kids):
            self.tree.selection_set(kids[i])
            self.tree.focus(kids[i])
            self.tree.see(kids[i])
        self.status.configure(text="Added %s. Drag to adjust, type a lyric, or Delete to remove."
                              % midi_note_name(key))
        self._sync_edit_bar()

    def transpose(self, semitones):
        """Shift every note by `semitones` (MIDI mode only; tuned files stay locked)."""
        if not self._editable() or not self.song.notes:
            return
        lo = min(n.key for n in self.song.notes) + semitones
        hi = max(n.key for n in self.song.notes) + semitones
        if lo < 0 or hi > 127:
            self.status.configure(text="Can't transpose — that would leave the MIDI range.")
            return
        self._push_undo()
        for n in self.song.notes:
            n.key += semitones
        self.draw_notes = self.song.notes
        self._populate()
        self.status.configure(text="Transposed all notes %+d semitone(s)." % semitones)
        self._sync_edit_bar()

    def _delete_note(self):
        if not self._editable():
            return
        sel = self.tree.selection()
        if not sel:
            return
        i = self.tree.get_children().index(sel[0])
        if 0 <= i < len(self.song.notes):
            self._push_undo()
            del self.song.notes[i]
            self.draw_notes = self.song.notes
            self._populate()
            self.status.configure(text="Deleted a note — %d left." % len(self.song.notes))
            self._sync_edit_bar()

    # ---- playback (built-in synth, or loopMIDI -> FL) ----------------------
    def _refresh_ports(self):
        names = []
        if mido is not None:
            try:
                names = mido.get_output_names()
            except Exception:  # noqa: BLE001
                names = []
        self._port_names = names
        if names:
            self.port_cb.configure(values=names, state="normal")
            if self.port_cb.get() not in names:
                self.port_cb.set(self._settings.get("port") if self._settings.get("port") in names
                                 else names[0])
            self.play_btn.configure(state="normal")
        else:
            self.port_cb.configure(values=["(no MIDI output — see Help)"], state="disabled")
            self.port_cb.set("(no MIDI output — see Help)")
            self.play_btn.configure(state="disabled")

    def toggle_play(self):
        if self._play_thread and self._play_thread.is_alive():
            self._stop.set()
            return
        if mido is None or not self.draw_notes:
            return
        port = self.port_cb.get()
        if not port or port.startswith("("):
            messagebox.showinfo("No MIDI output", "Pick a MIDI output first (e.g. "
                                "Microsoft GS Wavetable Synth, or a loopMIDI port for FL).")
            return
        program = dict(GM_INSTRUMENTS).get(self.sound_cb.get(), 0)
        bpm = self.song.bpm if self.song else 120.0
        notes = self._notes_to_play()
        if not notes:
            return
        self._stop.clear()
        self.play_btn.configure(text="■  Stop")
        self._play_thread = threading.Thread(
            target=self._play_worker, args=(notes, port, program, bpm), daemon=True)
        self._play_thread.start()

    def _notes_to_play(self):
        """All drawn notes, or — if a non-first row is selected — from that note onward,
        so Play acts like a playhead you can drop anywhere by clicking a row/note."""
        notes = list(self.draw_notes)
        if not notes:
            return notes
        sel = self.tree.selection()
        if sel and self.song:
            i = self.tree.get_children().index(sel[0])
            if 0 <= i < len(self.song.notes):
                start = self.song.notes[i].start
                if start > min(n.start for n in notes):
                    from_sel = [n for n in notes if n.start >= start]
                    if from_sel:
                        self.status.configure(text="› playing from syllable %d (click row 1 to "
                                              "play from the top)." % (i + 1))
                        return from_sel
        return notes

    def _play_worker(self, notes, port_name, program, bpm):
        spt = 60.0 / (bpm * VSQ_RESOLUTION)
        try:
            out = mido.open_output(port_name)
        except Exception as exc:  # noqa: BLE001
            self.after(0, lambda: messagebox.showerror("Playback failed", str(exc)))
            self.after(0, lambda: self.play_btn.configure(text="▶  Play"))
            return
        t0 = min(n.start for n in notes)
        events = []
        for n in notes:
            v = max(1, min(127, n.velocity))
            events.append((n.start - t0, 1, n.key, v))
            events.append((n.start + n.dur - t0, 0, n.key, 0))
        events.sort(key=lambda e: (e[0], e[1]))
        try:
            out.send(mido.Message("program_change", program=program))
            prev = 0
            for tick, on, key, vel in events:
                dt = (tick - prev) * spt
                if dt > 0 and self._stop.wait(dt):
                    break
                prev = tick
                out.send(mido.Message("note_on" if on else "note_off", note=key, velocity=vel))
        finally:
            try:
                out.send(mido.Message("control_change", control=123, value=0))
            except Exception:  # noqa: BLE001
                pass
            out.close()
            self.after(0, lambda: self.play_btn.configure(text="▶  Play"))

    def _on_close(self):
        self._save_settings()
        self._stop.set()
        self.destroy()

    # ---- dialogs -----------------------------------------------------------
    def _dialog(self, title, w, h):
        dlg = ctk.CTkToplevel(self)
        dlg.title(title)
        dlg.configure(fg_color=BG_WIN)
        dlg.geometry("%dx%d" % (w, h))
        dlg.transient(self)
        dlg.bind("<Escape>", lambda e: dlg.destroy())
        dlg.after(150, dlg.grab_set)        # grab once the window is viewable
        return dlg

    def batch_lyrics(self):
        if not self.song or not self.song.notes:
            messagebox.showinfo("Open a file first",
                                "Open a MIDI or a tuned VSQX, then paste lyrics here.")
            return
        n = len(self.song.notes)
        dlg = self._dialog("Batch lyrics", 500, 380)
        ctk.CTkLabel(dlg, text="Paste %d syllables — one per note, separated by spaces or new "
                     "lines." % n, font=self.cf_body, text_color=PAPER, justify="left",
                     wraplength=440).pack(anchor="w", padx=16, pady=(16, 6))
        txt = tk.Text(dlg, bg=ABYSS, fg=PAPER, insertbackground=ORANGE, relief="flat", wrap="word",
                      font=self.fonts["body"], highlightthickness=1, highlightbackground=PURPLE)
        txt.pack(fill="both", expand=True, padx=16)
        kana = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(dlg, text="Auto-split continuous kana  (きらきら → き ら き ら)",
                        variable=kana, font=self.cf_body, text_color=PAPER, fg_color=ORANGE,
                        hover_color=GLOW).pack(anchor="w", padx=16, pady=10)
        txt.focus_set()

        def apply():
            tokens = split_kana_moras(txt.get("1.0", "end")) if kana.get() else txt.get("1.0", "end").split()
            if not tokens:
                dlg.destroy()
                return
            if len(tokens) != n and not messagebox.askokcancel(
                    "Count differs", "You pasted %d syllables but there are %d notes.\n\n"
                    "Fill the first %d and leave the rest?" % (len(tokens), n, min(len(tokens), n)),
                    parent=dlg):
                return
            for i in range(min(len(tokens), n)):
                self.song.notes[i].lyric = tokens[i]
            self._populate()
            self.status.configure(text="› filled %d syllable(s) from batch input." % min(len(tokens), n))
            dlg.destroy()

        row = ctk.CTkFrame(dlg, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 16))
        self._btn(row, "Fill lyrics", apply, kind="primary").pack(side="right")
        self._btn(row, "Cancel", dlg.destroy).pack(side="right", padx=(0, 8))

    def _show_help(self):
        dlg = self._dialog("Made by M. Y. — Help", 740, 580)
        fam = self.fonts["body"][0]
        frame = ctk.CTkFrame(dlg, fg_color=BG_CARD, corner_radius=14)
        frame.pack(fill="both", expand=True, padx=12, pady=12)
        txt = tk.Text(frame, bg=BG_CARD, fg=PAPER, relief="flat", wrap="word", borderwidth=0,
                      font=self.fonts["body"], padx=22, pady=16, highlightthickness=0, spacing2=4)
        txt.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        sb = ctk.CTkScrollbar(frame, command=txt.yview, button_color=PURPLE, button_hover_color=LILAC)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y", padx=6, pady=6)
        txt.tag_configure("h", foreground=ORANGE, font=(fam, 14, "bold"), spacing1=20, spacing3=8)
        txt.tag_configure("b", foreground=GLOW, font=self.fonts["bold"], spacing1=10, spacing3=4)
        txt.tag_configure("p", foreground=PAPER, spacing3=14, lmargin1=12, lmargin2=12, rmargin=14)
        for kind, line in self._help_lines():
            txt.insert("end", line + "\n", kind or "p")
        txt.configure(state="disabled")

    @staticmethod
    def _help_lines():
        return [
            ("h", "What this tool does"),
            ("", "Put lyrics on a melody for Piapro Studio (VOCALOID) — either build a fresh "
                 ".vsqx from a MIDI, or re-word a tuned .vsqx while keeping all your tuning."),
            ("h", "1 · MIDI → VSQX  (write new lyrics)"),
            ("b", "Open MIDI  →  type one syllable per note  →  Export VSQX"),
            ("", "Export a melody from FL Studio as MIDI, open it, fill the Lyric column "
                 "(Enter = next note), then export. In Piapro: File ▸ Import ▸ VSQX."),
            ("h", "2 · Import a tuned VSQx  (re-lyric, keep the tuning)"),
            ("b", "Import VSQx  →  (pick a vocal line)  →  type new words  →  Export"),
            ("", "Open a .vsqx you already tuned in Piapro. Each row is one sung syllable "
                 "(the little tuning notes are grouped for you). Type the new word over each "
                 "syllable and export — every pitch and note-split you tuned is preserved. "
                 "After importing in Piapro, run Job ▸ Convert phonemes to match language."),
            ("b", "Import Untuned Reference VSQx"),
            ("", "Optional. If a syllable was split in a way the tool can't read for sure "
                 "(e.g. a held vowel next to a real vowel syllable), also load the UN-tuned "
                 "version of the same line. It pins the exact syllable boundaries by timing. "
                 "IMPORTANT: the tuned and un-tuned lines must have the SAME number of "
                 "syllables, or they won't line up."),
            ("h", "3 · Several vocal lines"),
            ("", "If a file has more than one vocal line, you'll be asked which one to "
                 "re-lyric. Only that line is changed; the others are left exactly as they were."),
            ("h", "4 · Batch lyrics"),
            ("", "Paste a whole line of syllables at once (spaces or new lines between them) "
                 "instead of typing one by one. Tick 'Auto-split kana' to break a continuous "
                 "kana string like きらきら into き ら き ら."),
            ("h", "5 · Play it back"),
            ("", "Press ▶ Play to hear the loaded notes; ■ Stop halts. 'Out' chooses where "
                 "the sound goes; 'Sound' picks an instrument for the built-in synth. Click a "
                 "row (or a note) first to play from there — like dropping a playhead."),
            ("b", "A) Quick — Windows built-in synth (no setup)"),
            ("", "Set Out = 'Microsoft GS Wavetable Synth', pick a Sound, press Play."),
            ("b", "B) Hear it with your FL Studio instrument (via loopMIDI)"),
            ("", "1. Download & install loopMIDI (free, by Tobias Erichsen)."),
            ("", "2. Open loopMIDI, type a name (e.g. 'ToFL') and click + to create the port. "
                 "Leave loopMIDI running."),
            ("", "3. In FL Studio: Options ▸ MIDI Settings. Under Input, select 'ToFL', click "
                 "Enable, and give it a Controller type = (generic) and a Port number, e.g. 0."),
            ("", "4. In FL, add your instrument to a channel; set that channel to receive on "
                 "the same MIDI port (channel's MIDI input port = 0), and enable it."),
            ("", "5. Back here: click ↻, set Out = 'ToFL', press ▶ Play. FL plays the notes "
                 "with your instrument. (The 'Sound' menu is ignored when routing to FL.)"),
            ("h", "6 · Edit notes (MIDI mode)"),
            ("", "After Open MIDI, you can fix the melody right on the piano-roll:"),
            ("", "• Drag a note to move it (and change its pitch); drag its right edge to resize."),
            ("", "• Double-click an empty spot to add a note; type a lyric for it like any other."),
            ("", "• Select a row (or click a note) and press Delete to remove it."),
            ("", "• Transpose all notes with the −8va / −1 / +1 / +8va buttons, or Shift+↑/↓ "
                 "(semitone) and Ctrl+↑/↓ (octave)."),
            ("", "• Undo / Redo (Ctrl+Z / Ctrl+Y) reverse any move, resize, add, delete or "
                 "transpose. (Editing is off in re-lyric mode so your Piapro tuning is never "
                 "altered — there, clicking a note just highlights its syllable.)"),
            ("h", "The piano-roll"),
            ("", "The strip up top shows your notes. ORANGE = a syllable's first note; "
                 "LAVENDER = a held/tuning note that continues it. Click a row (or a note) "
                 "to light it up and locate it."),
            ("", "Zoom & scroll, just like FL Studio: the Zoom H −/＋ buttons or Ctrl+wheel "
                 "zoom time (horizontal); the V −/＋ buttons or Alt+wheel zoom pitch "
                 "(vertical). Plain mouse-wheel scrolls up/down, Shift+wheel scrolls "
                 "sideways. A vertical scrollbar appears when the notes are taller than "
                 "the view, and the whole roll grows when you enlarge the window."),
        ]

    def _choose_clip(self, clips, preselect=0,
                     prompt="This file has several vocal lines.\nPick the one to re-lyric:",
                     ok_text="Re-lyric this line"):
        dlg = self._dialog("Choose a vocal line", 580, 360)
        ctk.CTkLabel(dlg, text=prompt, font=self.cf_body, text_color=PAPER,
                     justify="left").pack(anchor="w", padx=16, pady=(16, 6))
        box = tk.Listbox(dlg, height=min(12, len(clips)), bg=ABYSS, fg=PAPER, selectbackground=ORANGE,
                         selectforeground=INK, highlightthickness=1, highlightbackground=PURPLE,
                         borderwidth=0, activestyle="none", font=self.fonts["body"])
        for c in clips:
            box.insert("end", "  %s   —   %d notes, %d syllables"
                       % (c.label, len(c.notes), len(moras_of(c.notes))))
        preselect = max(0, min(preselect, len(clips) - 1))
        box.selection_set(preselect)
        box.see(preselect)
        box.pack(fill="both", expand=True, padx=16)
        chosen = {"clip": None}

        def ok(_=None):
            sel = box.curselection()
            if sel:
                chosen["clip"] = clips[int(sel[0])]
            dlg.destroy()

        row = ctk.CTkFrame(dlg, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=16)
        self._btn(row, ok_text, ok, kind="primary").pack(side="right")
        self._btn(row, "Cancel", dlg.destroy).pack(side="right", padx=(0, 8))
        box.bind("<Double-1>", ok)
        dlg.bind("<Return>", ok)
        box.focus_set()
        self.wait_window(dlg)
        return chosen["clip"]

    # ---- File actions ------------------------------------------------------
    def open_midi(self):
        path = filedialog.askopenfilename(
            title="Open MIDI file", initialdir=self._dir(),
            filetypes=[("MIDI files", "*.mid *.midi"), ("All files", "*.*")])
        if not path:
            return
        self._remember_dir(path)
        try:
            self.song = read_midi(path)
        except Exception as exc:  # noqa: BLE001 - surface any parse error to the user
            messagebox.showerror("Could not read MIDI", str(exc))
            return
        self.midi_path = path
        self.export_mode = "midi"
        self.vsqx_path = None
        self.clip = None
        self.baseline_path = None
        self.baseline_starts = None
        self._undo.clear()
        self._redo.clear()
        self._ppt = self._PPT
        self._vzoom = 1.0
        self.draw_notes = self.song.notes
        self._info_prefix = "%s  —  %d notes, %s BPM, %d/%d" % (
            os.path.basename(path), len(self.song.notes), self.song.bpm,
            self.song.numerator, self.song.denominator)
        self._populate()
        self._sync_edit_bar()
        self.status.configure(text="› type a syllable per note (Enter = next). Drag notes on the "
                              "roll to move/re-pitch, drag a right edge to resize, Delete to remove.")
        if self.song.notes:
            first = self.tree.get_children()[0]
            self.tree.selection_set(first)
            self.tree.focus(first)

    def open_tuned_vsqx(self):
        """Open a tuned .vsqx to put NEW lyrics on the same melody, keeping the tuning.
        If the file holds several vocal lines you pick one; each row is then one syllable."""
        path = filedialog.askopenfilename(
            title="Open a tuned VSQX to re-lyric", initialdir=self._dir(),
            filetypes=[("VOCALOID VSQX", "*.vsqx"), ("All files", "*.*")])
        if not path:
            return
        self._remember_dir(path)
        try:
            hdr = read_vsqx(path)
            clips = [c for c in read_clips(path) if c.notes]
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Could not read VSQX", str(exc))
            return
        if not clips:
            messagebox.showwarning("No vocal lines", "This .vsqx has no sung notes to re-lyric.")
            return
        if len(clips) == 1:
            clip = clips[0]
        else:
            clip = self._choose_clip(clips)
            if clip is None:
                return
        self.export_mode = "relyric"
        self.vsqx_path = path
        self.midi_path = path
        self.clip = clip
        self.baseline_path = None
        self.baseline_starts = None
        self._undo.clear()
        self._redo.clear()
        self._ppt = self._PPT
        self._vzoom = 1.0
        self._show_clip(clip, hdr, by_mora=True)
        self._sync_edit_bar()
        tag = "" if len(clips) == 1 else "  [%s]" % clip.label
        self._info_prefix = "%s  —  %d syllables, %s BPM, %d/%d  (re-lyric)%s" % (
            os.path.basename(path), len(self.song.notes), hdr.bpm,
            hdr.numerator, hdr.denominator, tag)
        self._refresh_info()
        self.status.configure(
            text="Type the NEW lyric for each syllable (Enter = save & next). Export keeps "
                 "your tuning. If a syllable was split oddly, add the un-tuned file.")

    def open_baseline(self):
        """Optionally load the UN-tuned version so syllable boundaries are exact even
        when a tuning tail shares the next syllable's vowel (e.g. [ke e e e] e)."""
        if self.export_mode != "relyric" or self.clip is None:
            messagebox.showinfo("Open a tuned file first",
                                "First use 'Import VSQx' to open the tuned file (and pick a line), "
                                "then add its un-tuned version here.")
            return
        path = filedialog.askopenfilename(
            title="Open the UN-tuned version (one note per syllable)", initialdir=self._dir(),
            filetypes=[("VOCALOID VSQX", "*.vsqx"), ("All files", "*.*")])
        if not path:
            return
        self._remember_dir(path)
        try:
            hdr = read_vsqx(path)
            bclips = read_clips(path)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Could not read VSQX", str(exc))
            return
        cand = [c for c in bclips if c.notes]
        if not cand:
            messagebox.showwarning("No notes", "That file has no notes to use as a guide.")
            return
        default = next((k for k, c in enumerate(cand)
                        if c.track_name == self.clip.track_name
                        and c.part_name == self.clip.part_name), None)
        if default is None:
            default = self.clip.index if self.clip.index < len(cand) else 0
        if len(cand) == 1:
            match = cand[0]
        else:
            match = self._choose_clip(cand, preselect=default, ok_text="Use this line",
                                      prompt="Which un-tuned line matches the one you're "
                                             "re-lyricing?\n(the matching line is highlighted)")
            if match is None:
                return
        self.baseline_path = path
        self.baseline_starts = sorted(n.start for n in match.notes)
        self._show_clip(match, hdr, by_mora=False, draw=self.clip.notes)
        self._sync_edit_bar()
        self._info_prefix = "%s + un-tuned %s  —  %d syllables (exact splits)" % (
            os.path.basename(self.vsqx_path), os.path.basename(path), len(match.notes))
        self._refresh_info()
        self.status.configure(text="Using the un-tuned file for exact splits. Type new lyrics; "
                              "export keeps all tuning.")

    def _show_clip(self, clip, hdr, by_mora=True, draw=None):
        song = Song(bpm=hdr.bpm, numerator=hdr.numerator,
                    denominator=hdr.denominator, pre_measure=hdr.pre_measure)
        if by_mora:
            for m in moras_of(clip.notes):
                song.notes.append(Note(m.start, m.dur, m.pitch, 64, m.lyric))
        else:
            for n in clip.notes:
                song.notes.append(Note(n.start, n.dur, n.key, 64, n.lyric))
        self.song = song
        self.draw_notes = list(draw if draw is not None else clip.notes)
        self._populate()
        kids = self.tree.get_children()
        if kids:
            self.tree.selection_set(kids[0])
            self.tree.focus(kids[0])

    def export_vsqx(self):
        if not self.song or not self.song.notes:
            messagebox.showwarning("Nothing to export", "Open a MIDI file first.")
            return
        self._commit_open_editor()
        if self.export_mode == "relyric":
            self._export_relyric()
            return
        empties = sum(1 for n in self.song.notes if not n.lyric.strip())
        if empties and not messagebox.askokcancel(
                "Some notes have no lyric",
                "%d of %d notes don't have a lyric yet — they'll sing the default 'あ'.\n\n"
                "Export anyway?" % (empties, len(self.song.notes))):
            return
        default = os.path.splitext(os.path.basename(self.midi_path or "lyrics"))[0] + ".vsqx"
        path = filedialog.asksaveasfilename(
            title="Export VSQX", defaultextension=".vsqx", initialfile=default,
            initialdir=self._dir(),
            filetypes=[("VOCALOID VSQX", "*.vsqx"), ("All files", "*.*")])
        if not path:
            return
        self._remember_dir(path)
        seq = os.path.splitext(os.path.basename(path))[0]
        try:
            write_vsqx(self.song, path, seq_name=seq, part_name=seq)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Export failed", str(exc))
            return
        self.status.configure(text="Exported %s. In Piapro: File > Import > VSQX." % os.path.basename(path))
        messagebox.showinfo("Exported",
                            "Saved:\n%s\n\nIn Piapro Studio:\n1) File > Import > VSQX\n"
                            "2) If every note sings 'a', run Job > Convert phonemes to match "
                            "language." % path)

    def _export_relyric(self):
        if self.baseline_starts:
            gap = unmapped_moras(self.clip.notes, self.baseline_starts)
            if gap and not messagebox.askokcancel(
                    "Syllables don't line up",
                    "%d un-tuned syllable(s) have no matching tuned notes — the un-tuned file "
                    "probably has a different syllable count than this tuned line.\n\n"
                    "The result may be shifted. Export anyway?" % gap):
                return
        default = os.path.splitext(os.path.basename(self.vsqx_path))[0] + "_relyric.vsqx"
        path = filedialog.asksaveasfilename(
            title="Export re-lyriced VSQX", defaultextension=".vsqx", initialfile=default,
            initialdir=self._dir(),
            filetypes=[("VOCALOID VSQX", "*.vsqx"), ("All files", "*.*")])
        if not path:
            return
        self._remember_dir(path)
        new_lyrics = [n.lyric for n in self.song.notes]
        try:
            changed = relyric_clip(self.vsqx_path, self.clip.index, new_lyrics, path,
                                   baseline_starts=self.baseline_starts)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Re-lyric failed", str(exc))
            return
        self.status.configure(text="Re-lyriced %d note(s) in '%s' → %s."
                              % (changed, self.clip.label, os.path.basename(path)))
        messagebox.showinfo("Re-lyriced",
                            "Saved:\n%s\n\nLine: %s\nAll tuning (pitches & note splits) is "
                            "preserved; the other vocal lines are untouched.\n\nIn Piapro Studio:\n"
                            "1) File > Import > VSQX\n2) Run Job > Convert phonemes to match "
                            "language so the new words sing right." % (path, self.clip.label))

    # ---- Table + inline lyric editing -------------------------------------
    def _refresh_info(self):
        """Show file details + a live 'X / N lyrics' counter (MIDI mode only). The
        counter turns mint-green once every note has a lyric."""
        total = len(self.song.notes) if self.song else 0
        text, color = self._info_prefix, ORANGE
        if self.export_mode == "midi" and total:
            filled = sum(1 for n in self.song.notes if n.lyric.strip())
            text = "%s  ·  %d/%d lyrics" % (self._info_prefix, filled, total)
            color = DONE if filled == total else ORANGE
        self.info.configure(text=text, text_color=color)

    def _populate(self):
        self._destroy_editor()
        self.tree.delete(*self.tree.get_children())
        tpm = ticks_per_measure(self.song.numerator, self.song.denominator)
        beat_ticks = max(1, tpm // self.song.numerator)
        for i, n in enumerate(self.song.notes):
            bar = n.start // tpm + 1
            beat = (n.start % tpm) // beat_ticks + 1
            tags = (("even",) if i % 2 else ("odd",)) if n.lyric.strip() else ("empty",)
            self.tree.insert("", "end", tags=tags, values=(i + 1, "%d.%d" % (bar, beat),
                                                            midi_note_name(n.key), n.dur, n.lyric))
        self._draw_piano_roll()
        self._refresh_info()

    def _edit_selected(self):
        sel = self.tree.selection()
        if sel:
            self._begin_edit(sel[0])

    def _begin_edit(self, iid):
        self._destroy_editor()
        self.tree.see(iid)
        bbox = self.tree.bbox(iid, column="lyric")
        if not bbox:
            return
        x, y, w, h = bbox
        entry = tk.Entry(self.tree, bg=ABYSS, fg=PAPER, insertbackground=ORANGE, relief="flat",
                         highlightthickness=1, highlightbackground=ORANGE, font=self.fonts["body"])
        entry.insert(0, self.tree.set(iid, "lyric"))
        entry.select_range(0, "end")
        entry.focus_set()
        entry.place(x=x, y=y, width=w, height=h)
        entry.bind("<Return>", lambda e: self._commit(iid, entry, +1))
        entry.bind("<Tab>", lambda e: self._commit(iid, entry, +1))
        entry.bind("<Down>", lambda e: self._commit(iid, entry, +1))
        entry.bind("<Up>", lambda e: self._commit(iid, entry, -1))
        entry.bind("<Escape>", lambda e: self._destroy_editor())
        self._editor = (entry, iid)

    def _commit(self, iid, entry, move=0):
        value = entry.get()
        self.tree.set(iid, "lyric", value)
        idx = int(self.tree.set(iid, "idx")) - 1
        if value.strip():
            self.tree.item(iid, tags=(("even",) if idx % 2 else ("odd",)))
        else:
            self.tree.item(iid, tags=("empty",))
        if self.song and 0 <= idx < len(self.song.notes):
            self.song.notes[idx].lyric = value
        self._refresh_info()
        self._destroy_editor()
        if move:
            kids = self.tree.get_children()
            j = kids.index(iid) + move
            if 0 <= j < len(kids):
                nxt = kids[j]
                self.tree.selection_set(nxt)
                self.tree.focus(nxt)
                self.tree.see(nxt)
                self.after(10, lambda: self._begin_edit(nxt))
        return "break"

    def _commit_open_editor(self):
        if self._editor:
            entry, iid = self._editor
            self._commit(iid, entry, 0)

    def _destroy_editor(self):
        if self._editor:
            self._editor[0].destroy()
            self._editor = None


if __name__ == "__main__":
    App().mainloop()
