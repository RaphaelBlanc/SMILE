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

# ================================================================
#  ESPRITS ÉLÉMENTAIRES
# ================================================================

class ExplosionVFX(pygame.sprite.Sprite):
    def __init__(self, pos, color, radius, groups):
        super().__init__(groups)
        d = radius * 2
        self.image = pygame.Surface((d, d), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (*color, 180), (radius, radius), radius)
        pygame.draw.circle(self.image, (*color[:3], 80), (radius, radius), radius, 4)
        self.rect  = self.image.get_rect(center=pos)
        self.timer = 18

    def update(self, *args):
        self.timer -= 1
        alpha = max(0, int(255 * self.timer / 18))
        self.image.set_alpha(alpha)
        if self.timer <= 0:
            self.kill()

class EspritBase(BaseEnemy):

    PATROL_SPEED     = 0
    PATROL_RADIUS    = 0
    SPEED            = 3
    JUMP_FORCE       = -11
    DETECT_RANGE     = 380
    LOSE_RANGE       = 560
    EXPLOSION_RADIUS = 50

    COULEUR_CORPS = PURPLE
    COULEUR_AURA  = (180, 0, 255)

    ST_WANDER  = "wander"
    ST_RETURN  = "return"
    ST_CHASE   = "chase"
    ST_EXPLODE = "explode"

    def __init__(self, pos, groups, hp, capacite, vfx_groups=None):
        super().__init__(pos, hp=hp, groups=groups, capacite_absorbable=capacite)

        w = h = 30
        self.image = self._build_img(w, h)
        self.rect  = self.image.get_rect(topleft=pos)

        self.state        = self.ST_WANDER
        self.vy           = 0
        self.on_floor     = False
        self.bounce_timer = random.randint(60, 120)

        self.vfx_groups = vfx_groups or []

    def _build_img(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        pygame.draw.ellipse(s, self.COULEUR_CORPS, (0, 4, w, h - 4))
        pygame.draw.ellipse(s, self.COULEUR_AURA,  (5, 0, w - 10, h // 2))
        pygame.draw.circle(s, WHITE,  (9,  9), 3)
        pygame.draw.circle(s, WHITE,  (21, 9), 3)
        pygame.draw.circle(s, BLACK,  (10, 9), 1)
        pygame.draw.circle(s, BLACK,  (22, 9), 1)
        return s

    def _apply_explosion(self, player):
        player.take_damage(10)

    def update(self, player, obstacles):
        if self.dead: return
        self.tick_contact_timer()

        # Utilisation de player.hitbox
        dist = self.distance_to(player.hitbox)

        if self.state in (self.ST_WANDER, self.ST_RETURN):
            if dist < self.DETECT_RANGE:
                self.state = self.ST_CHASE

        elif self.state == self.ST_CHASE:
            if dist > self.LOSE_RANGE:
                self.state = self.ST_RETURN
            
            # Utilisation de player.hitbox
            player_contact = self.rect.colliderect(player.hitbox)
            floor_under_player = (
                self.on_floor
                and abs(self.rect.centerx - player.hitbox.centerx) < self.EXPLOSION_RADIUS
                and abs(self.rect.bottom - player.hitbox.bottom) < 40
            )
            if player_contact or floor_under_player:
                self.state = self.ST_EXPLODE

        elif self.state == self.ST_EXPLODE:
            self._apply_explosion(player)
            ExplosionVFX(
                self.rect.center,
                self.COULEUR_CORPS,
                self.EXPLOSION_RADIUS,
                self.vfx_groups
            )
            self.on_death()
            return

        self._apply_gravity_esprit(obstacles)

        if self.state == self.ST_WANDER:
            self.bounce_timer -= 1
            if self.bounce_timer <= 0 and self.on_floor:
                self.vy = self.JUMP_FORCE * 0.4
                self.bounce_timer = random.randint(80, 140)

        elif self.state == self.ST_RETURN:
            if self._do_return_to_spawn(obstacles):
                self.state = self.ST_WANDER

        elif self.state == self.ST_CHASE:
            # Utilisation de player.hitbox
            d = 1 if player.hitbox.centerx > self.rect.centerx else -1
            self._try_move(d * self.SPEED, obstacles)
            
            if self.on_floor:
                # Utilisation de player.hitbox
                player_above = player.hitbox.centery < self.rect.centery - 20
                force = self.JUMP_FORCE * 1.1 if player_above else self.JUMP_FORCE * 0.9
                self.vy = force

    def _apply_gravity_esprit(self, obstacles):
        self.vy += 0.8
        if self.vy > 14: self.vy = 14
        self.rect.y  += int(self.vy)
        self.on_floor = False
        for hit in pygame.sprite.spritecollide(self, obstacles, False):
            if self.vy > 0:
                self.rect.bottom = hit.rect.top
                self.vy = 0; self.on_floor = True

# ── Esprit du Feu ──────────────────────────────────────────────

class EspritFeu(EspritBase):
    SPEED            = 4
    JUMP_FORCE       = -12
    DETECT_RANGE     = 450
    LOSE_RANGE       = 650
    EXPLOSION_RADIUS = 60
    COULEUR_CORPS    = (220, 60,  0)
    COULEUR_AURA     = (255, 200, 0)
    BURN_DPS         = 5
    BURN_DUR         = 3

    def __init__(self, pos, groups, vfx_groups=None):
        super().__init__(pos, groups, hp=30, capacite="fireball",
                         vfx_groups=vfx_groups)
        self.image = self._build_img(30, 30)

    def _apply_explosion(self, player):
        player.take_damage(12)
        if hasattr(player, 'burn_timer'):
            player.burn_timer = self.BURN_DUR * 60
            player.burn_dps   = self.BURN_DPS

# ── Esprit de Glace ────────────────────────────────────────────

class EspritGlace(EspritBase):
    SPEED            = 1
    JUMP_FORCE       = -8
    DETECT_RANGE     = 350
    LOSE_RANGE       = 500
    EXPLOSION_RADIUS = 70
    COULEUR_CORPS    = BLUE_ICE
    COULEUR_AURA     = CYAN
    SLOW_DUR         = 180
    SLOW_FAC         = 0.25

    def __init__(self, pos, groups, vfx_groups=None):
        super().__init__(pos, groups, hp=35, capacite="ice_shot",
                         vfx_groups=vfx_groups)
        self.image = self._build_img_ice(30, 30)

    def _build_img_ice(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        pygame.draw.ellipse(s, BLUE_ICE, (0, 4, w, h - 4))
        pygame.draw.ellipse(s, CYAN,     (5, 0, w - 10, h // 2))
        for cx, cy in [(5, 18), (15, 22), (24, 16)]:
            pygame.draw.polygon(s, WHITE,
                                [(cx, cy-6), (cx+3, cy), (cx, cy+4), (cx-3, cy)])
        pygame.draw.circle(s, WHITE,    (9,  9), 3)
        pygame.draw.circle(s, WHITE,    (21, 9), 3)
        pygame.draw.circle(s, BLUE_DARK, (10, 9), 1)
        pygame.draw.circle(s, BLUE_DARK, (22, 9), 1)
        return s

    def _apply_explosion(self, player):
        player.take_damage(8)
        player.slow_timer  = self.SLOW_DUR
        player.slow_factor = self.SLOW_FAC

# ── Esprit de Foudre ───────────────────────────────────────────

class EspritFoudre(EspritBase):
    SPEED            = 5
    JUMP_FORCE       = -14
    DETECT_RANGE     = 500
    LOSE_RANGE       = 700
    EXPLOSION_RADIUS = 55
    COULEUR_CORPS    = (180, 180, 0)
    COULEUR_AURA     = ELECTRIC
    SHOCK_DAMAGE     = 18
    TELEPORT_CD      = 150

    def __init__(self, pos, groups, vfx_groups=None):
        super().__init__(pos, groups, hp=25, capacite="thunder",
                         vfx_groups=vfx_groups)
        self.image   = self._build_img_thunder(30, 30)
        self.tp_timer = 0

    def _build_img_thunder(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        pygame.draw.ellipse(s, (180, 180, 20), (0, 4, w, h - 4))
        pygame.draw.ellipse(s, ELECTRIC,       (5, 0, w - 10, h // 2))
        pts = [(15, 2), (9, 13), (14, 13), (7, 27), (19, 11), (13, 11)]
        pygame.draw.polygon(s, WHITE, pts)
        pygame.draw.circle(s, WHITE,  (9,  9), 3)
        pygame.draw.circle(s, WHITE,  (21, 9), 3)
        pygame.draw.circle(s, BLACK,  (10, 9), 1)
        pygame.draw.circle(s, BLACK,  (22, 9), 1)
        return s

    def update(self, player, obstacles):
        if self.dead: return

        if self.state == self.ST_CHASE:
            if self.tp_timer > 0:
                self.tp_timer -= 1
            elif self.on_floor:
                offset_x = random.choice([-80, 80])
                # Utilisation de player.hitbox
                nx = max(32, min(1920 - 32, player.hitbox.centerx + offset_x))
                self.rect.centerx = nx
                self.rect.bottom  = player.hitbox.bottom
                self.vy           = 0
                self.tp_timer     = self.TELEPORT_CD

        super().update(player, obstacles)

    def _apply_explosion(self, player):
        player.take_damage(self.SHOCK_DAMAGE)
        if hasattr(player, 'direction'):
            player.direction.y = -10

# ── Esprit de Nature ───────────────────────────────────────────

class EspritNature(EspritBase):
    SPEED            = 2
    JUMP_FORCE       = -10
    DETECT_RANGE     = 350
    LOSE_RANGE       = 500
    EXPLOSION_RADIUS = 65
    COULEUR_CORPS    = NATURE_GREEN
    COULEUR_AURA     = GREEN_LIGHT
    POISON_DPS       = 3
    POISON_DUR       = 4
    HEAL_AMOUNT      = 8
    HEAL_RADIUS      = 130
    HEAL_CD          = 180

    def __init__(self, pos, groups, vfx_groups=None):
        super().__init__(pos, groups, hp=20, capacite="poison_cloud",
                         vfx_groups=vfx_groups)
        self.image      = self._build_img_nature(30, 30)
        self.heal_timer = 0

    def _build_img_nature(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        pygame.draw.ellipse(s, NATURE_GREEN, (0, 4, w, h - 4))
        pygame.draw.ellipse(s, GREEN_LIGHT,  (5, 0, w - 10, h // 2))
        for angle, r in [(0, 8), (120, 8), (240, 8)]:
            rad = math.radians(angle)
            lx  = int(15 + r * math.cos(rad))
            ly  = int(15 + r * math.sin(rad))
            pygame.draw.ellipse(s, (0, 160, 30), (lx - 4, ly - 3, 8, 6))
        pygame.draw.circle(s, WHITE,  (9,  9), 3)
        pygame.draw.circle(s, WHITE,  (21, 9), 3)
        pygame.draw.circle(s, BLACK,  (10, 9), 1)
        pygame.draw.circle(s, BLACK,  (22, 9), 1)
        return s

    def update(self, player, obstacles):
        if self.dead: return
        if self.heal_timer > 0: self.heal_timer -= 1
        super().update(player, obstacles)

    def heal_allies(self, monster_group):
        if self.heal_timer > 0 or self.dead: return
        for ally in monster_group:
            if ally is self or ally.dead: continue
            if self.distance_to(ally.rect) < self.HEAL_RADIUS:
                ally.hp_current = min(ally.hp_max,
                                      ally.hp_current + self.HEAL_AMOUNT)
        self.heal_timer = self.HEAL_CD

    def _apply_explosion(self, player):
        player.take_damage(6)
        if hasattr(player, 'is_poisoned'):
            player.is_poisoned  = True
            player.poison_timer = self.POISON_DUR * 60
            player.poison_dps   = self.POISON_DPS

# ================================================================
#  GOLEM DE PIERRE 
# ================================================================

class GolemPierre(BaseEnemy):

    PATROL_SPEED   = 0
    PATROL_RADIUS  = 0
    SPEED          = 1
    DETECT_RANGE   = 600
    LOSE_RANGE     = 900
    STOMP_RANGE    = 90
    QUAKE_RANGE    = 350
    STOMP_DAMAGE   = 25
    QUAKE_DAMAGE   = 15
    QUAKE_SLOW_DUR = 120
    QUAKE_SLOW_FAC = 0.4
    ATTACK_CD      = 90
    REINFORCE_DUR  = 60

    ST_SLEEP     = "sleep"
    ST_RETURN    = "return"
    ST_CHASE     = "chase"
    ST_REINFORCE = "reinforce"
    ST_STOMP     = "stomp"
    ST_QUAKE     = "quake"

    def __init__(self, pos, groups, screen_shake_ref=None):
        super().__init__(pos, hp=200, groups=groups, capacite_absorbable="stone_armor")
        self.CONTACT_COOLDOWN = 120
        self.screen_shake_ref = screen_shake_ref

        w, h = 56, 72
        self._img_sleep  = self._build_img(w, h, active=False)
        self._img_active = self._build_img(w, h, active=True)
        self._img_blink0 = self._build_img(w, h, active=True)
        self._img_blink1 = self._build_img(w, h, active=False)

        self.image = self._img_sleep
        self.rect  = self.image.get_rect(topleft=pos)

        self.state           = self.ST_SLEEP
        self.facing_right    = True
        self.attack_timer    = 0
        self.reinforce_timer = 0
        self._pending_attack = self.ST_STOMP
        self.vy              = 0

    @staticmethod
    def _build_img(w, h, active=True):
        eye_col  = (220, 30, 30) if active else (50, 20, 20)
        glow_col = (255, 60, 60) if active else (40, 10, 10)
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        pygame.draw.rect(s, GRAY,        (8, 16, 40, 56))
        pygame.draw.rect(s, GRAY,        (4,  0, 48, 24))
        pygame.draw.line(s, (80, 70, 60), (14, 20), (28, 42), 2)
        pygame.draw.line(s, (80, 70, 60), (38, 14), (30, 36), 2)
        pygame.draw.rect(s, eye_col,  (10, 6, 12, 10))
        pygame.draw.rect(s, eye_col,  (34, 6, 12, 10))
        pygame.draw.circle(s, glow_col, (16, 11), 4)
        pygame.draw.circle(s, glow_col, (40, 11), 4)
        pygame.draw.rect(s, (90, 80, 70),   (0,  24, 10, 32))
        pygame.draw.rect(s, (90, 80, 70),   (46, 24, 10, 32))
        pygame.draw.rect(s, (110, 100, 90), (0,  52, 12, 14))
        pygame.draw.rect(s, (110, 100, 90), (44, 52, 12, 14))
        return s

    def update(self, player, obstacles):
        if self.dead: return
        self.tick_contact_timer()
        self._apply_gravity(obstacles)
        # Utilisation de player.hitbox
        dist = self.distance_to(player.hitbox)

        if self.attack_timer > 0: self.attack_timer -= 1

        if self.reinforce_timer > 0:
            self.reinforce_timer -= 1
            self.image = self._img_blink0 if (self.reinforce_timer // 8) % 2 == 0 \
                         else self._img_blink1
            return

        if self.state == self.ST_SLEEP:
            if dist < self.DETECT_RANGE:
                self.image = self._img_active
                self.state = self.ST_CHASE

        elif self.state == self.ST_RETURN:
            pass

        elif self.state == self.ST_CHASE:
            if dist > self.LOSE_RANGE:
                self.image = self._img_sleep
                self.state = self.ST_RETURN
            elif dist <= self.STOMP_RANGE:
                self._pending_attack = self.ST_STOMP
                self.reinforce_timer = self.REINFORCE_DUR
            elif dist <= self.QUAKE_RANGE:
                self._pending_attack = self.ST_QUAKE
                self.reinforce_timer = self.REINFORCE_DUR

        elif self.state == self.ST_REINFORCE:
            self.state = self._pending_attack

        elif self.state in (self.ST_STOMP, self.ST_QUAKE):
            self.state = self.ST_CHASE

        # Utilisation de player.hitbox
        d = 1 if player.hitbox.centerx > self.rect.centerx else -1
        self.facing_right = (d == 1)

        if self.state == self.ST_CHASE:
            self._try_move(d * self.SPEED, obstacles)

        elif self.state == self.ST_RETURN:
            if self._do_return_to_spawn(obstacles):
                self.image = self._img_sleep
                self.state = self.ST_SLEEP

        elif self.state == self.ST_STOMP:
            if self.attack_timer == 0 and self.contact_timer == 0:
                player.take_damage(self.STOMP_DAMAGE)
                self.contact_timer = self.CONTACT_COOLDOWN
                self.attack_timer  = self.ATTACK_CD
                self.state         = self.ST_CHASE

        elif self.state == self.ST_QUAKE:
            if self.attack_timer == 0:
                self._do_quake(player)
                self.attack_timer = self.ATTACK_CD
                self.state        = self.ST_CHASE

    def _do_quake(self, player):
        # Utilisation de player.hitbox
        dist = self.distance_to(player.hitbox)
        if dist <= self.QUAKE_RANGE:
            player.take_damage(self.QUAKE_DAMAGE)
            player.slow_timer  = self.QUAKE_SLOW_DUR
            player.slow_factor = self.QUAKE_SLOW_FAC
        if self.screen_shake_ref is not None:
            self.screen_shake_ref[0] = 20