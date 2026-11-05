# Tableau de bord télémétrie pour mini écran : contexte et feuille de route

> **Pour les assistants IA (Claude, Cursor, Copilot, opencode…)** : lis ce fichier en entier avant de toucher au code. Il décrit le projet, ce qui existe réellement, ce qui est vérifié ou non, et ce qu'il reste à faire. Mets-le à jour à chaque étape terminée (cases à cocher, section « Faits vérifiés »).
>
> Nom du projet : à définir. Auteur : Reda. Dernière mise à jour : 2026-11-05.

## 1. Le projet

Un tableau de bord de voiture (compteur analogique, vitesse, rapport, shift lights, clignotants, phares, carburant, températures, temps au tour…) affiché sur un **mini écran 7" (1024x600)** posé à côté de l'écran principal, alimenté en temps réel par la télémétrie d'**Assetto Corsa Evo**.

**Objectif final** : une vraie application Windows avec de **vrais menus**. On y navigue par **catégories** (Course, Aviation, …) puis par jeu (AC Evo, iRacing, MSFS, DCS…), on choisit parmi **plusieurs compteurs / tableaux de bord** pour chaque jeu, on les lance sur le mini écran, et on **personnalise les couleurs et les blocs sans modifier le HTML**.

## 2. Environnement de l'utilisateur (contraintes réelles)

- Windows 11 (interface en anglais), PC de jeu. Écran principal 2560x1440, mini écran 7" 1024x600 placé en bas à droite (coordonnées Windows : **X=2560, Y=834**, vérifié avec `System.Windows.Forms.Screen`).
- Python **3.15** installé (`C:\Users\reda\AppData\Local\Python\pythoncore-3.15-64\python.exe`) avec le paquet `acevo-sdk` 0.2.1.
- Navigateur principal : **Zen**. Le tableau de bord s'ouvre dans une fenêtre **Chrome** dédiée (`--app`, profil séparé `C:\MapDeck\profile`) pour ne pas gêner Zen.
- **Macro Deck 3** tourne sur le 7" (boutons de raccourcis, maps de jeux). Le plugin « ETS2/ATS Telemetry » a été essayé puis abandonné (voir décisions).
- L'utilisateur est développeur junior (React, Next.js, Tailwind, Node/Express, un peu de Python). Il préfère des réponses **courtes, directes, en français informel**.
- Le jeu et la mémoire partagée n'existent que sous Windows. L'environnement où travaillent certaines IA (Linux) ne peut **pas** lire le jeu : on teste avec une fausse source de données (voir §8).

## 3. État actuel (ce qui existe et fonctionne)

