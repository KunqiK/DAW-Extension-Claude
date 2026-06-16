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
;   Ctrl + Shift+wheel = zoom horizontally   <-- the trigger we reuse
;   Ctrl + wheel       = (nothing)           <-- free, so we hijack it
;   Alt  + wheel       = (nothing)
;
; What this script does: while a Piapro Studio window is focused, it turns
; your FL-style Ctrl+wheel into Piapro's Ctrl+Shift+wheel, so Ctrl+wheel
; zooms horizontally just like in FL Studio. It is ACTIVE ONLY in Piapro,
; so FL Studio's own shortcuts are never touched.
;
; Requires AutoHotkey v2  (https://www.autohotkey.com/)
; Repo:    https://github.com/KunqiK/DAW-Extension-Claude
;==============================================================================

SetTitleMatchMode(2)   ; match a window whose title CONTAINS the given text

A_IconTip := "Piapro <-> FL zoom hotkeys (active only in Piapro Studio)"
TrayTip("Ctrl+wheel now zooms horizontally inside Piapro (like FL Studio).",
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

    ; VERTICAL ZOOM — FL uses Alt+wheel. Piapro's vertical-zoom trigger is not
    ; found yet, so this is intentionally left unmapped for now. Once we know
    ; how Piapro zooms vertically, it gets mapped here:
    ; !WheelUp::Send(...)   ; Alt + wheel up   -> zoom IN
    ; !WheelDown::Send(...) ; Alt + wheel down -> zoom OUT

#HotIf   ; end Piapro-only context
