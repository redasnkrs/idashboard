"""Interface commune des sources de telemetrie.

Une source expose deux lectures :

- ``read()`` : l'etat du tableau de bord au format du contrat (§4), ou ``None``
  si le jeu n'est pas joignable.
- ``ets2()`` : le meme etat au format « ETS2 Telemetry Server » (optionnel,
  utilise par le plugin Macro Deck).

Ajouter un jeu (Phase 4) = ecrire une classe qui respecte cette interface.
"""


class Source:
    def read(self):
        raise NotImplementedError

    def ets2(self):
        return DISCONNECTED_ETS2


DISCONNECTED_ETS2 = {
    "game": {"connected": False, "paused": False, "gameName": None},
    "truck": {},
    "trailer": {},
    "navigation": {},
    "job": {},
}


def basic_ets2(dash):
    """Format ETS2 minimal a partir du contrat commun (AC, AMS2...)."""
    if not dash or not dash.get("c"):
        return DISCONNECTED_ETS2
    game = dash.get("game_id") or "sim"
    return {
        "game": {"connected": True, "paused": dash.get("st") == 3,
                 "gameName": game},
        "truck": {
            "id": game, "make": dash.get("game") or game,
            "model": dash.get("car") or "Car",
            "speed": dash.get("v") or 0,
            "gear": dash.get("g") or 0,
            "displayedGear": dash.get("g") or 0,
            "engineRpm": dash.get("r") or 0,
            "engineRpmMax": dash.get("rm") or 0,
            "fuel": dash.get("fuel") or 0,
            "fuelCapacity": 0,
            "engineOn": bool(dash.get("run")),
            "electricOn": bool(dash.get("ign")),
            "parkBrakeOn": (dash.get("hb") or 0) > .3,
            "userThrottle": dash.get("gas") or 0,
            "userBrake": dash.get("brk") or 0,
            "userClutch": dash.get("clu") or 0,
            "lightsBeamLowOn": bool(dash.get("low")),
            "lightsBeamHighOn": bool(dash.get("high")),
            "blinkerLeftOn": bool(dash.get("L")),
            "blinkerRightOn": bool(dash.get("R")),
            "lightsBeaconOn": bool(dash.get("haz")),
            "lightsBrakeOn": (dash.get("brk") or 0) > .05,
            "lightsReverseOn": (dash.get("g") or 0) < 0,
        },
        "trailer": {"attached": False},
        "navigation": {"speedLimit": 0, "estimatedDistance": 0,
                       "estimatedTime": ""},
        "job": {},
    }
