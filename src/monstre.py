import pygame
import math
import random
import os
from animator import Animator

# --- CALCUL DU CHEMIN ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)

# ────────────────────────────────────────────
#  COULEURS (Pour le Golem et les Esprits)
# ────────────────────────────────────────────
BROWN        = (139,  69,  19)
DARK_RED     = (139,   0,   0)
GREEN_DARK   = (  0, 100,   0)
GREEN_LIGHT  = ( 50, 200,  50)
PURPLE       = (100,   0, 150)
YELLOW       = (255, 220,   0)
ORANGE       = (255, 140,   0)
WHITE        = (255, 255, 255)
BLACK        = (  0,   0,   0)
RED          = (255,   0,   0)
GRAY         = (140, 130, 120)
CYAN         = (  0, 220, 255)
BLUE_ICE     = ( 80, 160, 255)
BLUE_DARK    = ( 20,  40, 120)
ELECTRIC     = (200, 255,   0)
NATURE_GREEN = ( 30, 180,  60)

SCREEN_WIDTH  = 1920
SCREEN_HEIGHT = 1072

# ================================================================
#  CLASSE DE BASE COMMUNE 
# ================================================================

class BaseEnemy(pygame.sprite.Sprite):
    DETECT_RANGE  = 400
    LOSE_RANGE    = 600
    PATROL_SPEED  = 1
    PATROL_RADIUS = 100

    def __init__(self, pos, hp, groups, capacite_absorbable=None):
        super().__init__(groups)
        self.spawn_pos  = (int(pos[0]), int(pos[1]))
        self.hp_max     = hp
        self.hp_current = hp
        self.dead       = False
        self.capacite_absorbable = capacite_absorbable

        self.contact_timer    = 0
        self.CONTACT_COOLDOWN = 90
        self._patrol_targets = [self.spawn_pos[0] - self.PATROL_RADIUS, self.spawn_pos[0] + self.PATROL_RADIUS]
        self._patrol_idx = 0

        self.image = pygame.Surface((64, 64))
        self.rect  = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect.copy() 
        self.vy = 0
        self.facing_right = True

    def take_damage(self, amount):
        self.hp_current -= amount
        if self.hp_current <= 0:
            self.hp_current = 0
            self.dead = True

    def distance_to(self, other_rect):
        a = pygame.math.Vector2(self.hitbox.center)
        b = pygame.math.Vector2(other_rect.center)
        return a.distance_to(b)

    def _do_return_to_spawn(self, obstacles):
        tx = self.spawn_pos[0]
        if abs(self.hitbox.centerx - tx) < 8: return True
        d = 1 if tx > self.hitbox.centerx else -1
        self._try_move(d * self.PATROL_SPEED, obstacles)
        return False

    def _do_wander(self, obstacles):
        tx = self._patrol_targets[self._patrol_idx]
        if abs(self.hitbox.centerx - tx) < 8: self._patrol_idx = (self._patrol_idx + 1) % 2
        d = 1 if tx > self.hitbox.centerx else -1
        self._try_move(d * self.PATROL_SPEED, obstacles)

    def _try_move(self, dx, obstacles):
        self.hitbox.x += int(dx)
        temp = self.rect
        self.rect = self.hitbox
        hits = pygame.sprite.spritecollide(self, obstacles, False)
        self.rect = temp
        
        for hit in hits:
            if dx > 0: self.hitbox.right = hit.rect.left
            else:      self.hitbox.left  = hit.rect.right
            
        self.rect.centerx = self.hitbox.centerx

    def _apply_gravity(self, obstacles):
        self.vy += 0.8
        if self.vy > 18: self.vy = 18
        
        self.hitbox.y += int(self.vy)
        
        temp_rect = self.rect
        self.rect = self.hitbox
        hits = pygame.sprite.spritecollide(self, obstacles, False)
        self.rect = temp_rect
        
        for hit in hits:
            if self.vy > 0:
                self.hitbox.bottom = hit.rect.top
                self.vy = 0
            elif self.vy < 0:
                self.hitbox.top = hit.rect.bottom
                self.vy = 0
                
        # CORRECTION : Utilise getattr pour permettre un décalage personnalisé si l'archer flotte
        offset = getattr(self, 'y_offset', 0)
        self.rect.midbottom = self.hitbox.midbottom
        self.rect.y += offset

# ================================================================
#  ENNEMIS AVEC ANIMATOR
# ================================================================