Dépôt Git : `github.com/redasnkrs/idashboard` (privé). Sur le PC de jeu, on
clone le dépôt (`C:\MapDeck\` ou ailleurs) puis on lance `lancer.bat` (ou
`python main.py`).

Structure après la Phase 2 :

| Chemin | Rôle |
|---|---|
| `main.py` | Point d'entrée (`--fake`, `--debug`, `--port`). |
| `core/schema.py` | Contrat de données (`SCHEMA_VERSION = 1`) et validation. |
| `core/config.py` | Port, fréquences, chemins, résolution des tableaux de bord. |
| `core/pump.py` | Boucle de lecture 60 Hz et état partagé. |
| `core/server.py` | Serveur HTTP + flux SSE. |
| `core/themes.py` | Palettes, résolution par jeu/voiture, sauvegarde, diffusion. |
| `adapters/acevo.py` | Source AC Evo (mémoire partagée, structures `ctypes`). |
| `adapters/fake.py` | Fausse source animée pour Mac/Linux/tests. |
| `adapters/base.py` | Interface commune des sources (`read()`, `ets2()`). |
| `dashboards/course/acevo-cluster/` | `index.html` + `manifest.json` + `preview.png` (compteur à aiguille centrale). |
| `settings/index.html` | Page de réglages avec aperçu live. |
| `themes/*.json` | `ambre-ivoire`, `rouge-sport`, `vert`. `active.json` = choix utilisateur (hors git). |
| `acevo_bridge.py` | Ancien nom, conservé en compatibilité (`python acevo_bridge.py`). |
| `lancer.bat` | Lancement double-clic sous Windows. |

Fichiers de l'ancienne version qui n'existent pas et ne sont donc pas dans le
dépôt : `dashboard_twin.html` et `close.ps1`. `map.ps1` reste à importer s'il
est utilisé sur le PC.

### 3.1 Le pont (`core/` + `adapters/`)

- `adapters/acevo.py` lit trois régions de mémoire partagée Windows via `acevo.RegionReader` : `acevo_pmf_physics` (1024 o), `acevo_pmf_graphics` (4096 o), `acevo_pmf_static` (2048 o). Chemin `Local\<nom>`.
- **Physique** : `acevo.decode_physics()` renvoie un dictionnaire. **Graphique et statique** : structures `ctypes` écrites à la main (`GraphicsEvo`, `StaticEvo`) d'après le layout de la crate Rust `kerb` (`SPageFileGraphicsEvo`). Les sous-structures à taille fixe sont lues comme des blocs d'octets. `sizeof(GraphicsEvo)` = 3128 octets.
- `core/pump.py` fait la boucle de lecture à 60 Hz dans un thread. La page statique n'est relue que toutes les 2 s. Si le jeu est fermé, l'état devient `{"c": false}`.
- `core/server.py` est le serveur HTTP (`ThreadingHTTPServer`, HTTP/1.1, connexions persistantes) sur `127.0.0.1` **et** `::1` (voir pièges). Local uniquement.

| Route | Contenu |
|---|---|
| `/dashboard` | Sert le tableau de bord par défaut (`course/acevo-cluster/index.html`, relu à chaque requête : pas besoin de relancer le pont pour le modifier). |
| `/dashboard/<catégorie>/<nom>` | Sert `dashboards/<catégorie>/<nom>/index.html`. `/dashboard/<nom>` marche aussi si le nom est unique. Ajouter un dossier suffit à ajouter un tableau de bord. |
| `/dashboard/<catégorie>/<nom>/manifest.json` | Métadonnées du tableau de bord (nom, catégorie, jeu, taille, contrats). |
| `/dashboard?demo` ou `?demo=<secondes>` | Même page avec des données simulées, sans le jeu (marche aussi sur `/dashboard/<nom>`). |
| `/settings` | Page de réglages (couleurs, unités, blocs) avec aperçu live. |
| `/stream` | Flux SSE, un message `data: <json>` toutes les 1/60 s (sert aussi de heartbeat). |
| `/api/dash` | Dernier état au format du tableau de bord (JSON). |
| `/api/schema` | Version et description du contrat de données. |
| `/api/themes` | `GET` : palettes + état ; `POST` : enregistre un thème (global, jeu ou voiture). |
| `/api/themes/active` | Thème effectif, résolu avec `?game=…&car=…`. |
| `/api/themes/stream` | SSE : numéro de révision ; les pages rechargent leur thème, sans rechargement de page. |
| `/api/ets2/telemetry` (et `/`) | Format du « ETS2 Telemetry Server », pour le plugin Macro Deck si besoin. |

### 3.2 Le tableau de bord (`dashboards/course/acevo-cluster/index.html`)

- `viewBox="0 0 1024 600"`, `preserveAspectRatio="xMidYMid meet"` : s'adapte à la fenêtre (une fenêtre `--app` 1024x600 a une barre de titre, donc la zone utile est plus basse ; tester aussi à 1024x560).
- Compteur central (centre 512,324, rayon 260) : graduations générées selon `rm` (RPM max), zone rouge à 89 %, anneau lumineux de 54 segments, aiguille, vitesse en grand, rapport, barres de pédales.
- 27 shift lights en haut (remplies des bords vers le centre entre 72 % et 98 % des RPM max, clignotement au-delà de ~97 %).
- Colonne gauche : voiture, carburant (20 segments, litres, tours restants), eau, huile, pression d'huile, turbo, voyants (feux de croisement, feux de route, frein à main, limiteur de pit).
- Colonne droite : circuit, temps du tour en cours (+ delta), meilleur, dernier, position, pastilles TC / ABS / balance de freinage.
- Flèches de clignotants en haut. Le jeu envoie un état **fixe** : le battement (350 ms allumé / 350 ms éteint) est fait dans la page.
- Écran « En attente d'Assetto Corsa Evo » si aucun message depuis 2 s. Un clic bascule le plein écran.
- Rendu : un `requestAnimationFrame`, lissage exponentiel des valeurs (RPM, vitesse, pédales), écriture dans le DOM uniquement quand une valeur change.
- Police : **Bahnschrift** (présente sur Windows 10/11), avec police de secours.
- Style : fond noir, chiffres ivoire, aiguille et anneau ambre, zone rouge ; pas de cartes arrondies, colonnes ouvertes séparées par des filets.
- **Thème** : toutes les couleurs viennent de `themes/*.json` (variables CSS, objet `C` en JavaScript, dégradés SVG et valeurs des composants). La page charge `/api/themes/active`, écoute `/api/themes/stream` et applique les changements à chaud. Les unités (km/h ↔ mph, °C ↔ °F) et les blocs visibles (`car`, `fuel`, `water`, …) viennent aussi du thème.

## 4. Contrat de données (format `/stream` et `/api/dash`)

Le contrat est déclaré dans `core/schema.py` (`SCHEMA_VERSION = 1`) et exposé par `/api/schema`. Les tests vérifient qu'une source le respecte.

Une valeur inconnue ou incohérente vaut `null` (la page affiche `--`). Les clés sont courtes volontairement (60 messages par seconde).

| Clé | Type | Sens |
|---|---|---|
| `c` | bool | jeu connecté (si `false`, c'est la seule clé présente) |
| `st` | int | état : 0 arrêt, 1 replay, 2 en direct, 3 pause |
| `v` | nombre | vitesse affichée, km/h |
| `r`, `rm` | nombre | régime et régime maximum, tr/min |
| `g` | int | rapport : -1 marche arrière, 0 point mort, 1…n |
| `gas`, `brk`, `clu`, `hb` | 0..1 | accélérateur, frein, embrayage, frein à main |
| `fuel`, `fp`, `fpl`, `laps` | nombre | carburant en litres, fraction 0..1, litres par tour, tours restants (0 si inconnu) |
| `low`, `high` | bool | feux de croisement, feux de route |
| `L`, `R`, `haz` | bool | clignotants gauche, droit, warnings (état fixe, pas le battement) |
| `pit`, `pitlane` | bool | limiteur de pit actif, voiture dans la voie des stands |
| `tc`, `abs`, `esc` | bool | aide en train d'agir |
| `lim`, `up`, `run` | bool | limiteur de régime, indicateur de passage de rapport, moteur tournant |
| `wt`, `ot` | nombre ou null | température d'eau et d'huile, °C |
| `op`, `boost` | nombre ou null | pression d'huile, turbo, bar |
| `lap`, `last`, `best`, `delta` | int | tour en cours, dernier, meilleur, delta, en millisecondes (≤ 0 ou énorme = inconnu) |
| `valid` | bool | tour valide |
| `pos`, `nd` | int | position et nombre de pilotes |
| `tcl`, `absl` | int ou null | niveau de TC et d'ABS réglés |
| `bb` | nombre ou null | balance de freinage, % |
| `car`, `track`, `cfg` | texte | voiture, circuit, configuration (majuscules, `_` remplacés par des espaces) |

Le format `/api/ets2/telemetry` est un second format, indépendant, calqué sur l'API du serveur ETS2 (`game`, `truck`, `navigation`, `trailer`, `job`).

> **Ce contrat est celui de la catégorie Course.** Chaque catégorie (par exemple Aviation : altitude, vitesse, cap, assiette, etc.) aura son **propre contrat**, déclaré dans le `manifest.json` de ses tableaux de bord. Ne pas mélanger les clés d'une catégorie dans une autre.

## 5. Faits vérifiés, non vérifiés, pièges

### Vérifié en jeu par l'utilisateur
- Vitesse, régime, carburant : valeurs correctes.
- **Rapport** (physique `gear`) : 0 = marche arrière, 1 = point mort, 2 = première. Le pont convertit (`g = raw - 1`, sauf R et N).
- **Phares** (`main_light_stage`) : 0 éteint, 1 croisement, 2 route.
- **Clignotants** : le jeu envoie un état **fixe** (pas de battement). Corrigé côté page.
- Retour global de l'utilisateur le 2026-11-04 : le tableau de bord fonctionne très bien en jeu.

### Vérifié hors jeu (Mac, fausse source)
- Phase 1 : les 16 tests passent (`python -m unittest discover -s tests -v`) et les captures Playwright 1024x600 / 1024x560 montrent le même design qu'avant.
- `core/schema.py` valide la sortie de `adapters/fake.py` et l'état déconnecté `{"c": false}`.
- Phase 2 : 27 tests passent. Captures Playwright des 3 thèmes à 1024x600 et 1024x560. Une couleur changée dans `/settings` est enregistrée et appliquée dans l'aperçu sans rechargement (vérifié via Playwright, aucune erreur JS). Unités mph/°F et masquage de blocs vérifiés.

### Vérifié sur le PC de l'utilisateur
- 2026-11-05 : après `git pull`, `lancer.bat` démarre le pont et le compteur s'affiche correctement sur le 7" depuis la nouvelle structure (vraie source AC Evo). Phase 1 confirmée.

### Pas vérifié valeur par valeur (layout issu de `kerb`, lecture cohérente mais à confirmer)
Nom de la voiture et du circuit, temps au tour (dernier, meilleur, delta), position, niveaux TC/ABS, balance de freinage, températures d'eau et d'huile, frein à main, voie des stands. Pour confirmer : lancer `python acevo_bridge.py --debug` et regarder la ligne affichée toutes les 0,5 s.

### Pièges déjà rencontrés (ne pas les refaire)
- **Plugin Macro Deck ETS2** : il interroge le serveur toutes les 200 ms (5 Hz) → aiguille saccadée. C'est pour ça que le tableau de bord est une page web à 60 Hz.
- **`localhost` sous Windows** peut être résolu en IPv6 (`::1`) : le serveur écoute donc sur les deux, et les connexions sont persistantes (sinon retard à chaque requête).
- **Pourcentages ambigus** (0..1 ou 0..100 selon les champs) : la fonction `frac()` normalise.
- Les chaînes lues dans la mémoire partagée sont filtrées (ASCII imprimable) ; sinon vide.
- Le `--app` de Chrome inclut la barre de titre dans `--window-size` : ne pas dessiner à 600 px de haut fixe, rester en `viewBox`.
- Le shell de certaines IA est Linux : `python acevo_bridge.py` s'arrête volontairement (`sys.platform != "win32"`).

## 6. Décisions prises (pour ne pas les rediscuter)

1. **Lecture seule** de la mémoire du jeu. On n'écrit jamais dedans.
2. **SSE** plutôt que WebSocket : unidirectionnel, tient dans la bibliothèque standard.
3. **SVG + JavaScript sans dépendance** pour les tableaux de bord : pas d'étape de build, fonctionne hors ligne, s'adapte à toute taille d'écran.
4. **Fenêtre Chrome `--app` dédiée** pour afficher le tableau de bord : position contrôlée sur le 7", n'interfère pas avec Zen.
5. **Architecture en trois couches** : sources (une par jeu) → format de données commun → tableaux de bord. Ajouter un jeu = écrire une source, sans toucher au design.
6. Le cœur reste en **Python + web** : menus, réglages et lanceur sont des pages HTML servies par le pont (fenêtre d'app via Chrome `--app` ou `pywebview`, icône de barre des tâches via `pystray`, emballage via `PyInstaller`). Un portage du cœur en **Rust avec Tauri** reste une **option** pour la Phase 6 ; les tableaux de bord HTML ne changeraient pas.

## 7. Feuille de route

Chaque phase est utilisable seule. Ne commencer la suivante que si la précédente est terminée et testée.

### Phase 0 : preuve de concept ✅
- [x] Pont mémoire partagée → HTTP, tableau de bord compteur, mode démo, flux 60 Hz
- [x] Clignotants qui battent, écran d'attente, plein écran au toucher

### Phase 1 : mettre de l'ordre (fondations) ✅
- [x] Structurer le dépôt (voir arborescence cible ci-dessous) et le mettre sous Git
- [x] Extraire le contrat de données dans un module (`core/schema.py`) avec un numéro `schema_version` (ajouter des clés = compatible ; renommer = version majeure)
- [x] Séparer le pont en : source AC Evo, serveur HTTP, configuration
- [x] Ajouter des tests : fausse source + captures Playwright à 1024x600 et 1024x560
- [x] `README.md` d'installation et de lancement (un `.bat` double-cliquable)
- **Terminé quand** : les tests passent, le tableau de bord se lance depuis la nouvelle structure sans rien changer visuellement. *(confirmé sur le PC le 2026-11-05)*

### Phase 2 : thèmes et réglages (sans toucher au HTML) ✅
- [x] **Centraliser toutes les couleurs** dans un objet de thème unique (variables CSS + JS lisant les mêmes valeurs), supprimer les valeurs en dur
- [x] Format de thème en JSON : couleurs, police, unités (km/h ↔ mph, °C ↔ °F), blocs à afficher ou masquer
- [x] Route `/api/themes` (lire / enregistrer) ; le tableau de bord charge le thème au démarrage et l'applique en direct
- [x] Page de réglages (`/settings`) : sélecteurs de couleur, aperçu en direct, enregistrement par jeu et par voiture
- [x] 3 thèmes fournis : ambre/ivoire (actuel), rouge sport, vert
- **Terminé quand** : on change une couleur dans la page de réglages et le 7" se met à jour sans rechargement manuel ni édition de fichier. *(vérifié hors jeu ; à confirmer sur le PC)*

### Phase 3 : le lanceur
- [ ] Détection automatique du mini écran (par résolution 1024x600, ou choix dans les réglages) : plus de X/Y à la main
- [ ] **Menu en catégories** (Course, Aviation, …) → jeux → tableaux de bord, avec **plusieurs compteurs au choix par jeu**. Chaque tableau de bord a un `manifest.json` (nom, catégorie, jeu, taille, aperçu, contrat de données utilisé) ; ajouter un dossier suffit à l'ajouter au menu
- [ ] Bouton « Lancer sur le 7" » et mémorisation du dernier compteur choisi par jeu
- [ ] Icône dans la barre des tâches, démarrage automatique avec Windows
- [ ] Lancement automatique quand le jeu démarre (nom du processus d'AC Evo **à vérifier** sur le PC)
- **Terminé quand** : un clic (ou le lancement du jeu) ouvre le bon tableau de bord sur le bon écran.

### Phase 4 : deuxième jeu (valide l'architecture)
- [ ] Définir l'interface d'une source : `read() -> dict | None` au format du §4
- [ ] Source **iRacing** (bibliothèque `pyirsdk`, mémoire partagée aussi), réutilisant le même tableau de bord
- [ ] Ce qui manque dans le format commun est ajouté en clés optionnelles, sans casser AC Evo
- [ ] **Catégorie Aviation** : source (MSFS via SimConnect, ou DCS), **nouveau contrat de données** dédié à l'avion, et au moins un tableau de bord d'instruments (altitude, vitesse, cap, horizon artificiel)
- **Terminé quand** : le même compteur fonctionne avec iRacing en changeant seulement la source, et la catégorie Aviation apparaît dans le menu avec son propre tableau de bord.

### Phase 5 : contenu des tableaux de bord
- [ ] Pneus (température, pression, usure) et températures de freins
- [ ] Écarts avec la voiture devant et derrière
- [ ] Secteurs avec couleurs violet / vert / jaune
- [ ] Historique des derniers tours avec l'écart de régularité
- [ ] Drapeaux (jaune, bleu, damier) et alertes plein écran (carburant bas, surchauffe, limiteur de pit)
- [ ] Plusieurs pages tactiles (conduite, pneus, chrono, carte)
- [ ] Carte du circuit avec la position des voitures
- [ ] Dégâts de la voiture
- Chaque nouvelle donnée du jeu : vérifier avec `--debug` sur le PC de l'utilisateur et l'ajouter au §5.

### Phase 6 : application de bureau
- [ ] Choisir : rester en Python (PyInstaller ; utiliser un Python 3.12 ou 3.13 si la 3.15 n'est pas encore supportée par les outils d'emballage) **ou** porter le cœur en Rust avec Tauri (interface React + Tailwind, ce que l'utilisateur maîtrise)
- [ ] Interface : liste des tableaux de bord, réglages, état de la connexion au jeu
- [ ] Installateur `.exe` et mises à jour
- **Terminé quand** : quelqu'un sans Python installé peut l'installer et obtenir le tableau de bord.

### Phase 7 : optionnel
- Éditeur de disposition par glisser-déposer
- Panneau d'avion (MSFS via SimConnect, DCS)
- Boutons de pilotage via Macro Deck (envoi de touches : TC, ABS, balance de freinage, essuie-glaces, pit)
- Enregistrement de la télémétrie en fichier pour comparer les tours
- Publication GitHub propre (README avec captures, licence, release)

### Arborescence actuelle (après Phase 2)

```
idashboard/
  core/          schema.py (contrat), config.py, pump.py, server.py,
                 themes.py (palettes, résolution, diffusion)
  adapters/      base.py, acevo.py, fake.py  (iracing.py plus tard)
  dashboards/    course/acevo-cluster/  index.html + manifest.json + preview.png
                 aviation/…  (plus tard : un dossier par catégorie, un sous-dossier par compteur)
  settings/      index.html (réglages + aperçu live)
  themes/        ambre-ivoire.json, rouge-sport.json, vert.json
                 active.json (choix utilisateur, hors git)
  tests/         test_schema.py, test_server.py, test_themes.py, visual_check.py
  main.py        point d'entrée
  acevo_bridge.py  compatibilité (ancien nom)
  lancer.bat
  README.md
  Mini Deck App Roadmap.md
```

Dossiers prévus plus tard : `launcher/` (Phase 3), `app/` (Phase 6).

## 8. Règles pour les IA qui travaillent sur ce projet

- **Parle à l'utilisateur en français informel, court et direct.** Pas de longues explications ; dis ce qui a changé et ce qu'il doit faire sur son PC.
- Ne casse pas le contrat de données (§4) : on **ajoute** des clés, on ne renomme pas. Valeur inconnue → `null`, jamais une valeur inventée.
- **Ne devine jamais la structure mémoire du jeu.** Toute nouvelle donnée se vérifie en jeu avec `--debug`, puis se note dans « Vérifié » (§5).
- Pas de CDN ni de dépendance lourde dans les tableaux de bord. Pas d'étape de build pour eux.
- Garde les performances : un seul `requestAnimationFrame`, n'écrire dans le DOM que si la valeur change, pas de filtre SVG sur beaucoup d'éléments animés.
- Un tableau de bord doit rester lisible à 1024x600 **et** 1024x560 (fenêtre avec barre de titre).
- Lecture seule du jeu. Ne jamais écrire dans sa mémoire.
- Ne propose pas de réécrire en autre langage ou autre framework sans raison forte : voir « Décisions » (§6).
- Après chaque changement visuel, fais une capture (Playwright) et regarde-la avant de dire que c'est fini.

### Comment tester sans le jeu (environnement Linux ou sans AC Evo)
1. `python main.py --fake` : utilise `adapters/fake.py`, aucune dépendance Windows, mêmes routes qu'en vrai.
2. `python -m tests.visual_check` : captures Playwright à 1024x600 et 1024x560 via le serveur.
3. Pour juste voir le design : `dashboards/course/acevo-cluster/index.html?demo=<secondes>` (aucun serveur nécessaire).
4. Tests : `python -m unittest discover -s tests -v`. Débit du flux : ~60 messages `data:` par seconde sur `/stream`.

### Pour démarrer une tâche avec une IA
> Lis `ROADMAP.md`. On travaille sur **la Phase X, étape Y**. Respecte les règles du §8. Dis-moi ce que tu changes et ce que je dois tester sur mon PC.

## 9. Idées en vrac (pas planifiées)
Thème nuit automatique, son de changement de rapport, mode « course » / « qualification », surcharge des seuils d'alerte par voiture, profils par jeu, partage de thèmes entre utilisateurs.
