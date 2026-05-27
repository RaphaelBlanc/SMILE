# Technologies et Bibliothèques utilisées pour le jeu SMILE

Ce document détaille les différentes technologies et bibliothèques Python utilisées pour concevoir le jeu SMILE. Ces outils ont été soigneusement choisis pour offrir des performances optimales, une expérience fluide et un code modulaire.

## 🎮 Moteur de jeu et Graphismes

### 1. Pygame (v2.6.1)
- **Pourquoi ?** Pygame est la bibliothèque de référence en Python pour la création de jeux vidéo 2D.
- **Comment ?** Elle est le cœur du projet. Nous l'utilisons pour gérer la boucle principale du jeu (`main loop`), capturer les entrées du joueur (clavier, souris), afficher les fenêtres (avec un redimensionnement dynamique géré par `pygame.RESIZABLE | pygame.SCALED`), gérer les collisions entre les objets (`pygame.sprite.Sprite`), et diffuser la musique.

### 2. PyTMX (v3.32)
- **Pourquoi ?** Concevoir des niveaux directement en code est complexe et peu visuel. Nous utilisons le logiciel externe *Tiled* pour dessiner nos cartes, qui génère des fichiers `.tmx`.
- **Comment ?** PyTMX sert de pont entre nos fichiers de carte (comme `Surface.tmx`, `ZoneLave.tmx`) et Pygame. Il lit les données de la carte, les calques (layers), et les objets de collisions pour les afficher et les intégrer automatiquement dans notre moteur physique.

---

## 🎥 Vidéo et Multimédia

### 3. OpenCV-Python (`cv2`)
- **Pourquoi ?** Pygame possède des limites pour la lecture native de fichiers vidéo complexes (comme les cinématiques d'introduction).
- **Comment ?** OpenCV, spécialisé dans le traitement d'images, décode notre cinématique d'introduction (`videointro.mp4`) image par image à très haute vitesse. Ces images sont redimensionnées et affichées en temps réel sur la fenêtre Pygame.

### 4. MoviePy
- **Pourquoi ?** OpenCV gère très bien l'image, mais pas le son d'une vidéo.
- **Comment ?** MoviePy est utilisé en complément pour extraire et jouer la piste audio de nos cinématiques de manière synchronisée avec le défilement des images d'OpenCV.

### 5. NumPy
- **Pourquoi ?** C'est une dépendance vitale pour traiter de gros volumes de données numériques.
- **Comment ?** Utilisée de manière transparente en arrière-plan par OpenCV et MoviePy pour manipuler les pixels de la vidéo sous forme de matrices mathématiques ultra-rapides.

---

## 🌐 Multijoueur et Réseau

### 6. WebSockets (`websockets`)
- **Pourquoi ?** Le jeu propose un mode multijoueur où les actions doivent être synchronisées instantanément.
- **Comment ?** Cette bibliothèque permet d'établir une connexion bidirectionnelle en temps réel avec notre serveur relais externe (`wss://smile-relay.onrender.com`). Elle envoie et reçoit la position des joueurs et des attaques sans latence perceptible.

### 7. Asyncio & Threading
- **Pourquoi ?** L'attente des messages réseau bloquerait la boucle d'affichage de Pygame, causant des "gels" (freezes) de l'image.
- **Comment ?** Le module `threading` crée un processus en arrière-plan. Dans ce thread, `asyncio` gère la communication réseau de manière asynchrone (non bloquante). Le jeu reste fluide à 60 FPS tout en communiquant avec le serveur réseau en permanence.

---

## 🛠️ Outils Standard Python

Ces bibliothèques sont incluses nativement dans Python et sont au cœur de la logique du jeu :

- **`math` et `random`** : Utilisées pour l'intelligence artificielle des boss. Elles calculent les trajectoires des projectiles (via la trigonométrie : sinus/cosinus), rendent les attaques imprévisibles, et génèrent les systèmes de particules (étincelles, poussière).
- **`json`** : Utilisé pour sauvegarder et charger la progression du joueur (système de `save_X.json`), ainsi que pour formater les données de position envoyées par le réseau multijoueur.
- **`os` et `sys`** : Indispensables pour garantir que le jeu fonctionne sur n'importe quel ordinateur (Windows, Mac, Linux) en reconstruisant intelligemment les chemins d'accès vers nos images et musiques peu importe où le jeu est installé.
