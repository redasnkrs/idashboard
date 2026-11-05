"""Catalogue des tableaux de bord.

Chaque dossier ``dashboards/<categorie>/<nom>/`` contenant un
``manifest.json`` et un ``index.html`` devient une entree du menu. Ajouter un
dossier suffit, aucun code a modifier.

Le manifest declare au minimum ``id`` et ``name`` ; ``category`` et ``game``
sont deduites des dossiers / du nom du jeu si absentes.
"""
import json

from core import studio
from core.config import DASHBOARDS_DIR, DEFAULT_DASHBOARD, dashboard_file

CATEGORY_LABELS = {
    "course": "Course",
    "aviation": "Aviation",
    "divers": "Divers",
    "custom": "Custom",
}

MANIFEST_FIELDS = (
    "name", "description", "game", "game_id", "size", "schema",
    "schema_version", "preview", "order", "tags",
)


def category_label(category):
    return CATEGORY_LABELS.get(category, (category or "").capitalize())


def _entry(manifest_path):
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    category = manifest_path.parent.parent.name
    folder_id = manifest_path.parent.name
    spec = "%s/%s" % (category, folder_id)
    if dashboard_file(spec) is None:
        return None
    item = {"spec": spec, "id": folder_id, "category": category,
            "category_label": category_label(category)}
    for field in MANIFEST_FIELDS:
        if field in data:
            item[field] = data[field]
    item.setdefault("name", folder_id)
    item.setdefault("description", "")
    item.setdefault("game", category_label(category))
    item.setdefault("game_id", folder_id)
    item.setdefault("size", [1024, 600])
    item.setdefault("schema", "course")
    item.setdefault("schema_version", 1)
    item.setdefault("tags", [])
    try:
        item["order"] = int(item.get("order", 999))
    except (TypeError, ValueError):
        item["order"] = 999
    preview = data.get("preview")
    item["preview_url"] = (
        "/dashboard/%s/%s" % (spec, preview) if isinstance(preview, str)
        and preview else None)
    item["url"] = "/dashboard/%s" % spec
    item["settings_url"] = "/settings?dashboard=%s" % spec
    return item


def list_dashboards():
    """Liste triee des tableaux de bord disponibles."""
    if not DASHBOARDS_DIR.is_dir():
        return []
    items = []
    for manifest in sorted(DASHBOARDS_DIR.glob("*/*/manifest.json")):
        item = _entry(manifest)
        if item is not None:
            items.append(item)
    for layout in studio.list_layouts():
        item = studio.catalog_entry(layout)
        if item is None:
            continue
        item["category_label"] = category_label(item["category"])
        items.append(item)
    items.sort(key=lambda i: (i["category"], i["game"], i["order"],
                              i["name"].lower()))
    return items


def find(spec):
    """Retourne l'entree correspondant a ``categorie/nom`` ou ``nom``."""
    spec = (spec or "").strip().strip("/")
    if not spec:
        spec = DEFAULT_DASHBOARD
    for item in list_dashboards():
        if spec in (item["spec"], item["id"]):
            return item
    return None


def default_dashboard():
    return find(DEFAULT_DASHBOARD) or (list_dashboards() or [None])[0]
