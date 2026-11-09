# Tableau de bord mini écran (AC Evo, AC 2014, AMS2)

Tableau de bord de voiture sur mini écran 7" (1024x600), alimenté par la
télémétrie d'Assetto Corsa Evo, d'Assetto Corsa 2014 ou d'Automobilista 2.
Voir `Mini Deck App Roadmap.md` pour le projet complet et les phases.

## Installation (PC Windows)

### Version .exe (recommandée)

1. Télécharge `idash-vX.Y.Z-win64.zip` depuis la dernière release GitHub.
2. Extrais le ZIP où tu veux, puis lance `idash.exe`.
3. Aucun Python à installer. Les logs sont dans `logs/idash.log`.

Le tray permet d'ouvrir l'accueil, les réglages, de redémarrer ou de quitter.
Au lancement, idash ouvre directement le dernier compteur sur le 7" (option
désactivable dans `/settings` → Système). Le démarrage avec Windows et la
réouverture automatique du 7" sont aussi dans cette page.

### Version source (développement)

1. Python 3.12+ et les dépendances :

   ```
   pip install -r requirements-windows.txt
   ```

2. Lancement : double-clique `lancer.bat` (ou `python main.py`).
   `python main.py --fake --no-tray` permet de tester sans jeu ni icône tray.

3. Ouvre `http://localhost:25555/` : la page d'accueil liste les compteurs.
   « Ouvrir sur le 7" » lance Chrome en mode application sur le mini écran
   (position et taille dans `core/config.py`, surchargeables par les variables
   `IDASH_SCREEN_X`, `IDASH_SCREEN_Y`, `IDASH_SCREEN_W`, `IDASH_SCREEN_H`).
   Hors Windows, les coordonnées ne sont appliquées que si `IDASH_SCREEN_X`
   est défini ; sinon Chrome s'ouvre normalement, ou le navigateur par défaut.
   La fenêtre démarre directement en plein écran (`--start-fullscreen`) ;
   `F11` ou `Échap` pour en sortir.

## Développement sans le jeu (Mac / Linux / Windows)

```
python main.py --fake
```

Ouvre ensuite `http://localhost:25555/`. Pour voir seulement le design, sans
serveur : ouvre `dashboards/course/acevo-cluster/index.html?demo` ou
`dashboards/course/acevo-minimal/index.html?demo` dans un navigateur.

Contact / veille : quand le contact est coupé (`ign` faux et moteur arrêté),
tout le compteur passe en gris. Au contact, test des voyants + balayage
pendant ~2,4 s avant l'affichage normal. Pour tester sans le jeu :
`?demo&ign=off` (veille) et `?demo&ign=wake` (coupé puis réveil).

Sur le 7" tactile, un balayage vers la gauche passe au compteur suivant, vers
la droite au précédent (le catalogue boucle). Les flèches ← / → font la même
chose au clavier. Le balayage est désactivé dans l'aperçu des réglages.

## Sources de télémétrie

Le pont lit en priorité le jeu qu'il trouve (détection automatique) :

- **Assetto Corsa Evo** (`acevo_pmf_*`, via `acevo-sdk`) ;
- **Assetto Corsa 2014** (`acpmf_*`, shared memory classique) ;
- **Automobilista 2** (`$pcars2$`, mode Shared Memory « Project CARS 2 » à
  activer dans les options du jeu) ;
- **Euro Truck Simulator 2 / ATS via SimHub** : idash lit
  `http://127.0.0.1:8888/api/getgamedata` et utilise aussi la carte GPS
  SimHub (`/maps/map.html`). SimHub doit être lancé avec son serveur web sur
  le port 8888. La carte affichée est celle de SimHub / du jeu, pas une carte
  redessinée par idash ; les mods de carte suivent le paquet TruckMaps utilisé
  par SimHub.

Pour forcer une source : `python main.py --game ac`, `--game ams2` ou
`--game acevo`. Sans option, le pont essaie AC Evo, puis AC, puis AMS2.
Les compteurs utilisent le contrat commun ; le nom du jeu et le thème
s'adaptent au jeu détecté. AC 2014 ne fournit pas le contact, les
feux/clignotants ni la température d'eau dans sa shared memory : ces champs
restent vides ou fixes (le reste — vitesse, rpm, rapport, carburant, temps,
position — fonctionne).

## Réglages

`/settings` est maintenant une vraie page à onglets :

- **Écran** : détection automatique des écrans Windows (le 1024×600 est
  proposé en priorité), sélection de l'écran du 7" et test de lancement.
- **Jeux** : chemins AC Evo, AC 2014 et AMS2, détection Steam, enregistrement
  et lancement de chaque jeu.
