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
    ; NO {Blind} here: we want to DROP the held Alt and send a clean Ctrl+Shift+key.
    ; (AHK's default Send releases the physical Alt during the send, then restores
    ;  it, so Piapro sees Ctrl+Shift+] without Alt — and repeated scrolling works.)
    !WheelUp::Send("^+]")     ; Alt + wheel up   -> Ctrl+Shift+]  -> vertical zoom IN
    !WheelDown::Send("^+[")   ; Alt + wheel down -> Ctrl+Shift+[  -> vertical zoom OUT

#HotIf   ; end Piapro-only context
