import pygame
import math
import random
import os
from animator import Animator
CURRENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
def _make_surf(w, h, draw_fn, *args):
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    draw_fn(surf, *args)
    return surf
from .base import BaseEnemy
from .base import BaseEnemy
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
    DETECT_RANGE     = 800
    LOSE_RANGE       = 1100
    EXPLOSION_RADIUS = 20
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
        dist = self.distance_to(player.rect)
        if self.state in (self.ST_WANDER, self.ST_RETURN):
            if dist < self.DETECT_RANGE:
                self.state = self.ST_CHASE
                if getattr(self, 'sound_manager', None):
                    self.sound_manager.play("spirit_detect")
        elif self.state == self.ST_CHASE:
            if dist > self.LOSE_RANGE:
                self.state = self.ST_RETURN
            player_contact = self.rect.colliderect(player.rect)
            floor_under_player = (
                self.on_floor
                and abs(self.rect.centerx - player.rect.centerx) < self.EXPLOSION_RADIUS
                and abs(self.rect.bottom - player.rect.bottom) < 40
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
            self.dead = True
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
            d = 1 if player.rect.centerx > self.rect.centerx else -1
            self._try_move(d * self.SPEED, obstacles)
            if self.on_floor:
                player_above = player.rect.centery < self.rect.centery - 20
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
    def on_death(self):
        self.death_finished = True
        if getattr(self, 'sound_manager', None):
            self.sound_manager.play("spirit_death")
class EspritFeu(EspritBase):
    SPEED            = 4
    JUMP_FORCE       = -12
    DETECT_RANGE     = 900
    LOSE_RANGE       = 1200
    EXPLOSION_RADIUS = 25
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
class EspritGlace(EspritBase):
    SPEED            = 1
    JUMP_FORCE       = -8
    DETECT_RANGE     = 800
    LOSE_RANGE       = 1100
    EXPLOSION_RADIUS = 30
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
class EspritFoudre(EspritBase):
    SPEED            = 5
    JUMP_FORCE       = -14
    DETECT_RANGE     = 970
    LOSE_RANGE       = 1250
    EXPLOSION_RADIUS = 22
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
                nx = max(32, min(1920 - 32, player.rect.centerx + offset_x))
                self.rect.centerx = nx
                self.rect.bottom  = player.rect.bottom
                self.vy           = 0
                self.tp_timer     = self.TELEPORT_CD
        super().update(player, obstacles)
    def _apply_explosion(self, player):
        player.take_damage(self.SHOCK_DAMAGE)
        if hasattr(player, 'direction'):
            player.direction.y = -10
class EspritNature(EspritBase):
    SPEED            = 2
    JUMP_FORCE       = -10
    DETECT_RANGE     = 800
    LOSE_RANGE       = 1100
    EXPLOSION_RADIUS = 25
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
