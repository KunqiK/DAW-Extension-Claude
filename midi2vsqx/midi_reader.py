"""Read a MIDI file into notes + tempo/time-signature, expressed in VSQ4 ticks.

VOCALOID's .vsqx uses a fixed resolution of 480 ticks per quarter note, so we
convert the MIDI file's own PPQ to 480 here. Note positions are 0-based from the
start of the song (the pre-measure count-in is added later by the writer).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Tuple

import mido

VSQ_RESOLUTION = 480  # VSQ4 ticks per quarter note (fixed by the format)

_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def midi_note_name(key: int) -> str:
    """MIDI note number -> name, e.g. 60 -> 'C4' (Yamaha/`middle C = C3` differs;
    we use the common MIDI convention where 60 = C4)."""
    return f"{_NOTE_NAMES[key % 12]}{key // 12 - 1}"


@dataclass
class Note:
    start: int          # tick (VSQ 480 PPQ), 0-based from song start
    dur: int            # length in ticks
    key: int            # MIDI note number 0..127
    velocity: int       # 0..127
    lyric: str = ""     # filled in by the user in the GUI


@dataclass
class Song:
    notes: List[Note] = field(default_factory=list)
    bpm: float = 120.0
    numerator: int = 4
    denominator: int = 4
    source_ppq: int = 480

    @property
    def duration_ticks(self) -> int:
        return max((n.start + n.dur for n in self.notes), default=0)


def read_midi(path: str) -> Song:
    """Parse a Standard MIDI File into a Song with notes in VSQ (480 PPQ) ticks.

    All tracks are merged onto one timeline; the first tempo and time signature
    encountered are used (multi-tempo support is a future enhancement).
    """
    mid = mido.MidiFile(path)
    ppq = mid.ticks_per_beat or VSQ_RESOLUTION
    song = Song(source_ppq=ppq)

    have_tempo = False
    have_timesig = False
    open_notes: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}
    raw: List[Tuple[int, int, int, int]] = []  # (start, end, key, velocity)

    abs_tick = 0
    for msg in mido.merge_tracks(mid.tracks):
        abs_tick += msg.time
        if msg.type == "set_tempo" and not have_tempo:
            song.bpm = round(mido.tempo2bpm(msg.tempo), 2)
            have_tempo = True
        elif msg.type == "time_signature" and not have_timesig:
            song.numerator = msg.numerator
            song.denominator = msg.denominator
            have_timesig = True
        elif msg.type == "note_on" and msg.velocity > 0:
            open_notes.setdefault((msg.channel, msg.note), []).append((abs_tick, msg.velocity))
        elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
            stack = open_notes.get((msg.channel, msg.note))
            if stack:
                start_tick, vel = stack.pop(0)
                raw.append((start_tick, abs_tick, msg.note, vel))

    def to_vsq(t: int) -> int:
        return round(t * VSQ_RESOLUTION / ppq)

    for start, end, key, vel in sorted(raw):
        s = to_vsq(start)
        dur = max(1, to_vsq(end) - s)
        song.notes.append(Note(start=s, dur=dur, key=key, velocity=vel))

    return song


if __name__ == "__main__":
    import sys

    song = read_midi(sys.argv[1])
    print(f"{len(song.notes)} notes | {song.bpm} BPM | "
          f"{song.numerator}/{song.denominator} | source PPQ {song.source_ppq}")
    for i, n in enumerate(song.notes[:20]):
        print(f"  {i:>3}  t={n.start:<6} dur={n.dur:<5} {midi_note_name(n.key):<4} vel={n.velocity}")
