"""MIDI -> VSQX lyric tool — a small desktop app.

Workflow: in FL Studio, export your melody as a MIDI file. Open it here, type one
syllable per note (Enter jumps to the next note), then Export VSQX and import that
into Piapro Studio (File > Import > VSQX).

Run:  python app.py      (needs Python 3.9+ and `pip install mido`)
"""
from __future__ import annotations

import os
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

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
# Her branding palette (#000000 / #575068 / #f29a30 / #e1d8ef) plus her official
# purples (#62567E, #9575E2): deep plum panels, lavender text, orange accents.
INK = "#000000"        # deepest background (piano-roll)
ABYSS = "#1b1822"      # table background (derived dark plum, softer than pure black)
PLUM = "#575068"       # window / panels
PURPLE = "#62567E"     # headings, gridlines
LILAC = "#9575E2"      # continuation (tail) notes
ORANGE = "#f29a30"     # primary accent: buttons, lead notes, selection
PAPER = "#e1d8ef"      # text
GLOW = "#ffce8a"       # lighter orange for hover/emphasis (derived)

# Selectable UI font families (display name -> family). Tk falls back if a font is
# missing. The Sound/font picker in the header switches between these live.
FONT_THEMES = {
    "Segoe UI · clean": "Segoe UI",
    "Bahnschrift · tech": "Bahnschrift",
    "Consolas · mono": "Consolas",
    "Verdana · rounded": "Verdana",
    "Yu Gothic · modern": "Yu Gothic UI",
}
FONT = ("Segoe UI", 11)        # safe fallback / default body
FONT_B = ("Segoe UI", 11, "bold")
FONT_MONO = ("Consolas", 10)   # piano-roll + status accents

# Derived deep shades for gradients (futuristic glass/neon look).
NIGHT = "#241f30"      # top of the piano-roll gradient
EMBER = "#3a2f2a"      # warm tint at the right of the header gradient