- **Apparence** : thème, portée (global/jeu/voiture/compteur), couleurs,
  unités et blocs, avec un aperçu compact.
- **Compteurs** : compteur par défaut (utilisé par `/dashboard` et l'accueil).
- **Système** : version, source de télémétrie active, mode exe/source,
  santé (`/api/health`), logs, démarrage Windows, ouverture directe du 7",
  réouverture du 7", redémarrage et mise à jour.

Les chemins de jeux et l'écran sont dans `app.json` (ignoré par git).

## Lancer Assetto Corsa Evo

Depuis l'accueil (bouton « Lancer AC Evo ») ou la section « Jeu » de
`/settings` :

- chemin de l'exécutable `AssettoCorsaEVO.exe` (bouton « Détecter » pour
  chercher dans les bibliothèques Steam) ;
- si le champ est vide, lancement via Steam (`steam://rungameid/3058630`) ;
- le chemin est enregistré dans `game.json` (ignoré par git).

Le lancement réel du jeu est disponible sous Windows ; sur Mac/Linux, la
logique est testable avec un exécutable quelconque mais le jeu n'existe pas.

## Média (Cider) sur le compteur Cockpit

Le compteur `/dashboard/course/acevo-cockpit` affiche le média en cours à
droite : pochette, titre, artiste, album, progression et boutons tactiles
(précédent / lecture-pause / suivant).

La source est la **session média Windows (SMTC)**, la même que le bloc
Macro Deck « System Media - Cider » : pas de token Cider, pas de configuration.
Cider est prioritaire, sinon la session média courante. Si Cider ne fournit pas
la timeline, la barre de progression et les temps sont masqués.

Sur Mac, le panneau média utilise des données de démo (`?demo`) ; le test réel
se fait sur le PC Windows.

## Studio (compteurs personnalisés)

