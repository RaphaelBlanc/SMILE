# SMILE 🎮

Bienvenue dans **SMILE**, un jeu 2D d'aventure, d'action et de plateforme développé en Python avec la bibliothèque Pygame. Ce projet a été initialement créé dans le cadre d'un projet scolaire et a évolué pour inclure des mécaniques de jeu variées, de multiples boss épiques et un mode multijoueur coopératif complet !

## 🌟 Fonctionnalités Principales

*   **Mode Multijoueur Coopératif** : Jouez avec un ami en réseau local ou via Internet grâce à une architecture client/serveur robuste. L'hôte incarne le héros principal, et le second joueur l'accompagne sous la forme d'un Slime animé ! L'exploration, les combats, la mort des monstres et les téléportations sont entièrement synchronisés.
*   **Bestiaire Varié & Altérations d'État** : Affrontez de nombreux monstres avec des comportements et statistiques uniques : 
    *   *Esprits Élémentaires* (Feu, Glace) explosant au contact et infligeant des statuts (Gel, Brûlure).
    *   *Loups, Chauve-souris, Gobelins* (Mêlée et Archers).
*   **Boss Épiques** : 
    *   **Glacius** (Boss de Glace) : Esquivez ses ondes de choc, ses projectiles glacés et son rayon laser dévastateur.
    *   **Pyros** (Boss de Lave) : Survivez à la montée de la lave et à ses attaques volcaniques imprévisibles !
*   **Système de Combat & Capacités** : Lancez des projectiles, attaquez au corps-à-corps, absorbez les capacités élémentaires de certains ennemis.
*   **Exploration & Progression** : Cartes créées avec Tiled (`.tmx`), incluant des portes de téléportation, des interactions scénarisées, et un système de sauvegarde / chargement automatique de la progression.
*   **PNJ & Dialogues** : Interagissez avec des personnages non-joueurs pour vous immerger dans l'univers et débloquer la suite de l'aventure ou l'accès aux arènes de boss.
*   **Effets Visuels & Sonores** : Système de particules avancées (VFX, trainées de sang, explosions) pour rendre les combats immersifs et un SoundManager complet pour gérer l'ambiance, les musiques de boss et les bruitages.

## 🛠️ Prérequis et Installation

Pour faire tourner le jeu en local, vous aurez besoin de Python 3 et des bibliothèques suivantes :

1. Clonez ce dépôt :
   ```bash
   git clone https://github.com/RaphaelBlanc/SMILE.git
   cd SMILE
   ```
2. Installez les dépendances nécessaires (`pygame` et `pytmx`) :
   ```bash
   pip install pygame pytmx
   ```

## 🚀 Comment jouer ?

Lancez simplement le fichier principal depuis la racine du projet :

```bash
python src/main.py
```

### 🎮 Contrôles Principaux

*   **Déplacement** : Flèches `Gauche`/`Droite` ou `Q`/`D`
*   **Saut** : `Espace` ou Flèche `Haut`
*   **Attaque CàC** : `F` / `Z` / `S` / `V` selon l'arme
*   **Action / Interaction (PNJ, Portes)** : `E`
*   **Menu & Pause** : `Échap`

## 🌐 Mode Multijoueur

Le jeu dispose d'un menu intuitif permettant de créer ou de rejoindre une session réseau coopérative :
- **Créer une partie (Hôte)** : Lancez le jeu, choisissez Multijoueur puis de créer une session. Le jeu vous fournira un code (ou IP) à partager.
- **Rejoindre (Client)** : Choisissez l'option de rejoindre et entrez le code fourni par l'hôte. Vous apparaitrez instantanément dans sa partie !

## 📁 Architecture du Code (Aperçu)

*   `src/main.py` : Cœur du jeu, boucle principale, rendu global (HUD, Caméra), gestion de la physique, des collisions et de l'état réseau (Synchronisation Client/Serveur).
*   `src/player.py` / `src/monstre.py` / `src/boss.py` / `src/npc.py` : Logique, animations et comportements des différentes entités.
*   `src/network.py` : Logique de communication réseau par sockets.
*   `src/menu.py` : Interface utilisateur moderne pour la sélection des modes, la gestion des sauvegardes et le lobby multijoueur.
*   `assets/maps/` : Cartes du jeu éditées avec Tiled (`Surface.tmx`, `ZoneLave.tmx`, `map_glace.tmx`, etc.).
*   `assets/images/`, `assets/audio/` : Ressources graphiques (spritesheets) et sonores (musiques dynamiques, bruitages).
