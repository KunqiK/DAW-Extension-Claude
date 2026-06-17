"""Read a Piapro/VOCALOID4 .vsqx, and re-lyric a *tuned* one while keeping the tuning.

Two jobs:
  * read_vsqx(path) -> Song   : parse notes + tempo/time-signature (for display).
  * group_moras / relyric_vsqx: the "change the words, keep the tuning" feature.

WHY RE-LYRIC IS SIMPLE (learned from real Piapro exports):
  When you tune a mora in Piapro you split it into one LEAD note that carries the
  syllable (e.g. 'ら', phoneme '4 a') followed by 'ー' CONTINUATION notes that just
  hold the previous vowel (phoneme '-'). So to put new words on the same melody we
  only change each lead note's lyric — the 'ー' notes follow the new vowel on their
  own, and every pitch / length / split you tuned is left exactly as it was.

HOW WE WRITE IT BACK:
  Not by re-serialising (that would drop Piapro's CDATA + metadata and reformat the
  file). Instead we do a surgical text replacement of just the lead notes' <y> value,
  so the rest of the file is preserved byte-for-byte. The phoneme is left UNLOCKED so
  VOCALOID can re-derive it — after import, run Piapro's
  "Job > Convert phonemes to match language" if a syllable sings the old sound.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List

from midi_reader import Song, Note, VSQ_RESOLUTION

# Lyrics that mean "hold the previous vowel" instead of starting a new syllable.
CONTINUATION_LYRICS = {"ー", "－", "-", ""}


# --- reading -----------------------------------------------------------------
def _local(tag: str) -> str:
    """Tag name without its XML namespace ('{ns}note' -> 'note')."""
    return tag.rsplit("}", 1)[-1]


def _child(el, name):
    if el is not None:
        for c in el:
            if _local(c.tag) == name:
                return c
    return None


def _children(el, name) -> list:
    return [c for c in el if _local(c.tag) == name] if el is not None else []


def _txt(el) -> str:
    return (el.text or "").strip() if el is not None else ""


def _int(el, default: int = 0) -> int:
    try:
        return int(_txt(el))
    except (TypeError, ValueError):
        return default


def _parts(root) -> list:
    parts = []
    for vstrack in _children(root, "vsTrack"):
        parts.extend(_children(vstrack, "vsPart"))
    return parts


def read_vsqx(path: str) -> Song:
    """Parse a .vsqx into a Song. Note positions are song-relative ticks (the
    pre-measure count-in is subtracted), so 0 == the first real bar."""
    root = ET.parse(path).getroot()
    master = _child(root, "masterTrack")
    resolution = _int(_child(master, "resolution"), VSQ_RESOLUTION) or VSQ_RESOLUTION
    pre_measure = _int(_child(master, "preMeasure"), 0)

    nu, de = 4, 4
    timesigs = _children(master, "timeSig")
    if timesigs:  # use the signature that starts at the lowest measure
        ts = min(timesigs, key=lambda e: _int(_child(e, "m"), 0))
        nu = _int(_child(ts, "nu"), 4) or 4
        de = _int(_child(ts, "de"), 4) or 4

    bpm = 120.0
    tempos = _children(master, "tempo")
    if tempos:  # tempo <v> is BPM * 100; use the earliest
        tp = min(tempos, key=lambda e: _int(_child(e, "t"), 0))
        bpm = round(_int(_child(tp, "v"), 12000) / 100.0, 2)

    song = Song(bpm=bpm, numerator=nu, denominator=de,
                source_ppq=resolution, pre_measure=pre_measure)
    pre_ticks = resolution * 4 * nu // de * pre_measure

    # Document order in a Piapro file is time order; keep it (the re-lyric writer
    # below relies on the same order), and group_moras needs leads before their 'ー'.
    for part in _parts(root):
        part_t = _int(_child(part, "t"), 0)
        for ne in _children(part, "note"):
            song.notes.append(Note(
                start=part_t + _int(_child(ne, "t"), 0) - pre_ticks,
                dur=_int(_child(ne, "dur"), 0),
                key=_int(_child(ne, "n"), 60),
                velocity=_int(_child(ne, "v"), 64),
                lyric=_txt(_child(ne, "y")),
                phoneme=_txt(_child(ne, "p")),
            ))
    return song


# --- moras (re-lyric units) --------------------------------------------------
@dataclass
class Mora:
    lyric: str       # the syllable currently on the lead note
    start: int       # song-relative tick of the lead note
    pitch: int       # lead note's MIDI pitch
    dur: int         # total span (lead + its 'ー' continuations)
    note_count: int  # notes making up this mora (1 == untuned)


def group_moras(song: Song) -> List[Mora]:
    """Collapse a tuned note list into one entry per sung syllable."""
    moras: List[Mora] = []
    for n in song.notes:
        if n.lyric not in CONTINUATION_LYRICS:          # real syllable -> new mora
            moras.append(Mora(n.lyric, n.start, n.key, n.dur, 1))
        elif moras:                                     # 'ー' -> extend current mora
            m = moras[-1]
            m.dur = (n.start + n.dur) - m.start
            m.note_count += 1
    return moras


def read_moras_as_song(path: str) -> Song:
    """A Song with one note per mora (for showing tuned files in the lyric table)."""
    src = read_vsqx(path)
    out = Song(bpm=src.bpm, numerator=src.numerator, denominator=src.denominator,
               source_ppq=src.source_ppq, pre_measure=src.pre_measure)
    for m in group_moras(src):
        out.notes.append(Note(m.start, m.dur, m.pitch, 64, m.lyric))
    return out


# --- re-lyric (surgical, tuning-preserving) ----------------------------------
_NOTE_BLOCK = re.compile(r"<note\b.*?</note>", re.DOTALL)
_Y_TAG = re.compile(r"(<y\b[^>]*>)(.*?)(</y>)", re.DOTALL)
_P_LOCK = re.compile(r'(<p\b[^>]*?)\s+lock="1"([^>]*>)')


def _lyric_of(block: str) -> str:
    m = _Y_TAG.search(block)
    if not m:
        return ""
    cdata = re.search(r"<!\[CDATA\[(.*?)\]\]>", m.group(2), re.DOTALL)
    return (cdata.group(1) if cdata else m.group(2)).strip()


def _esc_cdata(text: str) -> str:
    return text.replace("]]>", "]]]]><![CDATA[>")


def count_moras(path: str) -> int:
    text = open(path, encoding="utf-8").read()
    return sum(1 for b in _NOTE_BLOCK.findall(text)
               if _lyric_of(b) not in CONTINUATION_LYRICS)


def relyric_vsqx(in_path: str, new_lyrics: List[str], out_path: str) -> int:
    """Write `in_path` to `out_path` with each mora's lead note re-lyriced to the
    matching entry of `new_lyrics` (one per mora, in order). 'ー' continuation notes
    and every other byte are left untouched, so all tuning is preserved.
    Returns the number of moras changed. Raises ValueError on a count mismatch."""
    leads = count_moras(in_path)
    if len(new_lyrics) != leads:
        raise ValueError(
            "Got %d new lyrics but the file has %d moras (sung syllables)."
            % (len(new_lyrics), leads))

    text = open(in_path, encoding="utf-8").read()
    state = {"i": 0, "changed": 0}

    def replace_note(mo):
        block = mo.group(0)
        if _lyric_of(block) in CONTINUATION_LYRICS:     # a 'ー' note -> leave alone
            return block
        idx = state["i"]
        state["i"] += 1
        new = (new_lyrics[idx] or "").strip()
        if new == "" or new == _lyric_of(block):        # nothing to change
            return block
        block = _Y_TAG.sub(
            lambda m: m.group(1) + "<![CDATA[" + _esc_cdata(new) + "]]>" + m.group(3),
            block, count=1)
        block = _P_LOCK.sub(r"\1\2", block)             # unlock phoneme -> re-derivable
        state["changed"] += 1
        return block

    out = _NOTE_BLOCK.sub(replace_note, text)
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(out)
    return state["changed"]


if __name__ == "__main__":
    import sys

    song = read_vsqx(sys.argv[1])
    moras = group_moras(song)
    print("%d notes -> %d moras | %s BPM | %d/%d | preMeasure %d"
          % (len(song.notes), len(moras), song.bpm, song.numerator,
             song.denominator, song.pre_measure))
    for i, m in enumerate(moras):
        print("  mora %2d  '%s'  pitch=%d  start=%d  span=%d  (%d note%s)"
              % (i, m.lyric, m.pitch, m.start, m.dur, m.note_count,
                 "" if m.note_count == 1 else "s"))
