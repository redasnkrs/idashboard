"""Configuration centrale du pont.

Toutes les constantes modifiables sont ici. Les chemins sont resolus a partir
de la racine du depot, donc le projet peut etre place n'importe ou.
"""
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DASHBOARDS_DIR = ROOT / "dashboards"

PORT = int(os.environ.get("IDASH_PORT", "25555"))
POLL_HZ = int(os.environ.get("IDASH_POLL_HZ", "60"))
STREAM_HZ = int(os.environ.get("IDASH_STREAM_HZ", "60"))

# Tableau de bord affiche par /dashboard quand aucun nom n'est donne.
DEFAULT_DASHBOARD = "course/acevo-cluster"

# Un nom de tableau de bord ne contient que ces caracteres (pas de "..").
_SAFE = re.compile(r"^[A-Za-z0-9_-]+$")


def dashboard_file(spec):
    """Resout ``category/nom`` (ou juste ``nom``) vers un fichier du dossier.

    Accepte ``index.html`` ou ``manifest.json``. Retourne ``None`` si le
    chemin est invalide ou introuvable.
    """
    spec = (spec or "").strip().strip("/")
    if not spec:
        spec = DEFAULT_DASHBOARD
    parts = spec.split("/")
    if any(not _SAFE.match(p) for p in parts):
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
