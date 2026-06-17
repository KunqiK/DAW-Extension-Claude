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

from midi_reader import read_midi, midi_note_name
from vsqx_writer import write_vsqx, ticks_per_measure
from vsqx_reader import read_moras_as_song, relyric_vsqx


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
        self._editor = None     # (Entry, row_iid) while editing a lyric cell

        self._build_ui()
        self._bind_keys()

    # ---- UI construction ---------------------------------------------------
    def _build_ui(self):
        toolbar = ttk.Frame(self, padding=6)
        toolbar.pack(side="top", fill="x")
        ttk.Button(toolbar, text="Open MIDI… (Ctrl+O)", command=self.open_midi).pack(side="left")
        ttk.Button(toolbar, text="Re-lyric tuned VSQX… (Ctrl+R)", command=self.open_tuned_vsqx).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Export VSQX… (Ctrl+S)", command=self.export_vsqx).pack(side="left", padx=(6, 0))
        self.info = ttk.Label(toolbar, text="No file loaded.")
        self.info.pack(side="left", padx=12)

        table = ttk.Frame(self)
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

        self.status = ttk.Label(
            self, relief="sunken", anchor="w", padding=4,
            text="Open a MIDI exported from FL Studio, type a syllable per note (Enter = next note), then Export VSQX.")
        self.status.pack(side="bottom", fill="x")

    def _bind_keys(self):
        self.bind("<Control-o>", lambda e: self.open_midi())
        self.bind("<Control-r>", lambda e: self.open_tuned_vsqx())
        self.bind("<Control-s>", lambda e: self.export_vsqx())

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
        Each row is one mora (a sung syllable); type the new word over it and export."""
        path = filedialog.askopenfilename(
            title="Open a tuned VSQX to re-lyric",
            filetypes=[("VOCALOID VSQX", "*.vsqx"), ("All files", "*.*")])
        if not path:
            return
        try:
            self.song = read_moras_as_song(path)
        except Exception as exc:  # noqa: BLE001 - surface any parse error to the user
            messagebox.showerror("Could not read VSQX", str(exc))
            return
        if not self.song.notes:
            messagebox.showwarning(
                "No moras found",
                "This .vsqx has no sung syllables to re-lyric.\n"
                "(Open the tuned file you exported from Piapro.)")
            return
        self.export_mode = "relyric"
        self.vsqx_path = path
        self.midi_path = path
        self._populate()
        self.info.config(text="%s  —  %d moras, %s BPM, %d/%d  (re-lyric: tuning preserved)" % (
            os.path.basename(path), len(self.song.notes), self.song.bpm,
            self.song.numerator, self.song.denominator))
        self.status.config(
            text="Type the NEW lyric for each mora (Enter = save & next). "
                 "Export keeps every pitch/split you tuned.")
        first = self.tree.get_children()[0]
        self.tree.selection_set(first)
        self.tree.focus(first)

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
            changed = relyric_vsqx(self.vsqx_path, new_lyrics, path)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Re-lyric failed", str(exc))
            return
        self.status.config(text="Re-lyriced %d mora(s) → %s. In Piapro: File > Import > VSQX."
                                % (changed, os.path.basename(path)))
        messagebox.showinfo(
            "Re-lyriced",
            "Saved:\n%s\n\nAll your tuning (pitches & note splits) is preserved.\n\n"
            "In Piapro Studio:\n"
            "1) File > Import > VSQX\n"
            "2) Run Job > Convert phonemes to match language so the new words sing right."
            % path)

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
        entry = tk.Entry(self.tree)
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
