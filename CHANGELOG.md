# Changelog

Toutes les versions notables d'idash. Le format s'inspire de Keep a Changelog.
La section correspondant à `VERSION` est utilisée automatiquement comme notes
de release GitHub.

## [0.9.4] - 2026-11-09

### Corrigé
- Détection HID : idash essaie maintenant toutes les interfaces du bandeau
  (plus seulement l’interface 0) et privilégie les périphériques
  « light / Robobloq / DX ».
- Message d’erreur plus précis quand un périphérique HID est trouvé mais ne
  peut pas être ouvert.

## [0.9.3] - 2026-11-09

### Ajouté
- Support des bandeaux **série USB CDC** en plus du HID, avec détection
  automatique des ports `VID 1A86`.
- Diagnostic dans `/settings` : nombre de périphériques HID/série détectés et
  message clair quand aucun bandeau n’est trouvé.

### Corrigé
- Plus d’erreur `NoneType` quand l’énumération HID ne renvoie rien.

## [0.9.2] - 2026-11-09

### Corrigé
- Les réglages Ambient lights (cases et nombres) ne se réinitialisent plus
  instantanément : `app.json` recharge maintenant la section `ambient`.

## [0.9.1] - 2026-11-09

### Ajouté
- Case **Clignotants** dans les réglages ambient : on peut désactiver les
  clignotants tout en gardant le régime, les drapeaux ou le frein.

### Modifié
- Les effets ambient sont maintenant activables indépendamment :
  clignotants, régime, drapeaux, frein.

## [0.9.0] - 2026-11-09

### Ajouté
- Contrôle direct des bandeaux **Robobloq / DX Light** en USB HID, sans passer
  par l’application DX Light.
- Clignotants gauche/droite et feux de détresse sur la moitié correspondante
  du bandeau, régime moteur en barre colorée, drapeaux de course (jaune, bleu,
  rouge, drapeau à damier…) et frein.
- Réglages `/settings` → Jeux : activation, nombre de LED (auto), part
  gauche, luminosité, FPS, inversion gauche/droite et tests.
- Nouvelle clé de télémétrie `flag` pour AC 2014, AMS2 et AC Evo.

### Modifié
- Le bandeau doit être libre : fermer DX Light avant d’activer le contrôle
  idash.

## [0.8.3] - 2026-11-09

### Modifié
- Génération ts-map : choix de qualité **0-6 / 0-7 / 0-8**.
  0-7 est le réglage recommandé pour le 7" (beaucoup plus rapide et léger
  que 0-8).
- Progression réelle **tuile par tuile** au lieu de sauter de 89 % à 100 %.
- Le générateur affiche « Génération des tuiles… » pendant le zoom en cours.

## [0.8.2] - 2026-11-09

### Ajouté
- Générateur **ts-map intégré** : lit `base.scs`, les DLC et ProMods, puis
  produit un pack de tuiles 512 px avec noms de villes, logos et vraies rues
  de carrefours.
- Bouton `/settings` → Jeux → **Générer** avec détection automatique du
  dossier ETS2 et du fichier ProMods.
- Progression de génération et activation automatique du pack
  `custom/maps/tsmap-promods.zip`.

### Modifié
- La carte utilise en priorité les tuiles ProMods fidèles ; la carte
  vectorielle reste le fallback immédiat.

## [0.8.1] - 2026-11-09

### Ajouté
- Carte ETS2 **vectorielle ProMods** : routes, jonctions et villes extraites
  des fichiers de carte du jeu, avec zoom, déplacement tactile et camion
  temps réel. Plus de capture d’écran, plus de dépendance à SimHub.
- La carte vectorielle est incluse dans `assets/maps/ets2-vector.json.gz` et
  servie par `/api/ets2/vector`.

### Supprimé
- Le mode « GPS par capture écran » et ses réglages, remplacés par la carte
  vectorielle.

### Modifié
- La carte en tuiles reste le fallback si la carte vectorielle est absente.

## [0.8.0] - 2026-11-09

### Ajouté
- Mode **GPS ETS2 par capture écran** : capture la zone du GPS in-game et
  l’affiche dans le Route Advisor. ProMods et itinéraire sont donc visibles
  exactement comme dans le jeu, sans pack de tuiles.
- Sélecteur de zone dans `/settings` à partir d’une capture du bureau.
- Réglage X/Y/largeur/hauteur + activation de la capture.

### Modifié
- La carte en tuiles reste le fallback quand la capture est désactivée.

## [0.7.9] - 2026-11-09

### Ajouté
- Support d’un pack de tuiles personnalisé `custom/maps/tsmap-promods.zip`,
  détecté automatiquement avant la carte de base.
- Support des tuiles 512 px pour une meilleure qualité de carte.
- Les fichiers `.scs` sont ignorés par git (mods trop volumineux).

### Modifié
- La documentation explique comment générer une carte ProMods avec ts-map.

## [0.7.8] - 2026-11-09

### Modifié
- Carte ETS2 : zoom par défaut plus proche (niveau 8).
- Zoom tactile jusqu’à 2 niveaux au-delà des tuiles natives (niveaux 9 et 10)
  par agrandissement des tuiles, pour voir les routes de près.

## [0.7.7] - 2026-11-09

### Ajouté
- Carte ETS2 tactile : zoom par pincement, déplacement au doigt et
  recentrage par double-tap.
- Zoom molette sur ordinateur.
- Zoom par défaut plus proche du camion (niveau 7).

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
