# Changelog

Toutes les versions notables d'idash. Le format s'inspire de Keep a Changelog.
La section correspondant à `VERSION` est utilisée automatiquement comme notes
de release GitHub.

## [0.7.6] - 2026-11-09

### Corrigé
- Carte ETS2 : utilisation de la coordonnée `coordinateZ` (axe nord-sud) et
  inversion correcte de l’axe Y des tuiles. La position correspond maintenant
  à la ville réelle (testé à Calais).
- Carburant : la propriété SimHub `FuelPercent` est maintenant reconnue, donc
  la jauge se remplit correctement.
- Carte : redessin régulier pendant le chargement des tuiles pour éviter une
  zone vide au premier affichage.

## [0.7.5] - 2026-11-09

### Corrigé
- Carte ETS2 : si la position reçue est invalide ou hors des limites de la
  carte, idash recentre la vue au lieu d’afficher une zone grise.
- Zoom de carte plus robuste autour du camion.
- Carburant : fallback lorsque la capacité du réservoir n’est pas fournie par
  le plugin ; la capacité est aussi exposée dans `/api/dash` pour diagnostic.

## [0.7.4] - 2026-11-09

### Ajouté
- Installation du plugin SCS SDK depuis `/settings` → Jeux, pour lire
  ETS2/ATS sans SimHub.
- Installation locale de la carte ETS2 depuis la même page.

### Corrigé
- Les dashboards SimHub fidèles ne sont plus bloqués par l’écran
  « Waiting for Assetto Corsa Evo » quand la télémétrie n’est pas encore là.
  Le compteur reste affiché avec un petit bandeau d’attente.
- Le message d’attente utilise le jeu du dashboard (ETS2) au lieu d’AC Evo.

## [0.7.3] - 2026-11-09

### Corrigé
- Studio : la sauvegarde d’un dashboard SimHub fidèle contenant une carte ne
  renvoie plus « SVG non autorisé ». Le `foreignObject` de la carte est retiré
  de l’aperçu SVG, pas du dashboard.

## [0.7.2] - 2026-11-09

### Ajouté
- Télémétrie ETS2/ATS directe via `Local\SCSTelemetry` (`truck-telemetry`),
  sans lancer SimHub.
- Carte GPS ETS2 locale rendue par idash à partir des tuiles `tsmap-ets2.zip`.
- Installation de la carte depuis `/settings` : copie depuis SimHub ou
  téléchargement unique (~87 Mo) dans `custom/maps/`.
- Affichage Route Advisor : position/cap du camion, limite de vitesse, heure
  du jeu, vitesse, rapport, carburant, destination, ETA, usure camion /
  remorque / cargaison, clignotants et repos.
- Champs ETS2 supplémentaires dans le contrat commun (`map_x`, `map_y`,
  `map_heading`, `wear_*`, `speed_limit`, `game_time`, etc.).

### Modifié
- La source SimHub devient un fallback optionnel pour ETS2/ATS.
- La carte n'utilise plus le serveur SimHub en exécution.

## [0.7.1] - 2026-11-09

### Ajouté
- Ouverture automatique du dernier compteur sur le 7" au lancement.
- Optimisations tactiles : cibles 40–44 px, champs plus grands, meilleure
  gestion du zoom Chrome.
- ETS2 ajouté aux jeux configurables et à la détection automatique.
- Import du dashboard SimHub `Truck Route Advisor`.

### Modifié
- Source/carte ETS2 via SimHub en transition (remplacé en 0.7.2).

## [0.7.0] - 2026-11-06

### Ajouté
- Application Windows portable `idash.exe` construite par PyInstaller.
- Icône tray, démarrage avec Windows, instance unique.
- Logs rotatifs, `/api/health`, diagnostic et redémarrage.
- Watchdog optionnel pour rouvrir la fenêtre du 7".
- Mise à jour compatible exe avec helper `idash-update.exe`.
- Build Windows et publication de release via GitHub Actions.

## [0.6.3] - 2026-11-06

### Ajouté
- Mode d'import SimHub fidèle : le dashboard d'origine est conservé
  (dégradés, jauges, textes, images) et la télémétrie est branchée dessus.
- Import des dashboards SimHub en lecture seule dans le Studio.

## [0.6.2] - 2026-11-06

### Ajouté
- Premier importeur SimHub (`.simhubdash`, `.zip`, `.djson`) vers widgets
  idash, avec copie locale des images et rapport des éléments ignorés.

## [0.6.1] - 2026-11-06

### Ajouté
- Détection des écrans Windows et sélection du 7".
- Gestion des jeux AC Evo, AC 2014 et AMS2 : chemins, détection Steam,
  lancement.
- Page Réglages à onglets.

## [0.6.0] - 2026-11-06

### Ajouté
- Mises à jour sans git : page `/update`, ZIP de release GitHub,
  installation et redémarrage.
- Préservation des données utilisateur (`custom/`, thèmes, `app.json`,
  profil Chrome).
