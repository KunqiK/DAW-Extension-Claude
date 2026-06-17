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

# A tuning "tail" note holds the previous syllable's vowel instead of starting a new
# one. Piapro writes tails either as 'ー' (chōonpu) OR as the bare vowel itself — in
# kana (あいうえお) or romaji (a/i/u/e/o). Examples seen in real exports:
#   ら ー ー ー   (chōonpu style)        ke e e e   (bare-vowel style)
_PROLONG_MARKS = {"ー", "－", "-", ""}            # 'hold' markers (no vowel of their own)
_BARE_VOWELS = set("aiueoAIUEO") | set("あいうえおアイウエオ")

# Each kana's vowel (the last char of a syllable decides it: しゃ -> a, きょ -> o).
_KANA_VOWEL = {}
for _chars, _v in (
    ("あぁかがさざただなはばぱまやゃらわゎアァカガサザタダナハバパマヤャラワヮ", "a"),
    ("いぃきぎしじちぢにひびぴみりイィキギシジチヂニヒビピミリ", "i"),
    ("うぅくぐすずつづぬふぶぷむゆゅるゔウゥクグスズツヅヌフブプムユュルヴ", "u"),
    ("えぇけげせぜてでねへべぺめれエェケゲセゼテデネヘベペメレ", "e"),
    ("おぉこごそぞとどのほぼぽもよょろをオォコゴソゾトドノホボポモヨョロヲ", "o"),
):
    for _c in _chars:
        _KANA_VOWEL[_c] = _v


def is_continuation(lyric: str) -> bool:
    """True if this note continues the previous syllable (a 'ー' or a bare vowel)
    rather than starting a new one."""
    s = (lyric or "").strip()
    return s in _PROLONG_MARKS or s in _BARE_VOWELS


def vowel_of(lyric: str):
    """The vowel ('a'/'i'/'u'/'e'/'o') of a syllable, or None (e.g. 'ん' / 'n')."""
    s = (lyric or "").strip()
    if not s:
        return None
    if s.isascii():                       # romaji: the last vowel letter (ra->a, kyo->o)
        for ch in reversed(s.lower()):
            if ch in "aiueo":
                return ch
        return None
    for ch in reversed(s):                # kana: the last char that carries a vowel
        if ch in _KANA_VOWEL:
            return _KANA_VOWEL[ch]
    return None


def _vowel_tail(new_mora: str, vowel: str):
    """The bare-vowel lyric for a tail note, in the same script (kana/romaji) as
    `new_mora`, so the whole syllable stays consistent."""
    if vowel is None:
        return None
    if (new_mora or "").strip().isascii():
        return vowel                      # romaji 'a'/'e'/...
    return {"a": "あ", "i": "い", "u": "う", "e": "え", "o": "お"}[vowel]


# Small kana / prolong marks that attach to the preceding base kana.
_SMALL_KANA = set("ゃゅょゎぁぃぅぇぉャュョヮァィゥェォ") | {"ー", "－"}


def split_kana_moras(text: str):
    """Split a continuous kana string into moras — a base kana plus any following small
    kana or 'ー' (きゃ stays one mora). Whitespace separates and is dropped; non-kana
    characters each become their own token. Used for batch lyric entry."""
    moras = []
    for ch in text:
        if ch.isspace():
            continue
        if moras and ch in _SMALL_KANA:
            moras[-1] += ch
        else:
            moras.append(ch)
    return moras


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


def moras_of(notes) -> List[Mora]:
    """Group a note list into one entry per sung syllable. A note continues the current
    mora when it's a 'ー' or a bare vowel; otherwise it starts a new one. (The very first
    note always starts a mora, even if it is a bare vowel.)"""
    moras: List[Mora] = []
    for n in notes:
        if moras and is_continuation(n.lyric):          # tail -> extend current mora
            m = moras[-1]
            m.dur = (n.start + n.dur) - m.start
            m.note_count += 1
        else:                                           # new sung syllable -> new mora
            moras.append(Mora(n.lyric, n.start, n.key, n.dur, 1))
    return moras


def group_moras(song: Song) -> List[Mora]:
    """Collapse a tuned Song into one entry per sung syllable."""
    return moras_of(song.notes)


