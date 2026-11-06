"""Detection des ecrans (Windows) pour choisir le 7"."""
import ctypes
import sys


def list_screens():
    """Liste les ecrans connectes sous Windows, sinon liste vide."""
    if sys.platform != "win32":
        return []
    try:
        from ctypes import wintypes

        class RECT(ctypes.Structure):
            _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                        ("right", wintypes.LONG), ("bottom", wintypes.LONG)]

        class MONITORINFOEXW(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", wintypes.DWORD),
                ("szDevice", ctypes.c_wchar * 32),
            ]

        user32 = ctypes.windll.user32
        monitors = []
        hmonitor_type = getattr(wintypes, "HMONITOR", ctypes.c_void_p)
        hdc_type = getattr(wintypes, "HDC", ctypes.c_void_p)
        proc = ctypes.WINFUNCTYPE(
            wintypes.BOOL, hmonitor_type, hdc_type,
            ctypes.POINTER(RECT), wintypes.LPARAM)

        def callback(hmonitor, hdc, rect, data):
            info = MONITORINFOEXW()
            info.cbSize = ctypes.sizeof(info)
            if user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
                r = info.rcMonitor
                monitors.append({
                    "device": str(info.szDevice).strip("\x00"),
                    "x": int(r.left), "y": int(r.top),
                    "width": int(r.right - r.left),
                    "height": int(r.bottom - r.top),
                    "primary": bool(info.dwFlags & 0x1),
                })
            return True

        user32.EnumDisplayMonitors(0, 0, proc(callback), 0)
        monitors.sort(key=lambda m: (m["x"], m["y"]))
        return monitors
    except Exception:
        return []


def pick_7(screens):
    """Choisit l'ecran 1024x600, sinon un ecran secondaire, sinon le premier."""
    if not screens:
        return None
    for screen in screens:
        if screen["width"] == 1024 and screen["height"] == 600:
            return dict(screen)
    for screen in screens:
        if not screen.get("primary"):
            return dict(screen)
    return dict(screens[0])
