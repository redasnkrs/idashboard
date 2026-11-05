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

3. Ouvre `http://localhost:25555/` : la page d'accueil liste les compteurs.
   « Ouvrir sur le 7" » lance Chrome en mode application sur le mini écran
   (position et taille dans `core/config.py`, surchargeables par les variables
   `IDASH_SCREEN_X`, `IDASH_SCREEN_Y`, `IDASH_SCREEN_W`, `IDASH_SCREEN_H`).
   Hors Windows, les coordonnées ne sont appliquées que si `IDASH_SCREEN_X`
   est défini ; sinon Chrome s'ouvre normalement, ou le navigateur par défaut.

## Développement sans le jeu (Mac / Linux / Windows)

```
python main.py --fake
```

Ouvre ensuite `http://localhost:25555/`. Pour voir seulement le design, sans
serveur : ouvre `dashboards/course/acevo-cluster/index.html?demo` ou
`dashboards/course/acevo-minimal/index.html?demo` dans un navigateur.

## Routes

| Route | Contenu |
|---|---|
| `/` | accueil : catalogue des compteurs, aperçus, boutons de lancement |
| `/dashboard` | redirige vers le compteur par défaut (garde les paramètres) |
| `/dashboard/<catégorie>/<nom>` | tableau de bord précis (dossier) |
| `/dashboard/<nom>` | raccourci si le nom est unique |
| `/dashboard/<catégorie>/<nom>/preview.png` | aperçu statique du compteur |
| `/dashboard/<catégorie>/<nom>/manifest.json` | métadonnées du compteur |
| `/settings` | réglages (couleurs, unités, blocs) avec aperçu live |
| `/stream` | flux SSE à 60 Hz |
| `/api/dash` | dernier état (contrat commun) |
| `/api/dashboards` | catalogue JSON des compteurs + catégories |
| `/api/schema` | version et description du contrat |
| `/api/themes` | thèmes disponibles + état (GET), enregistrement (POST) |
| `/api/themes/active` | thème effectif (`?dashboard=…&game=…&car=…`) |
| `/api/themes/stream` | SSE : numéro de révision du thème |
| `/api/themes/reset` | réinitialise une portée (POST) |
| `/api/launch` | ouvre un compteur sur le mini écran (POST) |
| `/api/ets2/telemetry` | format « ETS2 Telemetry Server » (Macro Deck) |

## Thèmes et réglages

Ouvre `http://localhost:25555/settings` depuis l'écran principal : les
changements de couleur, d'unités (km/h ↔ mph, °C ↔ °F) et de blocs visibles
sont enregistrés et appliqués en direct sur le 7" (sans rechargement).

Les palettes sont dans `themes/*.json` (ambre/ivoire, rouge sport, vert). Les
choix de l'utilisateur vont dans `themes/active.json` (ignoré par git) et
peuvent être définis globalement, par jeu, par voiture ou par compteur
(priorité : compteur > voiture > jeu > global).

## Structure

```
core/          schema.py (contrat), config.py, pump.py (lecture), server.py,
               themes.py (palettes, résolution, diffusion), catalog.py
               (catalogue des compteurs), launcher.py (Chrome sur le 7")
adapters/      acevo.py (source du jeu), fake.py (tests), base.py (interface)
dashboards/    course/acevo-cluster/  compteur complet
               course/acevo-minimal/  compteur minimal
home/          index.html (accueil / catalogue)
settings/      index.html (page de réglages)
themes/        ambre-ivoire.json, rouge-sport.json, vert.json
tests/         tests unitaires et captures Playwright
main.py        point d'entrée
acevo_bridge.py  ancien nom (compatibilité)
```

Ajouter un tableau de bord = ajouter un dossier `dashboards/<catégorie>/<nom>/`
avec `index.html`, `manifest.json` et `preview.png`. Il apparaît tout seul sur
l'accueil et dans les réglages. Ajouter un jeu = écrire un adaptateur qui
respecte `adapters/base.py`.

## Tests

```
python -m unittest discover -s tests -v
python -m tests.visual_check     # captures 1024x600/560, accueil, réglages,
                                 # et génération des preview.png
```
