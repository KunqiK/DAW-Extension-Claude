"""Write a Song (from midi_reader) to a VOCALOID4 .vsqx file Piapro Studio imports.

The structure mirrors a known-good VSQ4 template (verified against UtaFormatix3):
  * resolution is always 480; tempo is stored as BPM x 100
  * the musical part starts at the pre-measure offset (`part <t>`)
  * each note's <t> is 0-based from the song start
  * <y> is the lyric (CDATA), <p> is the phoneme (CDATA, left UNLOCKED so Piapro
    can re-derive it from the lyric via "Job -> Convert phonemes to match language")
"""
from __future__ import annotations

from typing import Optional

from midi_reader import Song, VSQ_RESOLUTION

BPM_RATE = 100              # tempo is stored as bpm * 100
DEFAULT_PRE_MEASURE = 4     # count-in measures before the song
DEFAULT_LYRIC = "あ"        # placeholder for notes with no lyric typed (Japanese 'a')
DEFAULT_PHONEME = "a"       # neutral phoneme; unlocked so Piapro can re-derive


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _cdata(text: str) -> str:
    """Wrap text in a CDATA section, neutralising any literal ']]>'."""
    safe = (text or "").replace("]]>", "]]]]><![CDATA[>")
    return "<![CDATA[" + safe + "]]>"


def ticks_per_measure(numerator: int, denominator: int) -> int:
    """Ticks in one measure at 480 PPQ. A whole note = 480 * 4 ticks."""
    return VSQ_RESOLUTION * 4 * numerator // denominator


def build_vsqx(
    song: Song,
    *,
    pre_measure: int = DEFAULT_PRE_MEASURE,
    track_name: str = "Track",
    part_name: str = "MIDI Import",
    seq_name: str = "Untitled",
    default_lyric: str = DEFAULT_LYRIC,
    default_phoneme: str = DEFAULT_PHONEME,
) -> str:
    """Return the full .vsqx document as a string."""
    pre_measure = max(1, pre_measure)
    tpm = ticks_per_measure(song.numerator, song.denominator)
    part_t = tpm * pre_measure

    notes_xml = []
    for n in song.notes:
        notes_xml.append(_NOTE.format(
            t=n.start,
            dur=max(1, n.dur),
            n=_clamp(n.key, 0, 127),
            v=_clamp(n.velocity, 0, 127),
            y=_cdata(n.lyric or default_lyric),
            p=_cdata(default_phoneme),
        ))
    play_time = song.duration_ticks + tpm  # part length, padded by one measure

    return _DOC.format(
        seq_name=_xml_text(seq_name),
        pre_measure=pre_measure,
        nu=song.numerator,
        de=song.denominator,
        tempo_v=int(round(song.bpm * BPM_RATE)),
        track_name=_xml_text(track_name),
        part_t=part_t,
        play_time=play_time,
        part_name=_xml_text(part_name),
        notes="\n".join(notes_xml),
    )


def write_vsqx(song: Song, path: str, **kwargs) -> None:
    """Build and write the .vsqx file (UTF-8, no BOM)."""
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(build_vsqx(song, **kwargs))


def _xml_text(text: str) -> str:
    """These values also go inside CDATA in the template, so just guard ']]>'."""
    return (text or "").replace("]]>", "]]]]><![CDATA[>")


# --- Templates (verified VSQ4 structure) ------------------------------------

_NOTE = """\
            <note>
                <t>{t}</t>
                <dur>{dur}</dur>
                <n>{n}</n>
                <v>{v}</v>
                <y>{y}</y>
                <p>{p}</p>
                <nStyle>
                    <v id="accent">50</v>
                    <v id="bendDep">0</v>
                    <v id="bendLen">0</v>
                    <v id="decay">50</v>
                    <v id="fallPort">0</v>
                    <v id="opening">127</v>
                    <v id="risePort">0</v>
                    <v id="vibLen">0</v>
                    <v id="vibType">0</v>
                </nStyle>
            </note>"""

_DOC = """\
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<vsq4 xmlns="http://www.yamaha.co.jp/vocaloid/schema/vsq4/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.yamaha.co.jp/vocaloid/schema/vsq4/ vsq4.xsd">
    <vender><![CDATA[Yamaha corporation]]></vender>
    <version><![CDATA[4.0.0.3]]></version>
    <vVoiceTable>
        <vVoice>
            <bs>0</bs>
            <pc>0</pc>
            <id><![CDATA[BCXDC6CZLSZHZCB4]]></id>
            <name><![CDATA[VY2V3]]></name>
            <vPrm>
                <bre>0</bre>
                <bri>0</bri>
                <cle>0</cle>
                <gen>0</gen>
                <ope>0</ope>
            </vPrm>
        </vVoice>
    </vVoiceTable>
    <mixer>
        <masterUnit>
            <oDev>0</oDev>
            <rLvl>0</rLvl>
            <vol>0</vol>
        </masterUnit>
        <vsUnit>
            <tNo>0</tNo>
            <iGin>0</iGin>
            <sLvl>-898</sLvl>
            <sEnable>0</sEnable>
            <m>0</m>
            <s>0</s>
            <pan>64</pan>
            <vol>0</vol>
        </vsUnit>
        <monoUnit>
            <iGin>0</iGin>
            <sLvl>-898</sLvl>
            <sEnable>0</sEnable>
            <m>0</m>
            <s>0</s>
            <pan>64</pan>
            <vol>0</vol>
        </monoUnit>
        <stUnit>
            <iGin>0</iGin>
            <m>0</m>
            <s>0</s>
            <vol>-129</vol>
        </stUnit>
    </mixer>
    <masterTrack>
        <seqName><![CDATA[{seq_name}]]></seqName>
        <comment><![CDATA[Converted from MIDI]]></comment>
        <resolution>480</resolution>
        <preMeasure>{pre_measure}</preMeasure>
        <timeSig>
            <m>0</m>
            <nu>{nu}</nu>
            <de>{de}</de>
        </timeSig>
        <tempo>
            <t>0</t>
            <v>{tempo_v}</v>
        </tempo>
    </masterTrack>
    <vsTrack>
        <tNo>0</tNo>
        <name><![CDATA[{track_name}]]></name>
        <comment><![CDATA[Track]]></comment>
        <vsPart>
            <t>{part_t}</t>
            <playTime>{play_time}</playTime>
            <name><![CDATA[{part_name}]]></name>
            <comment><![CDATA[New Musical Part]]></comment>
            <sPlug>
                <id><![CDATA[ACA9C502-A04B-42b5-B2EB-5CEA36D16FCE]]></id>
                <name><![CDATA[VOCALOID2 Compatible Style]]></name>
                <version><![CDATA[3.0.0.1]]></version>
            </sPlug>
            <pStyle>
                <v id="accent">50</v>
                <v id="bendDep">8</v>
                <v id="bendLen">0</v>
                <v id="decay">50</v>
                <v id="fallPort">0</v>
                <v id="opening">127</v>
                <v id="risePort">0</v>
            </pStyle>
            <singer>
                <t>0</t>
                <bs>0</bs>
                <pc>0</pc>
            </singer>
{notes}
            <plane>0</plane>
        </vsPart>
    </vsTrack>
    <monoTrack>
    </monoTrack>
    <stTrack>
    </stTrack>
    <aux>
        <id><![CDATA[AUX_VST_HOST_CHUNK_INFO]]></id>
        <content><![CDATA[VlNDSwAAAAADAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=]]></content>
    </aux>
</vsq4>
"""
