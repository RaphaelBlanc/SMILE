# SMILE 🎮

Bienvenue dans **SMILE**, un jeu 2D d'aventure et de plateforme développé en Python avec la bibliothèque Pygame. Ce projet a été initialement créé dans le cadre d'un projet scolaire et a évolué pour inclure des mécaniques de jeu variées telles que le multijoueur.

## 🌟 Fonctionnalités Principales

*   **Mode Multijoueur** : Jouez en coopération avec un ami grâce à une architecture client/serveur intégrée directement dans le jeu.
*   **Bestiaire Varié** : Affrontez de nombreux monstres avec des comportements et statistiques uniques : 
    *   *Gobelins* (Mêlée et Archers)
    *   *Esprits Élémentaires* (Feu, Glace, Foudre, Nature)
    *   *Golem de Pierre* (Boss avec effet de secousse d'écran)
    *   *Chiens Enragés*
*   **Système de Combat & Capacités** : Lancez des projectiles, attaquez au corps-à-corps. Les monstres peuvent vous infliger des altérations d'état (Poison, Brûlure, Ralentissement).
*   **Exploration** : Cartes créées avec Tiled (`.tmx`), incluant des plateformes, des échelles, des zones de collision et une caméra dynamique.
*   **PNJ & Dialogues** : Interagissez avec des personnages non-joueurs pour vous immerger dans l'univers.
*   **Effets Visuels & Sonores** : Système de particules (VFX) pour rendre les combats immersifs et SoundManager pour gérer l'audio.

## 🛠️ Prérequis et Installation

Pour faire tourner le jeu en local, vous aurez besoin de Python 3 et des bibliothèques suivantes :

1. Clonez ce dépôt :
   ```bash
   git clone <votre_url_de_depot>
   cd SMILE
   ```
2. Installez les dépendances nécessaires (notamment `pygame` et `pytmx`) :
   ```bash
   pip install pygame pytmx
   ```

## 🚀 Comment jouer ?

Lancez simplement le fichier principal depuis la racine du projet :

```bash
python src/main.py
```

### 🎮 Contrôles Principaux

*   **Déplacement** : Flèches `Gauche`/`Droite` ou `A`/`D` (QWERTY)
*   **Saut** : `Espace` ou Flèche `Haut`
*   **Sprint / Dash** : `Shift Gauche`
*   **Actions / Compétences** : Touches `F`, `V`, `Z`, `S` 
*   **Menu & Pause** : `Échap`

## 🌐 Mode Multijoueur

Le jeu dispose d'un menu intuitif permettant de créer ou de rejoindre une session réseau pour jouer à deux :
- **Créer une partie (Hôte)** : Lancez le jeu, naviguez dans les modes et choisissez de créer une session.
- **Rejoindre (Client)** : Choisissez l'option de rejoindre et entrez le code réseau fourni par l'hôte.

## 📁 Architecture du Code (Aperçu)

*   `src/main.py` : Cœur du jeu, boucle principale, rendu global (HUD, Caméra) et gestion des événements.
*   `src/player.py` / `src/monstre.py` / `src/npc.py` : Logique et comportements des différentes entités.
*   `src/network.py` : Logique de communication réseau par sockets.
*   `src/menu.py` : UI de sélection des modes et pause.
*   `assets/maps/` : Cartes du jeu éditées avec Tiled (`map1.tmx`, `tiles_jeu.tsx`).
*   `assets/images/`, `assets/audio/`, `assets/video/` : Ressources graphiques et sonores classées par dossiers.
