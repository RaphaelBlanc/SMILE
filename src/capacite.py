import pygame
import os

# On définit les constantes nécessaires pour ce fichier
ORANGE = (255, 165, 0)
SCREEN_WIDTH = 1920

# --- NOUVEAU CHEMIN ---
# CURRENT_DIR = le dossier où se trouve capacite.py (donc "src")
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# ROOT_DIR = on recule d'un dossier pour revenir à la racine du projet
ROOT_DIR = os.path.dirname(CURRENT_DIR)

#CLASS PROJECTILE #########################################################

class Projectile(pygame.sprite.Sprite):

    # Cache partagé entre toutes les instances (chargé une seule fois)
    _frames_right = []
    _frames_left  = []
    _loaded       = False

    DISPLAY_SIZE = (48, 48)  # Taille de la boule d'eau (carré)
    ANIM_FPS     = 12        # Vitesse d'animation (frames/seconde)

    def __init__(self, pos, direction):
        super().__init__()

        self.direction = direction
        self.speed     = 15
        self.start_x   = pos[0]
        self.max_range = 1000  # Portée maximale du tir (en pixels)

        # Chargement des frames (une seule fois)
        Projectile._load_frames()

        self.frames = (
            Projectile._frames_right if direction == 1
            else Projectile._frames_left
        )

        # Fallback : carré orange si aucun asset n'est trouvé
        if not self.frames:
            surf = pygame.Surface((16, 16))
            surf.fill(ORANGE)
            self.frames = [surf]

        self.frame_index = 0.0
        self.image       = self.frames[0]
        self.rect        = self.image.get_rect(center=pos)

    @classmethod
    def _load_frames(cls):
        if cls._loaded:
            return
        cls._loaded = True

        # --- MISE À JOUR DU CHEMIN DES IMAGES ---
        # Le jeu part de ROOT_DIR puis rentre dans images -> player -> projectiles -> water_ball
        folder = os.path.join(ROOT_DIR, 'assets', 'images', 'player', 'projectiles')
        
        if not os.path.isdir(folder):
            print(f"[Projectile] ATTENTION: Dossier introuvable -> {folder}")
            return

        filenames = sorted(
            f for f in os.listdir(folder)
            if f.lower().endswith('.png')
        )

        for filename in filenames:
            path = os.path.join(folder, filename)
            try:
                img = pygame.image.load(path).convert_alpha()
                img = pygame.transform.scale(img, cls.DISPLAY_SIZE)
                
                # On stocke l'image orientée vers la droite et la gauche
                cls._frames_right.append(img)
                cls._frames_left.append(pygame.transform.flip(img, True, False))
                
            except Exception as e:
                pass

    def update(self, obstacles):
        # Mouvement
        self.rect.x += self.speed * self.direction

        # Animation
        self.frame_index += self.ANIM_FPS / 60
        if self.frame_index >= len(self.frames):
            self.frame_index = 0.0
        self.image = self.frames[int(self.frame_index)]

        # Destruction si collision
        if pygame.sprite.spritecollide(self, obstacles, False):
            self.kill()

        # Destruction si max_range est atteint
        distance_parcourue = abs(self.rect.x - self.start_x)
        if distance_parcourue > self.max_range:
            self.kill()

#CLASS CAPACITE ###########################################################

class Capacite:
    def __init__(self, player):
        self.player         = player
        self.last_dash_time = 0
        self.last_fire_time = 0
        self.fire_cooldown  = 500
        self.projectiles    = pygame.sprite.Group()

    def dash(self, obstacles, dash_key=pygame.K_v):
        current_time = pygame.time.get_ticks()
        keys         = pygame.key.get_pressed()

        if keys[dash_key] and (current_time - self.last_dash_time > 1000):
            if hasattr(self.player, 'sound_manager'):
                self.player.sound_manager.play("dash")
            direction_finale = 1 if self.player.facing_right else -1

            for _ in range(18):
                self.player.hitbox.x += int(direction_finale * 20)
                self.player.check_collision('horizontal', obstacles)

            self.player.direction.y = 0
            self.last_dash_time     = current_time

    def bdf(self, attack_key=pygame.K_f):
        keys         = pygame.key.get_pressed()
        current_time = pygame.time.get_ticks()

        # Vérifie si le cooldown (500ms) est passé
        if keys[attack_key] and (current_time - self.last_fire_time > self.fire_cooldown):
            if hasattr(self.player, 'sound_manager'):
                self.player.sound_manager.play("fireball")
            direction      = 1 if self.player.facing_right else -1
            
            # On décale l'apparition : 40 pixels en avant, et 20 pixels plus haut
            offset_x = 40 * direction
            pos_tir = (self.player.rect.centerx + offset_x, self.player.rect.centery)
            
            nouvelle_boule = Projectile(pos_tir, direction)
            self.projectiles.add(nouvelle_boule)
            self.last_fire_time = current_time