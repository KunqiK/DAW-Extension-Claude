"""MIDI -> VSQX lyric tool — a small desktop app.

Workflow: in FL Studio, export your melody as a MIDI file. Open it here, type one
syllable per note (Enter jumps to the next note), then Export VSQX and import that
into Piapro Studio (File > Import > VSQX).

Run:  python app.py      (needs Python 3.9+ and `pip install mido`)
"""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from midi_reader import read_midi, midi_note_name, Song, Note
from vsqx_writer import write_vsqx, ticks_per_measure
from vsqx_reader import read_clips, moras_of, relyric_clip, read_vsqx, is_continuation

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


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MIDI → VSQX Lyric Tool")
        self.geometry("780x540")
        self.minsize(620, 360)

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
        self._editor = None     # (Entry, row_iid) while editing a lyric cell

        self._apply_theme()
        self._build_ui()
        self._bind_keys()

    # ---- theme -------------------------------------------------------------
    def _apply_theme(self):
        """Dark-plum / orange 'Ina' theme via the ttk 'clam' base."""
        self.configure(bg=PLUM)
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=PLUM, foreground=PAPER, fieldbackground=ABYSS,
                        bordercolor=PURPLE, font=("Segoe UI", 9))
        style.configure("TFrame", background=PLUM)
        style.configure("TLabel", background=PLUM, foreground=PAPER)
        style.configure("Info.TLabel", background=PLUM, foreground=ORANGE,
                        font=("Segoe UI", 9, "bold"))
        style.configure("Status.TLabel", background=PURPLE, foreground=PAPER)
        style.configure("TButton", background=ORANGE, foreground=INK, borderwidth=0,
                        focuscolor=PLUM, padding=(10, 5), font=("Segoe UI", 9, "bold"))
        style.map("TButton", background=[("active", LILAC), ("pressed", PURPLE)],
                  foreground=[("active", INK), ("pressed", PAPER)])
        style.configure("Treeview", background=ABYSS, fieldbackground=ABYSS,
                        foreground=PAPER, rowheight=24, borderwidth=0)
        style.configure("Treeview.Heading", background=PURPLE, foreground=PAPER,
                        relief="flat", font=("Segoe UI", 9, "bold"))
        style.map("Treeview.Heading", background=[("active", PLUM)])
        style.map("Treeview", background=[("selected", ORANGE)],
                  foreground=[("selected", INK)])
        style.configure("TScrollbar", background=PLUM, troughcolor=ABYSS,
                        bordercolor=PLUM, arrowcolor=PAPER)

    # ---- UI construction ---------------------------------------------------
    def _build_ui(self):
        toolbar = ttk.Frame(self, padding=8)
        toolbar.pack(side="top", fill="x")
        for text, cmd in (("Open MIDI… (Ctrl+O)", self.open_midi),
                          ("Re-lyric tuned VSQX… (Ctrl+R)", self.open_tuned_vsqx),
                          ("+ un-tuned (exact splits)…", self.open_baseline),
                          ("Export VSQX… (Ctrl+S)", self.export_vsqx)):
            ttk.Button(toolbar, text=text, command=cmd).pack(side="left", padx=(0, 6))
        self.info = ttk.Label(toolbar, text="No file loaded.", style="Info.TLabel")
        self.info.pack(side="left", padx=10)

        # piano-roll visualizer (notes over time × pitch)
        roll = ttk.Frame(self, padding=(8, 8, 8, 0))
        roll.pack(side="top", fill="x")
        self.canvas = tk.Canvas(roll, height=190, bg=INK, highlightthickness=1,
                                highlightbackground=PURPLE)
        hsb = ttk.Scrollbar(roll, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=hsb.set)
        self.canvas.pack(side="top", fill="x")
        hsb.pack(side="top", fill="x")
        self.canvas.bind("<Configure>", lambda e: self._draw_piano_roll())

        # lyric table
        table = ttk.Frame(self, padding=(8, 8, 8, 0))
        table.pack(side="top", fill="both", expand=True)
        cols = ("idx", "bar", "pitch", "dur", "lyric")
        self.tree = ttk.Treeview(table, columns=cols, show="headings", selectmode="browse")
        widths = {"idx": 44, "bar": 80, "pitch": 80, "dur": 80, "lyric": 440}
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
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._highlight_selection())

        self.status = ttk.Label(
            self, relief="flat", anchor="w", padding=6, style="Status.TLabel",
            text="Open a MIDI exported from FL Studio, type a syllable per note (Enter = next note), then Export VSQX.")
        self.status.pack(side="bottom", fill="x")
        self._draw_piano_roll()      # show the empty-state placeholder

    def _bind_keys(self):
        self.bind("<Control-o>", lambda e: self.open_midi())
        self.bind("<Control-r>", lambda e: self.open_tuned_vsqx())
        self.bind("<Control-s>", lambda e: self.export_vsqx())

    # ---- piano-roll visualizer --------------------------------------------
    _PPT = 0.06       # pixels per tick (~115 px per 4/4 bar)

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
            c.create_text(14, 14, anchor="nw", fill=PURPLE, font=("Segoe UI", 10),
                          text="♪  piano-roll — open a MIDI or a tuned VSQX")
            return
        H, pad = int(c.cget("height")), 16
        keys = [n.key for n in notes]
        kmin, kmax = min(keys), max(keys)
        row_h = max(3.0, min(12.0, (H - 2 * pad) / (kmax - kmin + 1)))
        t0 = min(n.start for n in notes)              # left edge = first note's bar
        tpm = ticks_per_measure(self.song.numerator, self.song.denominator) if self.song else 1920
        t0 = (t0 // tpm) * tpm if tpm else t0
        self._roll_t0 = t0
        end = max(n.start + n.dur for n in notes)
        width = int((end - t0) * self._PPT) + 2 * pad
        c.configure(scrollregion=(0, 0, max(width, c.winfo_width()), H))

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
                              font=("Segoe UI", 8), text=n.lyric)

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
        self.status.config(text="Type a syllable per note. Enter = save & next note. Then Export VSQX.")
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
        self._show_clip(match, hdr, by_mora=False)       # one row per ORIGINAL syllable
        self.info.config(text="%s + un-tuned %s  —  %d syllables (exact splits)" % (
            os.path.basename(self.vsqx_path), os.path.basename(path), len(match.notes)))
        self.status.config(
            text="Using the un-tuned file for exact splits. Type new lyrics; export keeps "
                 "all tuning.")

    def _show_clip(self, clip, hdr, by_mora=True):
        """Load a clip into the table — one row per mora (by_mora) or per note."""
        song = Song(bpm=hdr.bpm, numerator=hdr.numerator,
                    denominator=hdr.denominator, pre_measure=hdr.pre_measure)
        if by_mora:
            for m in moras_of(clip.notes):
                song.notes.append(Note(m.start, m.dur, m.pitch, 64, m.lyric))
        else:
            for n in clip.notes:
                song.notes.append(Note(n.start, n.dur, n.key, 64, n.lyric))
        self.song = song
        self.draw_notes = list(clip.notes)        # the piano-roll shows the real notes
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
                         font=("Segoe UI", 9))
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
                         font=("Segoe UI", 10))
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
