"""Generate a tiny demo: writes twinkle.mid and converts it to twinkle.vsqx.

Run from anywhere:  python make_twinkle.py
Useful as a smoke test and as a ready-to-import Piapro sample.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # add midi2vsqx/ to the import path

import mido  # noqa: E402
from midi_reader import read_midi  # noqa: E402
from vsqx_writer import write_vsqx  # noqa: E402


def make_midi(path):
    mid = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(120), time=0))
    track.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    pitches = [60, 60, 67, 67, 69, 69, 67]          # C C G G A A G
    durs = [480, 480, 480, 480, 480, 480, 960]
    for key, dur in zip(pitches, durs):
        track.append(mido.Message("note_on", note=key, velocity=90, time=0))
        track.append(mido.Message("note_off", note=key, velocity=0, time=dur))
    mid.save(path)


if __name__ == "__main__":
    midi_path = os.path.join(HERE, "twinkle.mid")
    vsqx_path = os.path.join(HERE, "twinkle.vsqx")
    make_midi(midi_path)
    song = read_midi(midi_path)
    for note, lyric in zip(song.notes, ["きら", "きら", "ひか", "る", "おそ", "らの", "ほし"]):
        note.lyric = lyric
    write_vsqx(song, vsqx_path, seq_name="Twinkle", part_name="Twinkle")
    print("wrote:", midi_path)
    print("wrote:", vsqx_path)
