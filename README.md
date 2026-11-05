# Tableau de bord mini écran (Assetto Corsa Evo)

Tableau de bord de voiture sur mini écran 7" (1024x600), alimenté par la
télémétrie d'Assetto Corsa Evo. Voir `Mini Deck App Roadmap.md` pour le projet
complet et les phases.

## Installation (PC Windows)

1. Python 3.12+ et le paquet du jeu :

   ```
   pip install acevo-sdk
   ```

2. Lancement : double-clique `lancer.bat` (ou `python main.py`).

3. Ouvre `http://localhost:25555/dashboard` dans la fenêtre Chrome dédiée
   (`map.ps1` la place sur le 7" en `2560,834`).

## Développement sans le jeu (Mac / Linux / Windows)

```
python main.py --fake
```

Ouvre ensuite `http://localhost:25555/dashboard`. Pour voir seulement le
design, sans serveur : ouvre `dashboards/course/acevo-cluster/index.html?demo`
dans un navigateur.

## Routes

| Route | Contenu |
|---|---|
| `/dashboard` | tableau de bord par défaut |
| `/dashboard/<catégorie>/<nom>` | tableau de bord précis (dossier) |
| `/dashboard/<nom>` | raccourci si le nom est unique |
| `/settings` | page de réglages (couleurs, unités, blocs) avec aperçu live |
| `/stream` | flux SSE à 60 Hz |
| `/api/dash` | dernier état (contrat commun) |
| `/api/schema` | version et description du contrat |
| `/api/themes` | thèmes disponibles + état (GET), enregistrement (POST) |
| `/api/themes/active` | thème effectif (`?game=…&car=…`) |
| `/api/themes/stream` | SSE : numéro de révision du thème |
| `/api/ets2/telemetry` | format « ETS2 Telemetry Server » (Macro Deck) |

## Thèmes et réglages

Ouvre `http://localhost:25555/settings` depuis l'écran principal : les
changements de couleur, d'unités (km/h ↔ mph, °C ↔ °F) et de blocs visibles
sont enregistrés et appliqués en direct sur le 7" (sans rechargement).

Les palettes sont dans `themes/*.json` (ambre/ivoire, rouge sport, vert). Les
choix de l'utilisateur vont dans `themes/active.json` (ignoré par git) et
peuvent être définis globalement, par jeu ou par voiture.

## Structure

```
core/          schema.py (contrat), config.py, pump.py (lecture), server.py,
               themes.py (palettes, résolution, diffusion)
adapters/      acevo.py (source du jeu), fake.py (tests), base.py (interface)
dashboards/    course/acevo-cluster/  index.html + manifest.json + preview.png
settings/      index.html (page de réglages)
themes/        ambre-ivoire.json, rouge-sport.json, vert.json
tests/         tests unitaires et captures Playwright
main.py        point d'entrée
acevo_bridge.py  ancien nom (compatibilité)
```

Ajouter un tableau de bord = ajouter un dossier `dashboards/<catégorie>/<nom>/`
avec `index.html` et `manifest.json`. Ajouter un jeu = écrire un adaptateur qui
respecte `adapters/base.py`.

## Tests

```
python -m unittest discover -s tests -v
python -m tests.visual_check     # captures 1024x600 et 1024x560
```