def read_moras_as_song(path: str) -> Song:
    """A Song with one note per mora (for showing tuned files in the lyric table)."""
    src = read_vsqx(path)
    out = Song(bpm=src.bpm, numerator=src.numerator, denominator=src.denominator,
               source_ppq=src.source_ppq, pre_measure=src.pre_measure)
    for m in group_moras(src):
        out.notes.append(Note(m.start, m.dur, m.pitch, 64, m.lyric))
    return out


# --- clips (a vsqx can hold several vocal lines / parts) ---------------------
@dataclass
class Clip:
    track_name: str
    part_name: str
    index: int          # 0-based position among ALL vsParts, in document order
    start: int          # song-relative tick of the part
    notes: List[Note]   # this part's notes (song-relative starts), document order

    @property
    def label(self) -> str:
        part = self.part_name or ("part %d" % (self.index + 1))
        return "%s  —  %s" % (self.track_name or "Track", part)


def read_clips(path: str) -> List[Clip]:
    """Every singing part in the file, one Clip each, in document order. (A 3-track
    file with one part each yields 3 clips; a track with two parts yields two.)"""
    root = ET.parse(path).getroot()
    master = _child(root, "masterTrack")
    resolution = _int(_child(master, "resolution"), VSQ_RESOLUTION) or VSQ_RESOLUTION
    pre_measure = _int(_child(master, "preMeasure"), 0)
    nu, de = 4, 4
    timesigs = _children(master, "timeSig")
    if timesigs:
        ts = min(timesigs, key=lambda e: _int(_child(e, "m"), 0))
        nu = _int(_child(ts, "nu"), 4) or 4
        de = _int(_child(ts, "de"), 4) or 4
    pre_ticks = resolution * 4 * nu // de * pre_measure

    clips: List[Clip] = []
    for vstrack in _children(root, "vsTrack"):
        tname = _txt(_child(vstrack, "name"))
        for part in _children(vstrack, "vsPart"):
            part_t = _int(_child(part, "t"), 0)
            notes = [Note(
                start=part_t + _int(_child(ne, "t"), 0) - pre_ticks,
                dur=_int(_child(ne, "dur"), 0),
                key=_int(_child(ne, "n"), 60),
                velocity=_int(_child(ne, "v"), 64),
                lyric=_txt(_child(ne, "y")),
                phoneme=_txt(_child(ne, "p")),
            ) for ne in _children(part, "note")]
            clips.append(Clip(tname, _txt(_child(part, "name")),
                              len(clips), part_t - pre_ticks, notes))
    return clips


# --- re-lyric (surgical, tuning-preserving) ----------------------------------
_NOTE_BLOCK = re.compile(r"<note\b.*?</note>", re.DOTALL)
_VSPART_BLOCK = re.compile(r"<vsPart\b.*?</vsPart>", re.DOTALL)
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
    """Number of sung syllables (lead notes), matching group_moras()."""
    count, have_mora = 0, False
    for b in _NOTE_BLOCK.findall(open(path, encoding="utf-8").read()):
        if have_mora and is_continuation(_lyric_of(b)):
            continue
        count += 1
        have_mora = True
    return count


def _set_lyric_block(block: str, value: str) -> str:
    """Set a note block's <y> to `value` (CDATA) and unlock its phoneme so the editor
    re-derives pronunciation."""
    block = _Y_TAG.sub(
        lambda m: m.group(1) + "<![CDATA[" + _esc_cdata(value) + "]]>" + m.group(3),
        block, count=1)
    return _P_LOCK.sub(r"\1\2", block)


def _mora_index_by_baseline(start: int, baseline_starts: List[int]) -> int:
    """Index of the un-tuned mora whose span contains `start` (the last baseline note
    beginning at or before it). `baseline_starts` must be sorted ascending."""
    idx = 0
    for j, s in enumerate(baseline_starts):
        if start >= s:
            idx = j
        else:
            break
    return idx


