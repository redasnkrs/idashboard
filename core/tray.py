"""Icone de barre des taches, optionnelle."""
import logging
import threading

log = logging.getLogger("idash.tray")
_icon = None


def _image():
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (64, 64), (8, 7, 6, 255))
    draw = ImageDraw.Draw(img)
    draw.ellipse((10, 10, 54, 54), fill=(255, 154, 46, 255))
    draw.rectangle((28, 16, 36, 48), fill=(8, 7, 6, 255))
    draw.rectangle((16, 28, 48, 36), fill=(8, 7, 6, 255))
    return img


def start(on_open=None, on_settings=None, on_restart=None, on_quit=None):
    global _icon
    if _icon is not None:
        return True
    try:
        import pystray
    except ImportError:
        log.info("pystray absent : pas d'icone tray")
        return False
    try:
        image = _image()
    except ImportError:
        log.info("Pillow absent : pas d'icone tray")
        return False
    items = []
    if on_open:
        items.append(pystray.MenuItem("Ouvrir le 7\"", lambda *_: on_open(),
                                      default=True))
    if on_settings:
        items.append(pystray.MenuItem("Reglages", lambda *_: on_settings()))
    if on_restart:
        items.append(pystray.MenuItem("Redemarrer", lambda *_: on_restart()))
    if on_quit:
        items.append(pystray.MenuItem("Quitter", lambda *_: on_quit()))
    icon = pystray.Icon("idash", image, "idash", pystray.Menu(*items))
    try:
        thread = threading.Thread(target=icon.run, name="idash-tray",
                                  daemon=True)
        thread.start()
    except Exception as exc:
        log.warning("tray indisponible: %s", exc)
        return False
    _icon = icon
    return True


def stop():
    global _icon
    if _icon is not None:
        try:
            _icon.stop()
        except Exception:
            pass
        _icon = None


def running():
    return _icon is not None