class AnimatedEnemy(BaseEnemy):
    def __init__(self, pos, hp, groups, folder, mapping, target_size=(240, 240)):
        super().__init__(pos, hp, groups)
        self.animations = self._load_animations(folder, mapping, target_size)
        self.animator = Animator(self.animations, fps=12)
        
        if "idle" in self.animations and self.animations["idle"]:
            self.image = self.animations["idle"][0]
        else:
            self.image = pygame.Surface(target_size)
            self.image.fill((255, 0, 255))
            
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = pygame.Rect(0, 0, target_size[0] * 0.4, target_size[1] * 0.5)
        self.hitbox.midbottom = self.rect.midbottom

    def _load_animations(self, folder, mapping, target_size):
        animations = {}
        path = os.path.join(ROOT_DIR, "assets", "images", "monstre", folder)
        
        for state, fname in mapping.items():
            full_path = os.path.join(path, fname)
            frames = []
            if os.path.exists(full_path):
                img = pygame.image.load(full_path).convert_alpha()
                w, h = img.get_size()
                if w > h:
                    frame_size = h
                    for i in range(w // frame_size):
                        rect = pygame.Rect(i * frame_size, 0, frame_size, frame_size)
                        frame = img.subsurface(rect).copy()
                        frames.append(pygame.transform.scale(frame, target_size))
                else:
                    frames.append(pygame.transform.scale(img, target_size))
            
            if frames:
                animations[state] = frames
                
        if "idle" in animations: animations["idle_right"] = animations["idle"]
        return animations

    def _get_anim_frame(self, state, fps=10, loop=True):
        self.animator.animation_speed = 1.0 / fps
        surf = self.animator.get_current_frame(1/60.0, state, loop=loop)
        if not self.facing_right: 
            surf = pygame.transform.flip(surf, True, False)
        return surf

# ================================================================
#  CHIEN ENRAGÉ
# ================================================================

class ChienEnrage(AnimatedEnemy):
    def __init__(self, pos, groups):
        mapping = {"idle": "Idle.png", "wander": "walk.png", "chase": "Run.png", "attack": "Attack_1.png", "hurt": "Hurt.png", "dead": "Dead.png"}
        super().__init__(pos, 60, groups, "wolf", mapping, (200, 200))
        self.state = "wander"
        self.ATTACK_DAMAGE = 15

    def update(self, player, obstacles):
        if self.dead: return
        self.hitbox.center = self.rect.center 
        if self.contact_timer > 0: self.contact_timer -= 1
        self._apply_gravity(obstacles)
        
        dist = self.distance_to(player.rect)

        if dist < 400: self.state = "chase"
        else: self.state = "wander"

        if self.state == "wander":
            self._do_wander(obstacles)
            self.image = self._get_anim_frame("wander")
        elif self.state == "chase":
            d = 1 if player.hitbox.centerx > self.hitbox.centerx else -1
            self.facing_right = (d == 1)
            self._try_move(d * 3, obstacles)
            self.image = self._get_anim_frame("chase", 14)

    def take_damage(self, amount):
        super().take_damage(amount)
        if not self.dead:
            self.animator.current_state = "hurt"
            self.animator.frame_index = 0
            self.image = self._get_anim_frame("hurt", loop=False)

# ================================================================
#  GOBELINS (Guerrier, Archer, Lancier)
# ================================================================

class GoblinMelee(AnimatedEnemy):
    def __init__(self, pos, groups):
        mapping = {"idle": "Idle.png", "wander": "Walk.png", "chase": "Run.png", "attack": "Attack_1.png", "hurt": "Hurt.png", "dead": "Dead.png"}
        super().__init__(pos, 40, groups, "goblin_melee", mapping, (240, 240))
        self.state = "wander"
        self.ATTACK_DAMAGE = 12

    def update(self, player, obstacles):
        if self.dead: return
        if self.contact_timer > 0: self.contact_timer -= 1
        self._apply_gravity(obstacles)
        
        dist = self.distance_to(player.rect)
        
        # Gestion de la machine à état d'attaque
        if self.state == "attack":
            self.image = self._get_anim_frame("attack", 12, loop=False)
            if self.animator.frame_index >= len(self.animations.get("attack", [])) - 1:
                self.state = "chase"
            return

        if dist < 65: # Déclenchement de l'attaque au corps à corps
            if self.state != "attack":
                self.state = "attack"
                self.animator.current_state = "attack"
                self.animator.frame_index = 0
                if self.contact_timer <= 0 and self.hitbox.colliderect(player.hitbox):
                    player.take_damage(self.ATTACK_DAMAGE)
                    self.contact_timer = self.CONTACT_COOLDOWN
            return

        if dist < 400: self.state = "chase"
        else: self.state = "wander"

        if self.state == "wander":
            self._do_wander(obstacles)
            self.image = self._get_anim_frame("wander")
        elif self.state == "chase":
            d = 1 if player.hitbox.centerx > self.hitbox.centerx else -1
            self.facing_right = (d == 1)
            self._try_move(d * 2, obstacles)
            self.image = self._get_anim_frame("chase", 12)

    def take_damage(self, amount):
        super().take_damage(amount)
        if not self.dead:
            self.animator.current_state = "hurt"
            self.animator.frame_index = 0
            self.image = self._get_anim_frame("hurt", loop=False)

class GoblinLancier(GoblinMelee):
    def __init__(self, pos, groups):
        super().__init__(pos, groups)
        mapping = {"idle": "Idle.png", "wander": "Walk.png", "chase": "Run.png", "attack": "Attack_2.png", "hurt": "Hurt.png", "dead": "Dead.png"}
        self.animations = self._load_animations("goblin_lancier", mapping, (240, 240))
        self.animator = Animator(self.animations, fps=12)
        self.ATTACK_DAMAGE = 15

class Arrow(pygame.sprite.Sprite):
    def __init__(self, pos, direction, groups):
        super().__init__(groups)
        s = pygame.Surface((18, 6), pygame.SRCALPHA)
        pygame.draw.rect(s, BROWN, (0, 2, 14, 2))
        pygame.draw.polygon(s, (200, 200, 220), [(14, 0), (18, 3), (14, 6)])
        if direction == -1: s = pygame.transform.flip(s, True, False)
        self.image = s
        self.rect = self.image.get_rect(center=pos)
        self.hitbox = self.rect.inflate(-4, -4)
        self.direction = direction
        self.damage = 10

    def update(self, obstacles):
        self.rect.x += 16 * self.direction
        self.hitbox.center = self.rect.center
        if pygame.sprite.spritecollide(self, obstacles, False) or self.rect.x < -100 or self.rect.x > SCREEN_WIDTH + 100: 
            self.kill()
class GoblinArcher(AnimatedEnemy):
    def __init__(self, pos, groups, arrow_groups):
        # On définit le mapping avec tes nouveaux noms de fichiers
        mapping = {
            "idle": "Idle.png", 
            "chase": "Run.png", 
            "attack": "Shot_1.png", # Utilise ton sprite de tir
            "hurt": "Hurt.png", 
            "dead": "Dead.png"
        }
        super().__init__(pos, 30, groups, "goblin_archer", mapping, (120, 120))
        self.arrow_groups = arrow_groups
        self.shoot_timer = 0
        self.state = "idle"
        self.y_offset = 0

    def update(self, player, obstacles):
        if self.dead: return
        self.hitbox.center = self.rect.center
        if self.contact_timer > 0: self.contact_timer -= 1
        self._apply_gravity(obstacles)
        
        if self.shoot_timer > 0: self.shoot_timer -= 1
        
        dist = self.distance_to(player.rect)
        d = 1 if player.hitbox.centerx > self.hitbox.centerx else -1
        self.facing_right = (d == 1)
        
        # Logique de tir
        if self.shoot_timer <= 0 and dist < 700:
            self.shoot_timer = 120 # Cooldown entre les tirs
            self.animator.current_state = "attack"
            self.animator.frame_index = 0
            
            # Faire apparaître la flèche au milieu de l'animation (frame 8 sur 16 par ex)
            # On appelle la fonction de tir avec un léger délai si nécessaire
            spawn_x = self.hitbox.centerx + (d * 50)
            spawn_y = self.hitbox.centery - 20
            Arrow((spawn_x, spawn_y), d, [self.arrow_groups])
            
        # Animation
        if self.shoot_timer > 70:
            self.image = self._get_anim_frame("attack", 12, loop=False)
        else:
            self.image = self._get_anim_frame("idle", 8, loop=True)
# ================================================================
#  ESPRITS ET GOLEM
# ================================================================

class EspritBase(BaseEnemy):
    def __init__(self, pos, groups, hp, color):
        super().__init__(pos, hp, groups)
        self.image = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (15, 15), 15)
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect.inflate(-10, -10)
        self.bounce_timer = 0

    def update(self, player, obstacles):
        if self.dead: return
        self._apply_gravity(obstacles)
        
        d = 1 if player.rect.centerx > self.rect.centerx else -1
        self._try_move(d * 2, obstacles)
        
        if self.bounce_timer > 0: self.bounce_timer -= 1
        else:
            self.vy = -10
            self.bounce_timer = 60

class EspritFeu(EspritBase):
    def __init__(self, pos, groups, vfx_groups=None):
        super().__init__(pos, groups, 30, (255, 100, 0))
class EspritGlace(EspritBase):
    def __init__(self, pos, groups, vfx_groups=None):
        super().__init__(pos, groups, 30, (0, 200, 255))
class EspritFoudre(EspritBase):
    def __init__(self, pos, groups, vfx_groups=None):
        super().__init__(pos, groups, 30, (255, 255, 0))
class EspritNature(EspritBase):
    def __init__(self, pos, groups, vfx_groups=None):
        super().__init__(pos, groups, 30, (0, 255, 0))

class GolemPierre(BaseEnemy):
    def __init__(self, pos, groups, screen_shake_ref=None):
        super().__init__(pos, 200, groups)
        self.image = pygame.Surface((80, 100))
        self.image.fill(GRAY)
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect.inflate(-40, -40)
        self.screen_shake_ref = screen_shake_ref

    def update(self, player, obstacles):
        if self.dead: return
        self._apply_gravity(obstacles)
        d = 1 if player.hitbox.centerx > self.hitbox.centerx else -1
        self._try_move(d * 1, obstacles)