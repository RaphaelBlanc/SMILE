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
class BaseEnemy(pygame.sprite.Sprite):
    DETECT_RANGE  = 600
    LOSE_RANGE    = 900
    PATROL_SPEED  = 1
    PATROL_RADIUS = 100
    def __init__(self, pos, hp, groups, capacite_absorbable=None):
        super().__init__(groups)
        self.spawn_pos  = (int(pos[0]), int(pos[1]))
        self.hp_max     = hp
        self.hp_current = hp
        self.dead       = False
        self.death_finished = False
        self.capacite_absorbable = capacite_absorbable
        self.contact_timer    = 0
        self.CONTACT_COOLDOWN = 90
        self._patrol_targets = [
            self.spawn_pos[0] - self.PATROL_RADIUS,
            self.spawn_pos[0] + self.PATROL_RADIUS,
        ]
        self._patrol_idx = 0
        self.image = pygame.Surface((32, 32))
        self.image.fill((200, 0, 200))
        self.rect  = self.image.get_rect(topleft=pos)
        self._sprites    = {}
        self._anim_timer = 0.0
        self._anim_index = 0
        self._anim_speed = 0.12
    def take_damage(self, amount):
        self.hp_current -= amount
        if self.hp_current <= 0:
            self.hp_current = 0
            self.dead = True
            self.on_death()
    def on_death(self):
        self.death_finished = True 
    def tick_contact_timer(self):
        if self.contact_timer > 0:
            self.contact_timer -= 1
    def _do_return_to_spawn(self, obstacles):
        tx = self.spawn_pos[0]
        if abs(self.rect.centerx - tx) < 8:
            return True
        d = 1 if tx > self.rect.centerx else -1
        self._try_move(d * self.PATROL_SPEED, obstacles)
        return False
    def _do_wander(self, obstacles):
        if self.PATROL_SPEED == 0:
            return
        tx = self._patrol_targets[self._patrol_idx]
        if abs(self.rect.centerx - tx) < 8:
            self._patrol_idx = (self._patrol_idx + 1) % 2
        d = 1 if tx > self.rect.centerx else -1
        self._try_move(d * self.PATROL_SPEED, obstacles)
    def draw_health_bar(self, surface):
        if self.dead:
            return
        bw, bh = self.rect.width, 6
        x, y   = self.rect.left, self.rect.top - 12
        ratio  = max(0.0, self.hp_current / self.hp_max)
        pygame.draw.rect(surface, DARK_RED,    (x, y, bw, bh))
        pygame.draw.rect(surface, (0, 220, 0), (x, y, int(bw * ratio), bh))
        pygame.draw.rect(surface, BLACK,       (x, y, bw, bh), 1)
    def distance_to(self, other_rect):
        a = pygame.math.Vector2(self.rect.center)
        b = pygame.math.Vector2(other_rect.center)
        return a.distance_to(b)
    def _try_move(self, dx, obstacles):
        self.rect.x += int(dx)
        for hit in pygame.sprite.spritecollide(self, obstacles, False):
            if dx > 0: self.rect.right = hit.rect.left
            else:      self.rect.left  = hit.rect.right
    def _apply_gravity(self, obstacles):
        self.vy += 0.8
        if self.vy > 18: self.vy = 18
        self.rect.y += int(self.vy)
        for hit in pygame.sprite.spritecollide(self, obstacles, False):
            if self.vy > 0:
                self.rect.bottom = hit.rect.top
                self.vy = 0