def plan_relyric(notes, new_lyrics, baseline_starts=None):
    """Decide the new lyric for each note (document order); None == leave unchanged.

    Notes are grouped into moras either by `baseline_starts` (sorted song-relative start
    ticks of the un-tuned moras — exact, and removes the bare-vowel ambiguity) or, when
    that's None, by the 'ー'/bare-vowel heuristic. Per mora the first note (the lead) gets
    the new syllable; tails follow it — 'ー' tails stay 'ー', bare-vowel tails become the
    new syllable's vowel (ke→ra turns its 'e' tails into 'a'). Raises ValueError if the
    number of new lyrics doesn't match the mora count."""
    if baseline_starts is not None:
        nmora = len(baseline_starts)
        mora_of = [_mora_index_by_baseline(n.start, baseline_starts) for n in notes]
    else:
        mora_of, cur, have = [], -1, False
        for n in notes:
            if have and is_continuation(n.lyric):
                mora_of.append(cur)
            else:
                cur += 1
                have = True
                mora_of.append(cur)
        nmora = cur + 1

    if len(new_lyrics) != nmora:
        raise ValueError(
            "Got %d new lyrics but the file has %d moras (sung syllables)."
            % (len(new_lyrics), nmora))

    plan = [None] * len(notes)
    seen = set()
    for i, n in enumerate(notes):
        m = mora_of[i]
        new = (new_lyrics[m] or "").strip()
        if m not in seen:                               # lead note of this mora
            seen.add(m)
            if new and new != n.lyric.strip():
                plan[i] = new
        elif n.lyric.strip() not in _PROLONG_MARKS:     # bare-vowel tail -> new vowel
            tail = _vowel_tail(new, vowel_of(new))
            if tail and tail != n.lyric.strip():
                plan[i] = tail
    return plan


def unmapped_moras(notes, baseline_starts) -> int:
    """How many baseline moras receive NO tuned notes — a sign the un-tuned file doesn't
    line up with the tuned one (e.g. their syllable counts differ). 0 == clean fit."""
    if not baseline_starts:
        return 0
    hit = {_mora_index_by_baseline(n.start, baseline_starts) for n in notes}
    return len(baseline_starts) - len(hit)


def relyric_vsqx(in_path: str, new_lyrics: List[str], out_path: str,
                 baseline_path: str = None) -> int:
    """Write `in_path` to `out_path` re-lyriced to `new_lyrics` (one per mora, in order),
    preserving all tuning (pitches/lengths/splits) and unlocking phonemes for re-derivation.
    If `baseline_path` (the un-tuned version) is given, syllable boundaries come from it by
    timing — exact even when a tuning tail shares the next syllable's vowel. Returns the
    number of notes changed; raises ValueError on a mora-count mismatch."""
    notes = read_vsqx(in_path).notes
    baseline_starts = None
    if baseline_path:
        baseline_starts = sorted(n.start for n in read_vsqx(baseline_path).notes)
    plan = plan_relyric(notes, new_lyrics, baseline_starts)

    text = open(in_path, encoding="utf-8").read()
    st = {"i": 0, "changed": 0}

    def replace_note(mo):
        block = mo.group(0)
        value = plan[st["i"]] if st["i"] < len(plan) else None
        st["i"] += 1
        if value is not None:
            block = _set_lyric_block(block, value)
            st["changed"] += 1
        return block

    out = _NOTE_BLOCK.sub(replace_note, text)
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(out)
    return st["changed"]


def relyric_clip(in_path: str, clip_index: int, new_lyrics: List[str], out_path: str,
                 baseline_starts=None) -> int:
    """Like relyric_vsqx, but re-lyric ONLY the clip at `clip_index` (its vsPart), leaving
    every other vocal line in the file untouched. The whole file is written out with just
    that one line changed. `baseline_starts` (sorted song-relative starts of the un-tuned
    version of THIS clip) is optional and disambiguates splits as before."""
    clips = read_clips(in_path)
    if not 0 <= clip_index < len(clips):
        raise ValueError("clip_index %d out of range (file has %d parts)"
                         % (clip_index, len(clips)))
    plan = plan_relyric(clips[clip_index].notes, new_lyrics, baseline_starts)

    text = open(in_path, encoding="utf-8").read()
    parts = list(_VSPART_BLOCK.finditer(text))      # same order as read_clips
    target = parts[clip_index]
    st = {"i": 0, "changed": 0}

    def replace_note(mo):
        block = mo.group(0)
        value = plan[st["i"]] if st["i"] < len(plan) else None
        st["i"] += 1
        if value is not None:
            block = _set_lyric_block(block, value)
            st["changed"] += 1
        return block

    new_part = _NOTE_BLOCK.sub(replace_note, target.group(0))
    out = text[:target.start()] + new_part + text[target.end():]
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(out)
    return st["changed"]


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
