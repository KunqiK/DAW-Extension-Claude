#Requires AutoHotkey v2.0
#SingleInstance Force
;==============================================================================
; PiaproFLHotkeys.ahk  —  make Piapro Studio zoom like FL Studio   (v0.5)
;
; FL Studio gestures:   Ctrl + wheel = zoom HORIZONTAL
;                       Alt  + wheel = zoom VERTICAL
;
; Piapro Studio (for Miku V4 / V4X) native gestures:
;   plain wheel           = scroll vertically
;   Shift + wheel         = scroll horizontally
;   Ctrl + Shift + wheel  = zoom horizontally  <-- reused for FL Ctrl+wheel
;   Ctrl + Shift + ] / [  = zoom vertically    <-- reused for FL Alt+wheel
;   Ctrl + wheel          = (nothing)          <-- free, so we hijack it
;   Alt  + wheel          = (nothing)          <-- free, so we hijack it
;
; This script, ONLY while a Piapro Studio window is focused, maps the FL gestures
; onto Piapro's real zoom triggers (so FL Studio's own shortcuts are untouched):
;   Ctrl + wheel -> Ctrl+Shift+wheel   (horizontal zoom)
;   Alt  + wheel -> Ctrl+Shift+] / [   (vertical zoom)
;
; TWO things make vertical zoom tricky (both handled below):
;  1. SPEED: Piapro ignores Ctrl+Shift+] sent with the default Send/SendInput
;     (all keys arrive in one instant batch). Sending it via SendEvent with a
;     short key delay — paced like typing — is what Piapro registers.
;  2. THE HELD ALT: to send a clean Ctrl+Shift+] we must drop your held Alt, but
;     that also makes AHK think Alt is up, so Alt+wheel would fire only once. We
;     re-press Alt afterwards (if you're still holding it) so you can hold Alt and
;     keep scrolling to zoom continuously, just like horizontal zoom.
;
; Requires AutoHotkey v2  (https://www.autohotkey.com/)
; Repo:    https://github.com/KunqiK/DAW-Extension-Claude
;==============================================================================

SetTitleMatchMode(2)   ; match a window whose title CONTAINS the given text

g_VZooming := false    ; true only while a vertical-zoom keystroke is being sent

; Vertical-zoom send speed. Piapro drops the keystroke if it arrives too fast,
; so we pace it. 60/30 ms is confirmed-working; LOWER = snappier zoom and smoother
; hold-and-scroll, but too low and Piapro may miss it. Tune these two to taste.
g_ZoomDelay := 60      ; ms between keystrokes
g_ZoomPress := 30      ; ms each key is held down

A_IconTip := "Piapro <-> FL zoom hotkeys (active only in Piapro Studio)"
TrayTip("In Piapro: Ctrl+wheel = horizontal zoom, Alt+wheel = vertical zoom (like FL Studio).",
        "Piapro FL hotkeys loaded  (v0.5)")

; --- These remaps fire ONLY while a 'Piapro Studio' window is active ----------
; "Piapro Studio" also matches FL's wrapper title "Piapro Studio VSTi (Master)",
; but never matches the FL Studio main window.
#HotIf WinActive("Piapro Studio")

    ; HORIZONTAL ZOOM — FL Ctrl+wheel -> Piapro Ctrl+Shift+wheel.
    ; {Blind} keeps your physically-held Ctrl down and just adds Shift.
    ^WheelUp::Send("{Blind}+{WheelUp}")     ; Ctrl + wheel up   -> zoom IN
    ^WheelDown::Send("{Blind}+{WheelDown}") ; Ctrl + wheel down -> zoom OUT

    ; VERTICAL ZOOM — FL Alt+wheel -> Piapro Ctrl+Shift+] / [ (paced SendEvent).
    !WheelUp::VZoom("]")     ; Alt + wheel up   -> Ctrl+Shift+]  (zoom IN)
    !WheelDown::VZoom("[")   ; Alt + wheel down -> Ctrl+Shift+[  (zoom OUT)

#HotIf   ; end Piapro-only context

; While a vertical-zoom keystroke is mid-flight, swallow ANY further wheel notch
; so a stray physical scroll can't leak out as Ctrl+Shift+wheel (= horizontal
; zoom). The window is only the few ms of the send; normal scrolling is untouched.
#HotIf WinActive("Piapro Studio") && g_VZooming
    *WheelUp::return
    *WheelDown::return
#HotIf

; --- Vertical-zoom sender -----------------------------------------------------
VZoom(bracket) {
    global g_VZooming, g_ZoomDelay, g_ZoomPress
    Critical                        ; don't let another thread interrupt the send
    prevDelay := A_KeyDelay
    prevDur := A_KeyDuration
    altHeld := GetKeyState("Alt", "P")   ; is Alt PHYSICALLY held right now?
    g_VZooming := true
    try {
        Send("{Alt up}")                  ; drop the held Alt (it would taint the combo)
        SetKeyDelay(g_ZoomDelay, g_ZoomPress)
        SendEvent("^+" bracket)           ; clean, paced Ctrl+Shift+] or Ctrl+Shift+[
    } finally {
        ; Re-press Alt only if you're still holding it, so AHK stays in sync and
        ; Alt+wheel keeps firing on the next notch (continuous zoom). If you let go
        ; mid-send, we leave it up — no stuck Alt key.
        if (altHeld && GetKeyState("Alt", "P"))
            Send("{Alt down}")
        SetKeyDelay(prevDelay, prevDur)
        g_VZooming := false
    }
}
