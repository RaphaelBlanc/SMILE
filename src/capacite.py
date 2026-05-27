import pygame
import os
ORANGE = (255, 165, 0)
SCREEN_WIDTH = 1920
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
class Projectile(pygame.sprite.Sprite):
    _frames_right = []
    _frames_left  = []
    _loaded       = False
    DISPLAY_SIZE = (48, 48)  
    ANIM_FPS     = 12        
    def __init__(self, pos, direction):
        super().__init__()
        self.direction = direction
        self.speed     = 15
        self.start_x   = pos[0]
        self.max_range = 1000  
        Projectile._load_frames()
        self.frames = (
            Projectile._frames_right if direction == 1
            else Projectile._frames_left
        )
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
                cls._frames_right.append(img)
                cls._frames_left.append(pygame.transform.flip(img, True, False))
            except Exception as e:
                pass
    def update(self, obstacles):
        self.rect.x += self.speed * self.direction
        self.frame_index += self.ANIM_FPS / 60
        if self.frame_index >= len(self.frames):
            self.frame_index = 0.0
        self.image = self.frames[int(self.frame_index)]
        if pygame.sprite.spritecollide(self, obstacles, False):
            self.kill()
        distance_parcourue = abs(self.rect.x - self.start_x)
        if distance_parcourue > self.max_range:
            self.kill()
class Capacite:
    def __init__(self, player):
        self.player         = player
        self.last_dash_time = 0
        self.last_fire_time = 0
        self.fire_cooldown  = 500
        self.projectiles    = pygame.sprite.Group()
    def dash(self, obstacles, dash_key=pygame.K_v):
        current_time = pygame.time.get_ticks()
        if getattr(self.player, 'input_locked', False):
            class EmptyKeys:
                def __getitem__(self, item): return False
            keys = EmptyKeys()
        else:
            keys = pygame.key.get_pressed()
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
        if getattr(self.player, 'input_locked', False):
            class EmptyKeys:
                def __getitem__(self, item): return False
            keys = EmptyKeys()
        else:
            keys = pygame.key.get_pressed()
        current_time = pygame.time.get_ticks()
        if keys[attack_key] and (current_time - self.last_fire_time > self.fire_cooldown):
            if hasattr(self.player, 'sound_manager'):
                self.player.sound_manager.play("fireball")
            direction      = 1 if self.player.facing_right else -1
            offset_x = 40 * direction
            pos_tir = (self.player.rect.centerx + offset_x, self.player.rect.centery)
            nouvelle_boule = Projectile(pos_tir, direction)
            self.projectiles.add(nouvelle_boule)
            self.last_fire_time = current_time