Ouvre `http://localhost:25555/studio` (bouton **Studio** sur l'accueil).

- Canvas **1024×600** avec grille, sélection, déplacement, redimensionnement.
- Widgets : valeur, texte, jauge, barre, icône, image, forme, track map,
  média Cider, horloge, shift lights, bande de rapports.
- Galerie d'icônes intégrée (dont les icônes maison) + **upload SVG/PNG**.
- Couleurs par rôles du thème ou hex, champ/format/unité par widget.
- **Import SimHub fidèle** (`.simhubdash`, `.zip`, `.djson`) : conserve le
  design d’origine (dégradés, jauges, aiguilles, textes, images) et branche la
  télémétrie dessus. Le dashboard importé est en lecture seule dans le Studio.
  Les images sont copiées dans `custom/imports/`. Le `.djson` seul fonctionne,
  mais l’archive complète est préférable pour les composants et les images.
  Le mode conversion en widgets reste disponible via l’API avec
  `"mode": "widgets"`.
- Sauvegarde, duplication, suppression, import/export JSON, aperçu généré,
  thème de prévisualisation et bouton « Launch on 7" ».
- Un compteur perso apparaît automatiquement dans l'accueil, les réglages,
  le swipe et le catalogue ; il utilise le thème global/compteur existant.

Pour ETS2/ATS, importe le dashboard SimHub `Truck Route Advisor` puis sauvegarde-le.
La zone carte utilise le vrai GPS SimHub. Si le serveur web SimHub n'est pas sur
le port 8888, lance idash avec `IDASH_SIMHUB_API_URL` et
`IDASH_SIMHUB_MAP_URL` adaptés.

Les fichiers générés sont dans `custom/` (ignoré par git) :
`custom/layouts/`, `custom/previews/`, `custom/icons/`,
`custom/imports/`. Le runtime commun est
dans `studio/runtime.js` ; la bibliothèque d'icônes Lucide est sous licence ISC
(voir `studio/ICONS_LICENSE.txt`).

## Mises à jour (sans git)

Deux ZIP sont publiés : `idash-vX.Y.Z-win64.zip` (application .exe) et
`idash-vX.Y.Z.zip` (source, pour les anciennes installations). Les deux
préservent `custom/`, `app.json`, `game.json`, `themes/active.json` et le
profil Chrome.

L'app dispose d'une page **`/update`** (lien « Mise à jour » sur l'accueil et
les réglages) :

1. télécharge le `.zip` de la dernière release depuis
   [GitHub Releases](https://github.com/redasnkrs/idashboard/releases) ;
2. sélectionne-le dans `/update` et clique **Installer et redémarrer** ;
3. l'app remplace le code, **conserve** `custom/`, `game.json`,
   `themes/active.json`, `.profile-7/` et le venv éventuel, puis redémarre.

Le dépôt étant privé, il faut être connecté à GitHub pour télécharger le ZIP.
Le ZIP de release est construit sans git et sans données utilisateur.

### Créer une release

1. Incrémente `VERSION` (ex. `0.6.1`), commit et push.
2. Pousse un tag : `git tag v0.6.1 && git push origin v0.6.1`.
3. Le workflow `.github/workflows/release.yml` construit
   `dist/idash-vX.Y.Z.zip` et crée la release GitHub avec le ZIP.

En local : `python tools/build_release.py` puis upload manuel du ZIP dans une
release GitHub.

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
| `/studio` | éditeur de compteurs personnalisés |
| `/update` | mise à jour par ZIP de release |
| `/api/update/info` | version installée + URL des releases |
| `/api/update/install` | installe un ZIP de release et redémarre (POST) |
| `/dashboard/custom/<id>` | compteur créé dans le Studio |
| `/custom/previews/<id>.svg` | aperçu d'un compteur perso |
| `/custom/icons/<fichier>` | icône perso uploadée |
| `/api/layouts` | liste (GET) / création-mise à jour (POST) des layouts |
| `/api/layouts/<id>` | layout complet (GET) / suppression (DELETE) |
| `/api/icons` | icônes perso (GET/POST) |
| `/stream` | flux SSE à 60 Hz |
| `/api/dash` | dernier état (contrat commun) |
| `/api/dashboards` | catalogue JSON des compteurs + catégories |
| `/api/schema` | version et description du contrat |
| `/api/themes` | thèmes disponibles + état (GET), enregistrement (POST) |
| `/api/themes/active` | thème effectif (`?dashboard=…&game=…&car=…`) |
| `/api/themes/stream` | SSE : numéro de révision du thème |
| `/api/themes/reset` | réinitialise une portée (POST) |
| `/api/launch` | ouvre un compteur sur le mini écran (POST) |
| `/api/game` | état AC Evo (compatibilité) ; `/api/game/detect`, `/api/game/launch` |
| `/api/games` | état des trois jeux (GET) ; `/api/games/<jeu>` (POST), `/detect`, `/launch` |
| `/api/screens` | écrans détectés + écran courant (GET/POST) |
| `/api/app` | version + compteur par défaut (GET/POST) |
| `/api/media` | média Windows en cours (Cider prioritaire) |
| `/api/media/art` | pochette en cache |
| `/api/media/control` | précédent / lecture-pause / suivant (POST) |
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
               (catalogue des compteurs), launcher.py (Chrome sur le 7"),
               nav_snippet.py (balayage tactile), game.py (lancement AC Evo),
               media.py + media_smtc.ps1 (média Windows / Cider),
               studio.py (layouts + icônes personnalisés),
               screens.py (détection des écrans),
               app_settings.py (écran, jeux, compteur par défaut),
               updater.py (ZIP de release + redémarrage)
update/        index.html (page de mise à jour)
tools/         build_release.py (ZIP), apply_update.py (application + relance)
.github/       workflows/release.yml (release auto sur tag vX.Y.Z)
VERSION        version de l'app (affichée dans l'interface)
studio/        index.html + editor.js/css, runtime.js, icons.js (éditeur/runtime)
custom/        layouts/, previews/, icons/  (données utilisateur, hors git)
adapters/      base.py (interface), fake.py (tests), auto.py (détection),
               acevo.py, ac.py + ac_defs.py (AC 2014),
               ams2.py + ams2_defs.py (AMS2, licence dans AMS2_DEFS_LICENSE.txt)
dashboards/    course/acevo-cluster/  compteur complet
               course/acevo-minimal/  compteur minimal
               course/acevo-cockpit/  cockpit 3 colonnes + média
home/          index.html (accueil / catalogue)
settings/      index.html (page de réglages)
themes/        ambre-ivoire.json, rouge-sport.json, vert.json
tests/         tests unitaires et captures Playwright
main.py        point d'entrée
acevo_bridge.py  ancien nom (compatibilité)
```

Ajouter un tableau de bord = ajouter un dossier `dashboards/<catégorie>/<nom>/`
avec `index.html`, `manifest.json` et `preview.png`. Il apparaît tout seul sur
l'accueil et dans les réglages. Pour un compteur personnalisé, passe par
`/studio` (widgets, grille, icônes) : il sera aussi ajouté automatiquement.
Ajouter un jeu = écrire un adaptateur qui respecte `adapters/base.py`.

## Tests

```
python -m unittest discover -s tests -v
python -m tests.visual_check     # captures 1024x600/560, accueil, réglages,
                                 # studio, compteur perso, mise à jour, previews
```
