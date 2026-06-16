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

#HotIf   ; end Piapro-only context

; Temporary diagnostic helper for vertical zoom (removed once confirmed working).
; The held Alt would otherwise taint the combo (Piapro would see Ctrl+Shift+Alt+]),
; so we release Alt, send a clean Ctrl+Shift+bracket with a real key-press
; duration, then restore Alt so repeated scrolling keeps firing.
VZoom(bracketKey, label) {
    altDown := GetKeyState("Alt", "P")       ; is the user physically holding Alt?
    SetKeyDelay(10, 30)                       ; 30 ms press duration (Event mode)
    SendEvent("{Alt up}")                     ; clear Alt so the combo is clean
    SendEvent("^+" . bracketKey)              ; Ctrl + Shift + bracket (by scan code)
    if (altDown)
        SendEvent("{Alt down}")               ; restore Alt to match the physical hold
    ToolTip("vertical zoom " . label . "  (Alt was " . (altDown ? "DOWN" : "up") . ")")
    SetTimer(() => ToolTip(), -1200)          ; auto-clear the tooltip
}
