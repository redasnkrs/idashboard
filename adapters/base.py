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