def _lerp(c1, c2, t):
    """Blend two #rrggbb hex colours; t clamped to [0, 1]."""
    t = max(0.0, min(1.0, t))
    a = (int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16))
    b = (int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16))
    return "#%02x%02x%02x" % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Made by M. Y.")
        self.geometry("1000x680")
        self.minsize(760, 460)

        self.song = None        # Song (from a MIDI import, or moras of a tuned .vsqx)
        self.midi_path = None
        self.export_mode = "midi"   # "midi" = build new .vsqx; "relyric" = edit a tuned one
        self.vsqx_path = None       # the tuned source file, in re-lyric mode
        self.clip = None            # the chosen Clip (one vocal line) in re-lyric mode
        self.baseline_path = None   # optional un-tuned version, for exact syllable splits
        self.baseline_starts = None # its chosen clip's syllable start ticks
        self.draw_notes = []        # raw notes drawn in the piano-roll
        self._note_items = []       # (canvas_id, note, is_lead) for highlight
        self._roll_t0 = 0           # tick at the left edge of the piano-roll
        self._pad = 16              # piano-roll inner padding
        self._row_h = 8.0           # piano-roll pixels per semitone (set when drawn)
        self._kmax = 84             # top pitch on the roll (set when drawn)
        self._drag = None           # active note drag {note, mode, ...}
        self._editor = None     # (Entry, row_iid) while editing a lyric cell
        self._play_thread = None    # background MIDI playback thread
        self._stop = threading.Event()
        self.font_name = "Verdana · rounded"     # current UI font (see FONT_THEMES)
        self.fonts = self._fonts_for(self.font_name)

        self._apply_theme()
        self._build_ui()
        self._bind_keys()

    # ---- theme -------------------------------------------------------------
    @staticmethod
    def _fonts_for(name):
        """Build the font set for a chosen family (see FONT_THEMES)."""
        fam = FONT_THEMES.get(name, "Segoe UI")
        return {
            "body": (fam, 11),
            "bold": (fam, 11, "bold"),
            "title": (fam, 18, "bold"),
            "sub": ("Consolas", 10),
            "small": (fam, 9),
        }

    def _apply_theme(self):
        """Dark-plum / orange 'Ina' theme via the ttk 'clam' base, current fonts."""
        f = self.fonts
        self.configure(bg=PLUM)
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=PLUM, foreground=PAPER, fieldbackground=ABYSS,
                        bordercolor=PURPLE, font=f["body"])
        style.configure("TFrame", background=PLUM)
        style.configure("Head.TFrame", background=INK)
        style.configure("Rule.TFrame", background=ORANGE)          # thin accent rule
        style.configure("TLabel", background=PLUM, foreground=PAPER, font=f["body"])
        style.configure("Title.TLabel", background=INK, foreground=ORANGE, font=f["title"])
        style.configure("Sub.TLabel", background=INK, foreground=LILAC, font=f["sub"])
        style.configure("Info.TLabel", background=PLUM, foreground=ORANGE, font=f["bold"])
        style.configure("Status.TLabel", background=INK, foreground=LILAC, font=f["sub"])
        style.configure("TButton", background=ORANGE, foreground=INK, borderwidth=0,
                        focuscolor=PLUM, padding=(12, 6), font=f["bold"])
        style.map("TButton", background=[("active", GLOW), ("pressed", PURPLE)],
                  foreground=[("active", INK), ("pressed", PAPER)])
        style.configure("Ghost.TButton", background=PURPLE, foreground=PAPER)
        style.map("Ghost.TButton", background=[("active", LILAC), ("pressed", PLUM)],
                  foreground=[("active", INK)])
        style.configure("Treeview", background=ABYSS, fieldbackground=ABYSS,
                        foreground=PAPER, rowheight=28, borderwidth=0, font=f["body"])
        style.configure("Treeview.Heading", background=PURPLE, foreground=PAPER,
                        relief="flat", font=f["bold"])
        style.map("Treeview.Heading", background=[("active", PLUM)])
        style.map("Treeview", background=[("selected", ORANGE)],
                  foreground=[("selected", INK)])
        style.configure("TScrollbar", background=PLUM, troughcolor=ABYSS,
                        bordercolor=PLUM, arrowcolor=PAPER)
        style.configure("TCombobox", fieldbackground=ABYSS, background=PURPLE,
                        foreground=PAPER, arrowcolor=ORANGE, bordercolor=PURPLE, padding=4)
        style.map("TCombobox", fieldbackground=[("readonly", ABYSS)],
                  foreground=[("readonly", PAPER)], selectbackground=[("readonly", ABYSS)])
        style.configure("TCheckbutton", background=PLUM, foreground=PAPER, font=f["body"])
        style.map("TCheckbutton", background=[("active", PLUM)],
                  foreground=[("active", GLOW)], indicatorcolor=[("selected", ORANGE)])

    def _set_font_theme(self, name):
        """Switch the UI font family live and redraw."""
        self.font_name = name
        self.fonts = self._fonts_for(name)
        self._apply_theme()
        self._draw_banner()
        self._draw_piano_roll()

    def _draw_banner(self):
        """Decorative gradient header: title + subtitle + a neon gradient rule."""
        c = getattr(self, "banner", None)
        if c is None:
            return
        c.delete("all")
        w = max(c.winfo_width(), 1)
        h = int(c.cget("height"))
        # horizontal gradient: ink → plum → a warm ember on the right
        steps = 64
        for i in range(steps):
            t = i / (steps - 1)
            col = _lerp(INK, PURPLE, t / 0.65) if t < 0.65 else _lerp(PURPLE, EMBER, (t - 0.65) / 0.35)
            c.create_rectangle(w * i / steps, 0, w * (i + 1) / steps + 1, h, fill=col, outline="")
        c.create_text(18, h // 2 - 7, anchor="w", text="MADE BY M. Y.",
                      fill=ORANGE, font=self.fonts["title"])
        c.create_text(20, h // 2 + 15, anchor="w",
                      text="midi → vsqx  ·  re-lyric  ·  keep your tuning",
                      fill=PAPER, font=self.fonts["sub"])
        # neon rule along the bottom: purple → orange → lilac
        for i in range(steps):
            t = i / (steps - 1)
            col = _lerp(PURPLE, ORANGE, t * 2) if t < 0.5 else _lerp(ORANGE, LILAC, (t - 0.5) * 2)
            c.create_rectangle(w * i / steps, h - 3, w * (i + 1) / steps + 1, h, fill=col, outline="")

    # ---- UI construction ---------------------------------------------------
    def _build_ui(self):
        # gradient banner (decorative header) + neon rule
        self.banner = tk.Canvas(self, height=58, bg=INK, highlightthickness=0)
        self.banner.pack(side="top", fill="x")
        self.banner.bind("<Configure>", lambda e: self._draw_banner())

        # file actions (+ font picker / help on the right)
        toolbar = ttk.Frame(self, padding=(8, 8, 8, 2))
        toolbar.pack(side="top", fill="x")
        for text, cmd in (("Open MIDI (Ctrl+O)", self.open_midi),
                          ("Import VSQx (Ctrl+R)", self.open_tuned_vsqx),
                          ("Import Untuned Reference VSQx", self.open_baseline),
                          ("Batch lyrics", self.batch_lyrics),
                          ("Export VSQX (Ctrl+S)", self.export_vsqx)):
            ttk.Button(toolbar, text=text, command=cmd).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="?  Help", style="Ghost.TButton",
                   command=self._show_help).pack(side="right")
        self.font_cb = ttk.Combobox(toolbar, width=17, state="readonly",
                                     values=list(FONT_THEMES))
        self.font_cb.set(self.font_name)
        self.font_cb.pack(side="right", padx=(0, 10))
        self.font_cb.bind("<<ComboboxSelected>>",
                          lambda e: self._set_font_theme(self.font_cb.get()))
        ttk.Label(toolbar, text="Font").pack(side="right", padx=(0, 6))

        # playback bar
        play = ttk.Frame(self, padding=(8, 2, 8, 6))
        play.pack(side="top", fill="x")
        self.play_btn = ttk.Button(play, text="▶  Play", command=self.toggle_play)
        self.play_btn.pack(side="left", padx=(0, 8))
        ttk.Label(play, text="Out").pack(side="left")
        self.port_cb = ttk.Combobox(play, width=30, state="readonly")
        self.port_cb.pack(side="left", padx=(4, 12))
        ttk.Label(play, text="Sound").pack(side="left")
        self.sound_cb = ttk.Combobox(play, width=16, state="readonly",
                                     values=[n for n, _ in GM_INSTRUMENTS])
        self.sound_cb.current(0)
        self.sound_cb.pack(side="left", padx=(4, 12))
        ttk.Button(play, text="↻", width=3, style="Ghost.TButton",
                   command=self._refresh_ports).pack(side="left")
        self.info = ttk.Label(play, text="No file loaded.", style="Info.TLabel")
        self.info.pack(side="right", padx=10)
        self._refresh_ports()

        # piano-roll visualizer (notes over time × pitch)
        roll = ttk.Frame(self, padding=(8, 4, 8, 0))
        roll.pack(side="top", fill="x")
        self.canvas = tk.Canvas(roll, height=200, bg=INK, highlightthickness=1,
                                highlightbackground=PURPLE)
        hsb = ttk.Scrollbar(roll, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=hsb.set)
        self.canvas.pack(side="top", fill="x")
        hsb.pack(side="top", fill="x")
        self.canvas.bind("<Configure>", lambda e: self._draw_piano_roll())
        self.canvas.bind("<Button-1>", self._roll_press)
        self.canvas.bind("<B1-Motion>", self._roll_drag)
        self.canvas.bind("<ButtonRelease-1>", self._roll_release)

        # lyric table
        table = ttk.Frame(self, padding=(8, 8, 8, 0))
        table.pack(side="top", fill="both", expand=True)
        cols = ("idx", "bar", "pitch", "dur", "lyric")
        self.tree = ttk.Treeview(table, columns=cols, show="headings", selectmode="browse")
        widths = {"idx": 48, "bar": 90, "pitch": 90, "dur": 100, "lyric": 460}
        heads = {"idx": "#", "bar": "Bar.Beat", "pitch": "Pitch", "dur": "Dur (ticks)", "lyric": "Lyric"}
        for c in cols:
            self.tree.heading(c, text=heads[c])
            self.tree.column(c, width=widths[c], anchor=("w" if c == "lyric" else "center"))
        vsb = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", lambda e: self._edit_selected())
        self.tree.bind("<Return>", lambda e: self._edit_selected())
        self.tree.bind("<Delete>", lambda e: self._delete_note())
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._highlight_selection())

        self.status = ttk.Label(
            self, relief="flat", anchor="w", padding=8, style="Status.TLabel",
            text="› open a MIDI, or Import VSQx to re-lyric — press “?  Help” for a guide")
        self.status.pack(side="bottom", fill="x")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._draw_banner()
        self._draw_piano_roll()      # empty-state placeholder + legend

    def _bind_keys(self):
        self.bind("<Control-o>", lambda e: self.open_midi())
        self.bind("<Control-r>", lambda e: self.open_tuned_vsqx())
        self.bind("<Control-s>", lambda e: self.export_vsqx())

    # ---- piano-roll visualizer --------------------------------------------
    _PPT = 0.06       # pixels per tick (~115 px per 4/4 bar)
    _GRID = 120       # note-edit time snap (1/16 note, in ticks)

    def _lead_flags(self, notes):
        """Per-note bool: True if the note starts a new sung syllable."""
        flags, have = [], False
        for n in notes:
            flags.append(not (have and is_continuation(n.lyric)))
            have = True
        return flags

    def _draw_piano_roll(self):
        c = self.canvas
        c.delete("all")
        self._note_items = []
        notes = self.draw_notes
        if not notes:
            c.configure(scrollregion=(0, 0, 0, 0))
            c.create_text(14, 14, anchor="nw", fill=PURPLE, font=self.fonts["body"],
                          text="♪  piano-roll — open a MIDI or import a tuned VSQx")
            return
        H, pad = int(c.cget("height")), self._pad
        keys = [n.key for n in notes]
        kmin, kmax = min(keys), max(keys)
        row_h = max(3.0, min(14.0, (H - 2 * pad) / (kmax - kmin + 1)))
        t0 = min(n.start for n in notes)              # left edge = first note's bar
        tpm = ticks_per_measure(self.song.numerator, self.song.denominator) if self.song else 1920
        t0 = (t0 // tpm) * tpm if tpm else t0
        self._roll_t0, self._row_h, self._kmax = t0, row_h, kmax
        end = max(n.start + n.dur for n in notes)
        width = int((end - t0) * self._PPT) + 2 * pad
        full = max(width, c.winfo_width())
        c.configure(scrollregion=(0, 0, full, H))

        # gradient backdrop (night-purple at top → black at bottom) for depth
        bands = 22
        for i in range(bands):
            c.create_rectangle(0, H * i / bands, full, H * (i + 1) / bands + 1,
                               fill=_lerp(NIGHT, INK, i / (bands - 1)), outline="")

        def px(t):
            return pad + (t - t0) * self._PPT

        def py(k):
            return pad + (kmax - k) * row_h

        bar = t0
        while tpm and px(bar) <= width:
            c.create_line(px(bar), 0, px(bar), H, fill=PURPLE)
            bar += tpm

        for i, lead in enumerate(self._lead_flags(notes)):
            n = notes[i]
            x0, x1, y0 = px(n.start), px(n.start + n.dur), py(n.key)
            item = c.create_rectangle(x0, y0, max(x0 + 2, x1), y0 + row_h,
                                      fill=(ORANGE if lead else LILAC), outline=INK)
            self._note_items.append((item, n, lead))
            if lead and n.lyric:
                c.create_text(x0 + 1, y0 - 1, anchor="sw", fill=PAPER,
                              font=self.fonts["small"], text=n.lyric)

        # legend (sits at the start of the roll)
        lx = pad
        for color, label in ((ORANGE, "syllable"), (LILAC, "held note")):
            c.create_rectangle(lx, 2, lx + 11, 11, fill=color, outline=INK)
            t = c.create_text(lx + 15, 1, anchor="nw", fill=PAPER,
                              font=self.fonts["small"], text=label)
            lx = c.bbox(t)[2] + 12

    def _highlight_selection(self):
        """Light up the piano-roll notes belonging to the selected table row."""
        sel = self.tree.selection()
        if not sel or not self.song or not self._note_items:
            return
        i = self.tree.get_children().index(sel[0])
        notes = self.song.notes
        t0 = notes[i].start
        t1 = notes[i + 1].start if i + 1 < len(notes) else 1 << 30
        for item, n, lead in self._note_items:
            inside = t0 <= n.start < t1
            self.canvas.itemconfigure(
                item, fill=(PAPER if inside else (ORANGE if lead else LILAC)))
        sr = self.canvas.cget("scrollregion").split()
        if len(sr) == 4 and float(sr[2]) > 0:
            self.canvas.xview_moveto(
                max(0.0, ((t0 - self._roll_t0) * self._PPT - 40) / float(sr[2])))

    # ---- note editing (MIDI mode only; re-lyric never alters tuning) -------
    def _editable(self):
        return self.export_mode == "midi" and bool(self.draw_notes)

    def _hit_note(self, cx, cy):
        """Topmost note rectangle under (cx, cy) → (note, 'move'|'resize'), else None."""
        for item, n, _lead in reversed(self._note_items):
            x0, y0, x1, y1 = self.canvas.coords(item)
            if x0 - 2 <= cx <= x1 + 2 and y0 - 2 <= cy <= y1 + 2:
                return n, ("resize" if (x1 - cx) <= 6 and (x1 - x0) > 12 else "move")
        return None

    def _roll_press(self, e):
        self._drag = None
        if not self._editable():
            return
        cx, cy = self.canvas.canvasx(e.x), self.canvas.canvasy(e.y)
        hit = self._hit_note(cx, cy)
        if not hit:
            return
        n, mode = hit
        self._drag = {"note": n, "mode": mode, "cx": cx, "cy": cy,
                      "start0": n.start, "key0": n.key, "dur0": n.dur}
        if n in self.song.notes:                       # select the matching table row
            i, kids = self.song.notes.index(n), self.tree.get_children()
            if i < len(kids):
                self.tree.selection_set(kids[i])
                self.tree.focus(kids[i])
                self.tree.see(kids[i])

    def _roll_drag(self, e):
        d = self._drag
        if not d:
            return
        cx, cy = self.canvas.canvasx(e.x), self.canvas.canvasy(e.y)
        dtick = round((cx - d["cx"]) / self._PPT / self._GRID) * self._GRID
        n = d["note"]
        if d["mode"] == "resize":
            n.dur = max(self._GRID, d["dur0"] + dtick)
        else:
            n.start = max(0, d["start0"] + dtick)
            n.key = max(0, min(127, d["key0"] - int(round((cy - d["cy"]) / self._row_h))))
        self._draw_piano_roll()

    def _roll_release(self, _e):
        if self._drag:
            self._drag = None
            self._populate()                            # resync table + redraw

    def _delete_note(self):
        if not self._editable():
            return
        sel = self.tree.selection()
        if not sel:
            return
        i = self.tree.get_children().index(sel[0])
        if 0 <= i < len(self.song.notes):
            del self.song.notes[i]
            self.draw_notes = self.song.notes
            self._populate()
            self.status.config(text="› deleted a note — %d left." % len(self.song.notes))

    # ---- playback (built-in synth, or loopMIDI -> FL) ----------------------
    def _refresh_ports(self):
        names = []
        if mido is not None:
            try:
                names = mido.get_output_names()
            except Exception:  # noqa: BLE001
                names = []
        self.port_cb["values"] = names
        if names:
            if self.port_cb.get() not in names:
                self.port_cb.current(0)
            self.play_btn.state(["!disabled"])
        else:
            self.port_cb.set("(no MIDI output — see Help)")
            self.play_btn.state(["disabled"])

    def toggle_play(self):
        if self._play_thread and self._play_thread.is_alive():
            self._stop.set()                                  # second press = stop
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
        self._stop.clear()
        self.play_btn.config(text="■  Stop")
        self._play_thread = threading.Thread(
            target=self._play_worker, args=(list(self.draw_notes), port, program, bpm),
            daemon=True)
        self._play_thread.start()

    def _play_worker(self, notes, port_name, program, bpm):
        spt = 60.0 / (bpm * VSQ_RESOLUTION)                   # seconds per tick
        try:
            out = mido.open_output(port_name)
        except Exception as exc:  # noqa: BLE001
            self.after(0, lambda: messagebox.showerror("Playback failed", str(exc)))
            self.after(0, lambda: self.play_btn.config(text="▶  Play"))
            return
        t0 = min(n.start for n in notes)
        events = []
        for n in notes:
            v = max(1, min(127, n.velocity))
            events.append((n.start - t0, 1, n.key, v))        # note on
            events.append((n.start + n.dur - t0, 0, n.key, 0))  # note off
        events.sort(key=lambda e: (e[0], e[1]))               # offs before ons at a tie
        try:
            out.send(mido.Message("program_change", program=program))
            prev = 0
            for tick, on, key, vel in events:
                dt = (tick - prev) * spt
                if dt > 0 and self._stop.wait(dt):
                    break
                prev = tick
                out.send(mido.Message("note_on" if on else "note_off",
                                      note=key, velocity=vel))
        finally:
            try:
                out.send(mido.Message("control_change", control=123, value=0))  # all off
            except Exception:  # noqa: BLE001
                pass
            out.close()
            self.after(0, lambda: self.play_btn.config(text="▶  Play"))

    def _on_close(self):
        self._stop.set()
        self.destroy()

    # ---- batch lyric entry -------------------------------------------------
    def batch_lyrics(self):
        if not self.song or not self.song.notes:
            messagebox.showinfo("Open a file first",
                                "Open a MIDI or a tuned VSQX, then paste lyrics here.")
            return
        n = len(self.song.notes)
        dlg = tk.Toplevel(self)
        dlg.title("Batch lyrics")
        dlg.configure(bg=PLUM)
        dlg.transient(self)
        ttk.Label(dlg, padding=(10, 8), justify="left",
                  text="Paste %d syllables — one per note, separated by spaces or new "
                       "lines." % n).pack(anchor="w")
        txt = tk.Text(dlg, width=46, height=12, bg=ABYSS, fg=PAPER, insertbackground=ORANGE,
                      relief="flat", wrap="word", font=self.fonts["body"], spacing1=2,
                      highlightthickness=1, highlightbackground=PURPLE)
        txt.pack(fill="both", expand=True, padx=10)
        kana = tk.BooleanVar(value=False)
        ttk.Checkbutton(dlg, variable=kana, style="TCheckbutton",
                        text="Auto-split continuous kana  (きらきら → き ら き ら)").pack(
            anchor="w", padx=10, pady=(6, 0))
        txt.focus_set()

        def apply():
            raw = txt.get("1.0", "end")
            tokens = split_kana_moras(raw) if kana.get() else raw.split()
            if not tokens:
                dlg.destroy()
                return
            if len(tokens) != n and not messagebox.askokcancel(
                    "Count differs",
                    "You pasted %d syllables but there are %d notes.\n\n"
                    "Fill the first %d and leave the rest?" % (
                        len(tokens), n, min(len(tokens), n)), parent=dlg):
                return
            for i in range(min(len(tokens), n)):
                self.song.notes[i].lyric = tokens[i]
            self._populate()
            self.status.config(text="› filled %d syllable(s) from batch input."
                                     % min(len(tokens), n))
            dlg.destroy()

        bar = ttk.Frame(dlg, padding=10)
        bar.pack(fill="x")
        ttk.Button(bar, text="Fill lyrics", command=apply).pack(side="right")
        ttk.Button(bar, text="Cancel", command=dlg.destroy).pack(side="right", padx=(0, 6))
        dlg.bind("<Escape>", lambda e: dlg.destroy())
        dlg.update_idletasks()
        dlg.grab_set()

    # ---- help --------------------------------------------------------------
    def _show_help(self):
        dlg = tk.Toplevel(self)
        dlg.title("Made by M. Y. — Help")
        dlg.configure(bg=PLUM)
        dlg.transient(self)
        fam = self.fonts["body"][0]
        txt = tk.Text(dlg, width=80, height=28, bg=ABYSS, fg=PAPER, relief="flat",
                      wrap="word", font=self.fonts["body"], padx=22, pady=16,
                      highlightthickness=0, spacing2=4)        # spacing2 = within-paragraph
        txt.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(dlg, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        # generous spacing so nothing feels crammed
        txt.tag_configure("h", foreground=ORANGE, font=(fam, 14, "bold"),
                          spacing1=20, spacing3=8)             # section headings
        txt.tag_configure("b", foreground=GLOW, font=self.fonts["bold"],
                          spacing1=10, spacing3=4)             # sub-headings
        txt.tag_configure("p", foreground=PAPER, spacing3=14,  # body paragraphs
                          lmargin1=12, lmargin2=12, rmargin=14)
        for kind, line in self._help_lines():
            txt.insert("end", line + "\n", kind or "p")
        txt.configure(state="disabled")
        dlg.bind("<Escape>", lambda e: dlg.destroy())
        dlg.update_idletasks()
        dlg.grab_set()

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
                 "the sound goes; 'Sound' picks an instrument for the built-in synth."),
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
            ("", "After Open MIDI, you can fix the melody right on the piano-roll: drag a note "
                 "to move it (and change its pitch), drag its right edge to resize, or select "
                 "a row and press Delete to remove it. (Editing is off in re-lyric mode so "
                 "your Piapro tuning is never altered.)"),
            ("h", "The piano-roll"),
            ("", "The strip up top shows your notes. ORANGE = a syllable's first note; "
                 "LAVENDER = a held/tuning note that continues it. Click a row to light up "
                 "and locate that syllable."),
        ]

    # ---- File actions ------------------------------------------------------
    def open_midi(self):
        path = filedialog.askopenfilename(
            title="Open MIDI file",
            filetypes=[("MIDI files", "*.mid *.midi"), ("All files", "*.*")])
        if not path:
            return
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
        self.draw_notes = self.song.notes      # piano-roll shows the MIDI notes
        self._populate()
        self.info.config(text="%s  —  %d notes, %s BPM, %d/%d" % (
            os.path.basename(path), len(self.song.notes), self.song.bpm,
            self.song.numerator, self.song.denominator))
        self.status.config(text="› type a syllable per note (Enter = next). Drag notes on the "
                                "roll to move/re-pitch, drag a right edge to resize, Delete to remove.")
        if self.song.notes:
            first = self.tree.get_children()[0]
            self.tree.selection_set(first)
            self.tree.focus(first)

    def open_tuned_vsqx(self):
        """Open a tuned .vsqx to put NEW lyrics on the same melody, keeping the tuning.
        If the file holds several vocal lines you pick one; each row is then one syllable."""
        path = filedialog.askopenfilename(
            title="Open a tuned VSQX to re-lyric",
            filetypes=[("VOCALOID VSQX", "*.vsqx"), ("All files", "*.*")])
        if not path:
            return
        try:
            hdr = read_vsqx(path)                        # file header (tempo/time-sig)
            clips = [c for c in read_clips(path) if c.notes]
        except Exception as exc:  # noqa: BLE001 - surface any parse error to the user
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
                return                                   # user cancelled the picker
        self.export_mode = "relyric"
        self.vsqx_path = path
        self.midi_path = path
        self.clip = clip
        self.baseline_path = None
        self.baseline_starts = None
        self._show_clip(clip, hdr, by_mora=True)
        tag = "" if len(clips) == 1 else "  [%s]" % clip.label
        self.info.config(text="%s  —  %d syllables, %s BPM, %d/%d  (re-lyric)%s" % (
            os.path.basename(path), len(self.song.notes), hdr.bpm,
            hdr.numerator, hdr.denominator, tag))
        self.status.config(
            text="Type the NEW lyric for each syllable (Enter = save & next). Export keeps "
                 "your tuning. If a syllable was split oddly, add the un-tuned file.")

    def open_baseline(self):
        """Optionally load the UN-tuned version so syllable boundaries are exact even
        when a tuning tail shares the next syllable's vowel (e.g. [ke e e e] e)."""
        if self.export_mode != "relyric" or self.clip is None:
            messagebox.showinfo(
                "Open a tuned file first",
                "First use 'Re-lyric tuned VSQX…' to open the tuned file (and pick a line), "
                "then add its un-tuned version here.")
            return
        path = filedialog.askopenfilename(
            title="Open the UN-tuned version (one note per syllable)",
            filetypes=[("VOCALOID VSQX", "*.vsqx"), ("All files", "*.*")])
        if not path:
            return
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
        # default to the SAME vocal line by name (else same position); let the user choose
        default = next((k for k, c in enumerate(cand)
                        if c.track_name == self.clip.track_name
                        and c.part_name == self.clip.part_name), None)
        if default is None:
            default = self.clip.index if self.clip.index < len(cand) else 0
        if len(cand) == 1:
            match = cand[0]
        else:
            match = self._choose_clip(
                cand, preselect=default, ok_text="Use this line",
                prompt="Which un-tuned line matches the one you're re-lyricing?\n"
                       "(the matching line is highlighted)")
            if match is None:
                return                                # user cancelled
        self.baseline_path = path
        self.baseline_starts = sorted(n.start for n in match.notes)
        # table = un-tuned syllables; piano-roll keeps showing the TUNED notes
        self._show_clip(match, hdr, by_mora=False, draw=self.clip.notes)
        self.info.config(text="%s + un-tuned %s  —  %d syllables (exact splits)" % (
            os.path.basename(self.vsqx_path), os.path.basename(path), len(match.notes)))
        self.status.config(
            text="Using the un-tuned file for exact splits. Type new lyrics; export keeps "
                 "all tuning.")

    def _show_clip(self, clip, hdr, by_mora=True, draw=None):
        """Load a clip into the table — one row per mora (by_mora) or per note. The
        piano-roll draws `draw` if given (e.g. the tuned notes while the table shows the
        un-tuned syllables), otherwise the clip's own notes."""
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

    def _choose_clip(self, clips, preselect=0,
                     prompt="This file has several vocal lines.\nPick the one to re-lyric:",
                     ok_text="Re-lyric this line"):
        """Modal list of vocal lines; returns the chosen Clip, or None if cancelled."""
        dlg = tk.Toplevel(self)
        dlg.title("Choose a vocal line")
        dlg.configure(bg=PLUM)
        dlg.transient(self)
        ttk.Label(dlg, padding=8, justify="left", text=prompt).pack(anchor="w")
        box = tk.Listbox(dlg, width=66, height=min(12, len(clips)), activestyle="dotbox",
                         bg=ABYSS, fg=PAPER, selectbackground=ORANGE, selectforeground=INK,
                         highlightthickness=1, highlightbackground=PURPLE, borderwidth=0,
                         font=self.fonts["body"])
        for c in clips:
            box.insert("end", "  %s   —   %d notes, %d syllables"
                       % (c.label, len(c.notes), len(moras_of(c.notes))))
        preselect = max(0, min(preselect, len(clips) - 1))
        box.selection_set(preselect)
        box.see(preselect)
        box.pack(fill="both", expand=True, padx=8)
        chosen = {"clip": None}

        def ok(_=None):
            sel = box.curselection()
            if sel:
                chosen["clip"] = clips[int(sel[0])]
            dlg.destroy()

        bar = ttk.Frame(dlg, padding=8)
        bar.pack(fill="x")
        ttk.Button(bar, text=ok_text, command=ok).pack(side="right")
        ttk.Button(bar, text="Cancel", command=dlg.destroy).pack(side="right", padx=(0, 6))
        box.bind("<Double-1>", ok)
        dlg.bind("<Return>", ok)
        dlg.bind("<Escape>", lambda e: dlg.destroy())
        dlg.update_idletasks()
        dlg.grab_set()
        box.focus_set()
        self.wait_window(dlg)
        return chosen["clip"]

    def export_vsqx(self):
        if not self.song or not self.song.notes:
            messagebox.showwarning("Nothing to export", "Open a MIDI file first.")
            return
        self._commit_open_editor()
        if self.export_mode == "relyric":
            self._export_relyric()
            return
        default = os.path.splitext(os.path.basename(self.midi_path or "lyrics"))[0] + ".vsqx"
        path = filedialog.asksaveasfilename(
            title="Export VSQX", defaultextension=".vsqx", initialfile=default,
            filetypes=[("VOCALOID VSQX", "*.vsqx"), ("All files", "*.*")])
        if not path:
            return
        seq = os.path.splitext(os.path.basename(path))[0]
        try:
            write_vsqx(self.song, path, seq_name=seq, part_name=seq)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Export failed", str(exc))
            return
        self.status.config(text="Exported %s. In Piapro: File > Import > VSQX." % os.path.basename(path))
        messagebox.showinfo(
            "Exported",
            "Saved:\n%s\n\nIn Piapro Studio:\n"
            "1) File > Import > VSQX\n"
            "2) If every note sings 'a', run Job > Convert phonemes to match language." % path)

    def _export_relyric(self):
        """Write the tuned source file back out with the new lyrics, tuning intact."""
        if self.baseline_starts:                  # un-tuned guide loaded: sanity-check fit
            gap = unmapped_moras(self.clip.notes, self.baseline_starts)
            if gap and not messagebox.askokcancel(
                    "Syllables don't line up",
                    "%d un-tuned syllable(s) have no matching tuned notes — the un-tuned "
                    "file probably has a different syllable count than this tuned line.\n\n"
                    "The result may be shifted. Export anyway?" % gap):
                return
        default = os.path.splitext(os.path.basename(self.vsqx_path))[0] + "_relyric.vsqx"
        path = filedialog.asksaveasfilename(
            title="Export re-lyriced VSQX", defaultextension=".vsqx", initialfile=default,
            filetypes=[("VOCALOID VSQX", "*.vsqx"), ("All files", "*.*")])
        if not path:
            return
        new_lyrics = [n.lyric for n in self.song.notes]
        try:
            changed = relyric_clip(self.vsqx_path, self.clip.index, new_lyrics, path,
                                   baseline_starts=self.baseline_starts)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Re-lyric failed", str(exc))
            return
        self.status.config(text="Re-lyriced %d note(s) in '%s' → %s."
                                % (changed, self.clip.label, os.path.basename(path)))
        messagebox.showinfo(
            "Re-lyriced",
            "Saved:\n%s\n\nLine: %s\nAll tuning (pitches & note splits) is preserved; the "
            "other vocal lines are untouched.\n\n"
            "In Piapro Studio:\n"
            "1) File > Import > VSQX\n"
            "2) Run Job > Convert phonemes to match language so the new words sing right."
            % (path, self.clip.label))

    # ---- Table + inline lyric editing -------------------------------------
    def _populate(self):
        self._destroy_editor()
        self.tree.delete(*self.tree.get_children())
        tpm = ticks_per_measure(self.song.numerator, self.song.denominator)
        beat_ticks = max(1, tpm // self.song.numerator)
        for i, n in enumerate(self.song.notes):
            bar = n.start // tpm + 1
            beat = (n.start % tpm) // beat_ticks + 1
            self.tree.insert("", "end", values=(i + 1, "%d.%d" % (bar, beat),
                                                 midi_note_name(n.key), n.dur, n.lyric))
        self._draw_piano_roll()

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
        entry = tk.Entry(self.tree, bg=ABYSS, fg=PAPER, insertbackground=ORANGE,
                         relief="flat", highlightthickness=1, highlightbackground=ORANGE,
                         font=self.fonts["body"])
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
        if self.song and 0 <= idx < len(self.song.notes):
            self.song.notes[idx].lyric = value
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
