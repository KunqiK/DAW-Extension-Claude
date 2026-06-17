#Requires AutoHotkey v2.0
#SingleInstance Force
;==============================================================================
; PiaproPanel.ahk  —  a friendlier floating control panel for Piapro Studio (v0.1)
;
; Piapro Studio is closed-source and runs inside FL Studio, so we can't restyle
; its real UI. Instead this draws a small, always-on-top panel that DOCKS to the
; Piapro window (top-right) and follows it around, giving big, clearly-labelled
; buttons for actions that are clunky to reach. v1 = a Play / Stop button.
;
; It only shows while FL Studio (which hosts Piapro) is the foreground app, so it
; won't float over your browser etc. Runs happily alongside PiaproFLHotkeys.ahk.
;
; Requires AutoHotkey v2  (https://www.autohotkey.com/)
; Repo:    https://github.com/KunqiK/DAW-Extension-Claude
;==============================================================================

SetTitleMatchMode(2)            ; match a window whose title CONTAINS the text

;--- Config (tweak to taste) ---------------------------------------------------
; Piapro's play/stop key. Space is the universal DAW transport toggle and is the
; best guess, but Piapro is closed and can't be inspected from here — if Play/Stop
; does nothing (or the wrong thing), tell me the real key and change THIS line.
global TRANSPORT_KEY := "Space"
global HOST_EXE      := "FL64.exe"   ; FL Studio's process (it hosts Piapro)
global PANEL_W       := 168          ; panel width (px)
global DOCK_X        := 14           ; inset from Piapro's right edge
global DOCK_Y        := 50           ; inset from Piapro's top edge
global POLL_MS       := 250          ; how often we track the Piapro window

; Ina'nis palette (RRGGBB for AHK Gui)
global C_BG := "1b1822", C_FG := "e1d8ef", C_ACCENT := "f29a30", C_INK := "000000", C_DIM := "9575E2"

;--- Build the panel -----------------------------------------------------------
global panel := Gui("+AlwaysOnTop -Caption +ToolWindow", "Piapro Panel")
panel.BackColor := C_BG
panel.MarginX := 10, panel.MarginY := 10

panel.SetFont("s8 Bold", "Verdana")
panel.AddText("c" C_DIM " w" (PANEL_W - 20), "PIAPRO  ·  M. Y.")

panel.SetFont("s12 Bold", "Verdana")
; A coloured Text acts as a flat button (native buttons can't be themed dark).
global btnPlay := panel.AddText("Background" C_ACCENT " c" C_INK " Center +0x200 w" (PANEL_W - 20) " h46",
                                "▶   Play / Stop")
btnPlay.OnEvent("Click", PlayStop)

global g_panelHwnd := panel.Hwnd
global g_prevX := -99999, g_prevY := -99999, g_shown := false

A_IconTip := "Piapro Panel (Play/Stop) — shows while FL Studio is focused"
TrayTip("A Play/Stop panel docks to the Piapro window while FL Studio is focused.",
        "Piapro Panel loaded  (v0.1)")

SetTimer(Track, POLL_MS)
Track()

;--- Follow the Piapro window --------------------------------------------------
Track() {
    global panel, g_prevX, g_prevY, g_shown, g_panelHwnd
    global PANEL_W, DOCK_X, DOCK_Y, HOST_EXE

    ; Hide unless Piapro exists, isn't minimized, and FL (or this panel) is in front.
    if (!WinExist("Piapro Studio") || WinGetMinMax("Piapro Studio") = -1
        || !(WinActive("ahk_exe " HOST_EXE) || WinActive("ahk_id " g_panelHwnd))) {
        if (g_shown) {
            panel.Hide()
            g_shown := false
        }
        return
    }

    WinGetPos(&wx, &wy, &ww, &wh, "Piapro Studio")
    px := wx + ww - PANEL_W - DOCK_X
    py := wy + DOCK_Y
    if (!g_shown || px != g_prevX || py != g_prevY) {
        panel.Show("x" px " y" py " AutoSize NoActivate")
        g_prevX := px, g_prevY := py, g_shown := true
    }
}

;--- Actions -------------------------------------------------------------------
PlayStop(*) {
    global TRANSPORT_KEY
    if WinExist("Piapro Studio") {
        WinActivate("Piapro Studio")            ; clicking us stole focus — give it back
        if WinWaitActive("Piapro Studio", , 0.5)
            SendEvent("{" TRANSPORT_KEY "}")     ; paced send, like the zoom tool
    }
}
