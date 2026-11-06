"""Contrat de donnees du tableau de bord.

``SCHEMA_VERSION`` decrit le format du flux ``/stream`` et de ``/api/dash``.
Ajouter une cle est compatible ; renommer ou supprimer une cle impose une
version majeure. Voir ``Mini Deck App Roadmap.md`` section 4.
"""

SCHEMA_VERSION = 1
SCHEMA_NAME = "course"

# cle -> type attendu. "number" accepte int et float ; "number|null" accepte
# en plus None (valeur inconnue). Le type ``bool`` est teste avant ``number``
# car ``bool`` herite de ``int`` en Python.
DASH_SCHEMA = {
    "c": "bool",
    "st": "int",
    "v": "number",
    "r": "number",
    "rm": "number",
    "g": "int",
    "gas": "number",
    "brk": "number",
    "clu": "number",
    "hb": "number",
    "fuel": "number",
    "fp": "number",
    "fpl": "number",
    "laps": "number",
    "low": "bool",
    "high": "bool",
    "L": "bool",
    "R": "bool",
    "haz": "bool",
    "pit": "bool",
    "pitlane": "bool",
    "tc": "bool",
    "abs": "bool",
    "esc": "bool",
    "lim": "bool",
    "up": "bool",
    "run": "bool",
    "ign": "bool",
    "wt": "number|null",
    "ot": "number|null",
    "op": "number|null",
    "boost": "number|null",
    "at": "number|null",
    "lap": "int",
    "last": "int",
    "best": "int",
    "delta": "int",
    "valid": "bool",
    "pos": "int",
    "nd": "int",
    "npos": "number|null",
    "tcl": "int|null",
    "absl": "int|null",
    "bb": "number|null",
    "car": "str",
    "track": "str",
    "cfg": "str",
    "mode": "str",
    "game": "str",
    "game_id": "str",
}


def _check(value, kind):
    if kind == "bool":
        return isinstance(value, bool)
    if kind == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "number|null":
        return value is None or _check(value, "number")
    if kind == "int|null":
        return value is None or _check(value, "int")
    if kind == "str":
        return isinstance(value, str)
    return False


def validate(dash):
    """Verifie un etat du tableau de bord.

    Retourne la liste des problemes (vide si tout est bon). Toutes les cles ne
    sont pas obligatoires (d'autres jeux peuvent en omettre), mais ``c`` l'est.
    Une cle inconnue est une erreur : elle doit etre declaree ici d'abord.
    """
    if not isinstance(dash, dict):
        return ["etat: objet attendu"]
    problems = []
    if "c" not in dash:
        problems.append("cle obligatoire manquante: c")
    if dash.get("c") is False:
        extra = set(dash) - {"c"}
        if extra:
            problems.append("deconnecte: cles en trop %s" % sorted(extra))
        return problems
    for key, value in dash.items():
        kind = DASH_SCHEMA.get(key)
        if kind is None:
            problems.append("cle inconnue: %s" % key)
        elif not _check(value, kind):
            problems.append("%s: attendu %s, recu %r" % (key, kind, value))
    return problems


def schema_info():
    """Description serialisable du contrat, pour ``/api/schema``."""
    return {
        "name": SCHEMA_NAME,
        "version": SCHEMA_VERSION,
        "keys": DASH_SCHEMA,
    }
