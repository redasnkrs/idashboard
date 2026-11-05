"""Themes : chargement, resolution par compteur/jeu/voiture, sauvegarde,
diffusion.

Les palettes sont des fichiers ``themes/<id>.json``. L'etat choisi par
l'utilisateur (theme actif + surcharges) est dans ``themes/active.json``,
ignore par git.

Resolution : compteur > voiture > jeu > global. Les surcharges sont
fusionnees dans cet ordre, ce qui permet de garder un reglage global et de ne
changer qu'une couleur pour un compteur, une voiture ou un jeu precis.
"""
import copy
import json
import re
import queue
import threading

from core.config import ROOT

THEMES_DIR = ROOT / "themes"
STATE_FILE = THEMES_DIR / "active.json"

COLOR_KEYS = {
    "ink", "ivory", "muted", "rule", "off", "amber", "red", "green", "blue",
    "violet", "dim", "backIn", "backOut", "faceIn", "faceMid", "faceOut",
    "bezelLight", "bezelMid", "bezelDark", "needleFrom", "needleTo",
    "tachMinor", "redText", "arrowOff", "ledOff", "chipBorder",
    "chipActiveBg", "waitOverlay",
}
BLOCK_KEYS = {
    "car", "fuel", "water", "oil", "pressures", "telltales", "track", "lap",
    "best", "last", "position", "aids", "shiftlights",
}

DEFAULT_STATE = {
    "active": "ambre-ivoire",
    "overrides": {},
    "games": {},
    "cars": {},
    "dashboards": {},
}

_HEX = re.compile(r"^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$")

_lock = threading.Lock()
_revision = 0
_subscribers = set()


def _deep_merge(base, extra):
    for key, value in (extra or {}).items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def load_themes():
    themes = {}
    if not THEMES_DIR.is_dir():
        return themes
    for path in sorted(THEMES_DIR.glob("*.json")):
        if path.name == STATE_FILE.name:
            continue
        try:
            theme = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        themes[theme.get("id") or path.stem] = theme
    return themes


def load_state():
    state = copy.deepcopy(DEFAULT_STATE)
    try:
        saved = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return state
    if isinstance(saved, dict):
        state.update(saved)
    return state


def save_state(state):
    THEMES_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    tmp.replace(STATE_FILE)


def sanitize_overrides(overrides):
    """Ne garde que les cles et valeurs connues (couleurs hex, etc.)."""
    if not isinstance(overrides, dict):
        return {}
    clean = {}
    colors = overrides.get("colors")
    if isinstance(colors, dict):
        colors = {k: v for k, v in colors.items()
                  if k in COLOR_KEYS and isinstance(v, str) and _HEX.match(v)}
        if colors:
            clean["colors"] = colors
    units = overrides.get("units")
    if isinstance(units, dict):
        units = {k: v for k, v in units.items()
                 if (k == "speed" and v in ("kmh", "mph"))
                 or (k == "temp" and v in ("c", "f"))}
        if units:
            clean["units"] = units
    blocks = overrides.get("blocks")
    if isinstance(blocks, dict):
        blocks = {k: bool(v) for k, v in blocks.items() if k in BLOCK_KEYS}
        if blocks:
            clean["blocks"] = blocks
    font = overrides.get("font")
    if isinstance(font, str) and 0 < len(font) <= 120:
        clean["font"] = font
    return clean


def resolve(dashboard=None, game=None, car=None):
    """Theme effectif pour un compteur / un jeu / une voiture donnes."""
    themes = load_themes()
    if not themes:
        return {}
    state = load_state()
    active = state.get("active")
    scopes = [state]
    if game:
        scopes.append(state.get("games", {}).get(game, {}))
    if car:
        scopes.append(state.get("cars", {}).get(car, {}))
    if dashboard:
        scopes.append(state.get("dashboards", {}).get(dashboard, {}))
    overrides = {}
    for scope in scopes:
        if scope.get("active"):
            active = scope["active"]
        _deep_merge(overrides, scope.get("overrides") or {})
    if active not in themes:
        active = next(iter(themes))
    theme = copy.deepcopy(themes[active])
    _deep_merge(theme, overrides)
    theme["id"] = active
    return theme


def update(payload):
    """Applique un enregistrement de la page de reglages."""
    if not isinstance(payload, dict):
        raise ValueError("payload invalide")
    state = load_state()
    scope = payload.get("scope") or "global"
    key = str(payload.get("key") or "").strip()
    if scope == "game" and key:
        target = state.setdefault("games", {}).setdefault(key, {})
    elif scope == "car" and key:
        target = state.setdefault("cars", {}).setdefault(key, {})
    elif scope == "dashboard" and key:
        target = state.setdefault("dashboards", {}).setdefault(key, {})
    else:
        scope = "global"
        target = state
    active = payload.get("active")
    if active is not None:
        if active not in load_themes():
            raise ValueError("theme inconnu: %s" % active)
        target["active"] = active
    if "overrides" in payload:
        target["overrides"] = sanitize_overrides(payload["overrides"])
    save_state(state)
    bump()
    return scope, key, resolve()


def reset_scope(scope, key):
    state = load_state()
    if scope == "game":
        state.get("games", {}).pop(key, None)
    elif scope == "car":
        state.get("cars", {}).pop(key, None)
    elif scope == "dashboard":
        state.get("dashboards", {}).pop(key, None)
    else:
        state["overrides"] = {}
        state["active"] = DEFAULT_STATE["active"]
    save_state(state)
    bump()


# ---------------------------------------------------------------------------
# Diffusion (SSE) : on ne pousse qu'un numero de revision, les pages rechargent
# le theme resolu avec leur propre jeu / voiture.
# ---------------------------------------------------------------------------
def revision():
    with _lock:
        return _revision


def bump():
    global _revision
    with _lock:
        _revision += 1
        subs = list(_subscribers)
        rev = _revision
    for q in subs:
        try:
            q.put_nowait(rev)
        except queue.Full:
            pass
    return rev


def subscribe():
    q = queue.Queue(maxsize=8)
    with _lock:
        _subscribers.add(q)
    return q


def unsubscribe(q):
    with _lock:
        _subscribers.discard(q)
