#Requires AutoHotkey v2.0
#SingleInstance Force
;==============================================================================
; PiaproFLHotkeys.ahk  —  make Piapro Studio zoom like FL Studio
;
; FL Studio gestures:   Ctrl + wheel = zoom HORIZONTAL
;                       Alt  + wheel = zoom VERTICAL
;
; Piapro Studio (for Miku V4 / V4X) native gestures:
;   plain wheel        = scroll vertically
;   Shift + wheel      = scroll horizontally
;   Ctrl + Shift + wheel  = zoom horizontally  <-- reused for FL Ctrl+wheel
;   Ctrl + Shift + ] / [  = zoom vertically    <-- reused for FL Alt+wheel
;   Ctrl + wheel          = (nothing)          <-- free, so we hijack it
;   Alt  + wheel          = (nothing)          <-- free, so we hijack it
;
; What this script does: while a Piapro Studio window is focused, it maps
; your FL-style gestures onto Piapro's real zoom triggers:
;   Ctrl + wheel -> Ctrl+Shift+wheel   (horizontal zoom)
;   Alt  + wheel -> Ctrl+Shift+] / [   (vertical zoom)
; It is ACTIVE ONLY in Piapro, so FL Studio's own shortcuts are never touched.
;
; Requires AutoHotkey v2  (https://www.autohotkey.com/)
; Repo:    https://github.com/KunqiK/DAW-Extension-Claude
;==============================================================================

SetTitleMatchMode(2)   ; match a window whose title CONTAINS the given text

A_IconTip := "Piapro <-> FL zoom hotkeys (active only in Piapro Studio)"
TrayTip("In Piapro: Ctrl+wheel = horizontal zoom, Alt+wheel = vertical zoom (like FL Studio).",
        "Piapro FL hotkeys loaded")

; --- These remaps fire ONLY while a 'Piapro Studio' window is active ----------
; "Piapro Studio" also matches FL's wrapper title "Piapro Studio VSTi (Master)",
; but never matches the FL Studio main window.
#HotIf WinActive("Piapro Studio")

    ; HORIZONTAL ZOOM — FL uses Ctrl+wheel; Piapro uses Ctrl+Shift+wheel.
    ; {Blind} keeps your physically-held Ctrl down and just adds Shift,
    ; so Ctrl+wheel is delivered to Piapro as Ctrl+Shift+wheel.
    ; (Plain Ctrl+wheel does nothing in Piapro, so nothing is lost.)
    ; A bare ^WheelUp does NOT fire when you also hold Shift yourself, so your
    ; manual Ctrl+Shift+wheel still passes straight through.
    ^WheelUp::Send("{Blind}+{WheelUp}")     ; Ctrl + wheel up   -> zoom IN
    ^WheelDown::Send("{Blind}+{WheelDown}") ; Ctrl + wheel down -> zoom OUT

    ; VERTICAL ZOOM — FL uses Alt+wheel; Piapro uses Ctrl+Shift+] / Ctrl+Shift+[.
    ; Brackets are sent by SCAN CODE (sc01B = "]", sc01A = "[") so a held Shift
    ; can't turn them into } / { — Piapro reads key+modifiers, so it sees the real
    ; Ctrl+Shift+] / [. AHK auto-releases the hotkey's Alt during the Send.
    ; (The ToolTip is a TEMPORARY diagnostic to confirm the hotkey is firing.)
    !WheelUp::VZoom("{sc01B}", "IN")     ; Alt + wheel up   -> Ctrl+Shift+]
    !WheelDown::VZoom("{sc01A}", "OUT")  ; Alt + wheel down -> Ctrl+Shift+[

    ; DIAGNOSTIC test keys: press F8 / F9 in Piapro to fire a CLEAN Ctrl+Shift+] / [
    ; with NO Alt and NO wheel. If F8/F9 zoom vertically but Alt+wheel doesn't, the
    ; problem is the Alt/wheel handling. If F8/F9 also do nothing, Piapro is ignoring
    ; the synthetic keystroke and we need a different approach.
    F8::VZoomTest("{sc01B}", "IN")
    F9::VZoomTest("{sc01A}", "OUT")

#HotIf   ; end Piapro-only context

; --- Vertical-zoom senders (temporary diagnostics: tooltips + F8/F9 test keys) ---
; Alt+wheel path: ONE atomic SendInput drops the held Alt, sends a clean
; Ctrl+Shift+bracket, then restores Alt. Because SendInput is atomic, a physical
; wheel notch can't leak in mid-send (that leak previously produced a stray
; Ctrl+Shift+wheel = horizontal zoom).
VZoom(bracket, label) {
    Send("{Alt up}^+" bracket "{Alt down}")
    Tip("Alt+wheel  ->  Ctrl+Shift+" (label == "IN" ? "]" : "[") "   (vertical " label ")")
}
; F8/F9 path: a CLEAN Ctrl+Shift+bracket with no Alt and no wheel, to test whether
; Piapro accepts the synthetic keystroke at all.
VZoomTest(bracket, label) {
    Send("^+" bracket)
    Tip("F-key test  ->  Ctrl+Shift+" (label == "IN" ? "]" : "[") "   (vertical " label ")")
}
Tip(text) {
    ToolTip(text)
    SetTimer(() => ToolTip(), -1100)          ; auto-clear the tooltip
}
