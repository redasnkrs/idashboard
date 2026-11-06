"""Configuration centrale du pont.

Toutes les constantes modifiables sont ici. Les chemins sont resolus a partir
de la racine du depot, donc le projet peut etre place n'importe ou.
"""
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DASHBOARDS_DIR = ROOT / "dashboards"
HOME_FILE = ROOT / "home" / "index.html"
SETTINGS_FILE = ROOT / "settings" / "index.html"
STUDIO_DIR = ROOT / "studio"
UPDATE_FILE = ROOT / "update" / "index.html"
VERSION_FILE = ROOT / "VERSION"


def _read_version():
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip() or "dev"
    except OSError:
        return "dev"


VERSION = _read_version()

PORT = int(os.environ.get("IDASH_PORT", "25555"))
POLL_HZ = int(os.environ.get("IDASH_POLL_HZ", "60"))
STREAM_HZ = int(os.environ.get("IDASH_STREAM_HZ", "60"))

# Fenetre Chrome --app du mini ecran (Phase 3 : detection automatique).
SCREEN = {
    "x": int(os.environ.get("IDASH_SCREEN_X", "2560")),
    "y": int(os.environ.get("IDASH_SCREEN_Y", "834")),
    "width": int(os.environ.get("IDASH_SCREEN_W", "1024")),
    "height": int(os.environ.get("IDASH_SCREEN_H", "600")),
}

# Tableau de bord affiche par /dashboard quand aucun nom n'est donne.
DEFAULT_DASHBOARD = "course/acevo-cluster"

# Un nom de tableau de bord ne contient que ces caracteres (pas de "..").
_SAFE = re.compile(r"^[A-Za-z0-9_-]+$")
# Un fichier d'apercu peut avoir une extension (preview.png).
_SAFE_FILE = re.compile(r"^[A-Za-z0-9_.-]+$")


def _safe_parts(spec):
    parts = (spec or "").strip().strip("/").split("/")
    if not parts or any(not _SAFE.match(p) for p in parts):
        return None
    return parts


def dashboard_file(spec):
    """Resout ``category/nom`` (ou juste ``nom``) vers un fichier du dossier.

    Retourne ``None`` si le chemin est invalide ou introuvable.
    """
    spec = (spec or "").strip().strip("/")
    if not spec:
        spec = DEFAULT_DASHBOARD
    parts = _safe_parts(spec)
    if parts is None:
        return None
    if len(parts) == 1:
        found = sorted(DASHBOARDS_DIR.glob("*/%s/index.html" % parts[0]))
        return found[0] if found else None
    if len(parts) != 2:
        return None
    target = DASHBOARDS_DIR / parts[0] / parts[1] / "index.html"
    return target if target.is_file() else None


def dashboard_manifest(spec):
    """Retourne le ``manifest.json`` d'un tableau de bord, ou ``None``."""
    html = dashboard_file(spec)
    if html is None:
        return None
    manifest = html.parent / "manifest.json"
    return manifest if manifest.is_file() else None


def dashboard_asset(spec, name):
    """Retourne un fichier statique d'un tableau de bord (apercu, etc.)."""
    parts = _safe_parts(spec)
    asset = (name or "").strip().strip("/").split("/")
    if parts is None or len(parts) != 2 or not asset:
        return None
    if any(not _SAFE_FILE.match(p) or p in (".", "..") for p in asset):
        return None
    target = DASHBOARDS_DIR.joinpath(*parts, *asset)
    try:
        target.resolve().relative_to((DASHBOARDS_DIR / parts[0] / parts[1]).resolve())
    except (OSError, ValueError):
        return None
    return target if target.is_file() else None


def spec_for_path(path):
    """Retourne la cle ``categorie/nom`` d'un index.html sous dashboards/."""
    try:
        rel = Path(path).resolve().relative_to(DASHBOARDS_DIR.resolve())
    except (OSError, ValueError):
        return None
    if len(rel.parts) != 3 or rel.name != "index.html":
        return None
    return "%s/%s" % (rel.parts[0], rel.parts[1])
