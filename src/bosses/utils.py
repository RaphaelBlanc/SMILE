import pygame
import math
import random
from config import ROOT_DIR, SCREEN_WIDTH, SCREEN_HEIGHT
GRAVITY = 0.8
ORANGE = (255, 140, 0)
RED = (255, 0, 0)
WHITE = (255, 255, 255)

class BossProjectile(pygame.sprite.Sprite):
    def __init__(self, pos, vx, vy, radius=20, color=ORANGE,
                 use_gravity=False, max_lifetime=4000,
                 trail_color=None):
        super().__init__()
        self.radius      = radius
        self.color       = color
        self.use_grav    = use_gravity
        self.born        = pygame.time.get_ticks()
        self.max_life    = max_lifetime
        self.vx          = vx
        self.vy          = vy
        self.trail_color = trail_color
        self._glow       = tuple(min(255, c + 70) for c in color)
        self._build_image()
        self.rect = self.image.get_rect(center=pos)
        self.fx   = float(self.rect.x)
        self.fy   = float(self.rect.y)
    def _build_image(self):
        r    = self.radius
        size = r * 2 + 18
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = cy = size // 2
        for dr, a in [(r+8, 30), (r+4, 60), (r+1, 100)]:
            pygame.draw.circle(surf, (*self._glow, a), (cx, cy), dr)
        pygame.draw.circle(surf, self.color,  (cx, cy), r)
        pygame.draw.circle(surf, self._glow,  (cx, cy), max(2, r - 6))
        pygame.draw.circle(surf, WHITE,       (cx - r//3, cy - r//3), max(1, r//4))
        self.image = surf
    def update(self, obstacles=None):
        if self.use_grav:
            self.vy = min(self.vy + GRAVITY * 0.55, 22)
        self.fx += self.vx
        self.fy += self.vy
        self.rect.x = int(self.fx)
        self.rect.y = int(self.fy)
        if pygame.time.get_ticks() - self.born > self.max_life:
            self.kill(); return
        if (self.rect.right < -80 or self.rect.left > SCREEN_WIDTH + 80
                or self.rect.top > SCREEN_HEIGHT + 80):
            self.kill(); return
        if obstacles and pygame.sprite.spritecollide(self, obstacles, False):
            self.kill()
class ShockWave(pygame.sprite.Sprite):
    def __init__(self, center_x, floor_y, spread_speed=14,
                 wave_height=70, color=ORANGE):
        super().__init__()
        self.cx    = center_x
        self.floor_y     = floor_y
        self.spread      = 20
        self.spread_speed= spread_speed
        self.max_spread  = SCREEN_WIDTH // 2 + 80
        self.height      = wave_height
        self.alpha       = 255
        self.color       = color
        self.image = pygame.Surface((1, 1), pygame.SRCALPHA)
        self.rect  = self.image.get_rect()
    def update(self, obstacles=None):
        self.spread += self.spread_speed
        self.alpha   = max(0, int(255*(1 - self.spread/self.max_spread)))
        if self.alpha == 0 or self.spread >= self.max_spread:
            self.kill(); return
        w, h = self.spread * 2, self.height
        surf  = pygame.Surface((w, h), pygame.SRCALPHA)
        r, g, b = self.color
        for i in range(w):
            ratio = (1 - (abs(i - w//2)/(w//2))**0.6)
            a     = int(self.alpha * ratio)
            pygame.draw.line(surf, (r, g, b, a), (i, h//3), (i, h))
        iw = max(4, w//5)
        ix = w//2 - iw//2
        yr, yg, yb = min(255,r+80), min(255,g+80), min(255,b+80)
        for i in range(iw):
            ratio = 1 - abs(i - iw//2)/(iw//2)
            a     = int(min(255, self.alpha * ratio * 1.5))
            pygame.draw.line(surf, (yr, yg, yb, a), (ix+i, 0), (ix+i, h))
        self.image = surf
        self.rect  = surf.get_rect(midbottom=(self.cx, self.floor_y))
    def draw_self(self, screen, ox=0, oy=0):
        screen.blit(self.image, (self.rect.x+ox, self.rect.y+oy))
class SlamWarning:
    def __init__(self, target_x, floor_y, duration_ms=700, radius=240, color=RED):
        self.target_x   = target_x
        self.floor_y    = floor_y
        self.duration   = duration_ms
        self.elapsed    = 0
        self.done       = False
        self.max_r      = radius
        self.color      = color
    def update(self, dt_ms):
        self.elapsed += dt_ms
        if self.elapsed >= self.duration:
            self.done = True
    def draw(self, screen, ox=0, oy=0):
        if self.done: return
        prog   = self.elapsed / self.duration
        radius = int(self.max_r * (1 - prog))
        alpha  = int(200 * (1 - prog * 0.4))
        cx, cy = self.target_x + ox, self.floor_y + oy
        if radius < 5: return
        s = pygame.Surface((radius*2+6, radius*2+6), pygame.SRCALPHA)
        sc = radius + 3
        r, g, b = self.color
        pygame.draw.circle(s, (r, g, b, alpha),       (sc, sc), radius, 4)
        pygame.draw.circle(s, (255, 240, 50, alpha//2),(sc, sc), radius, 2)
        pygame.draw.line(s, (255,240,0,alpha),(sc-14,sc),(sc+14,sc),3)
        pygame.draw.line(s, (255,240,0,alpha),(sc,sc-14),(sc,sc+14),3)
        screen.blit(s, (cx-sc, cy-sc))
class LightningWarning:
    def __init__(self, x, floor_y, duration_ms=900):
        self.x        = x
        self.floor_y  = floor_y
        self.duration = duration_ms
        self.elapsed  = 0
        self.done     = False
        self.fired    = False
    def update(self, dt_ms):
        self.elapsed += dt_ms
        if self.elapsed >= self.duration:
            self.done = True
    def draw(self, screen, ox=0, oy=0):
        if self.done: return
        prog  = self.elapsed / self.duration
        alpha = int(80 + 175 * prog)
        w     = 30
        s = pygame.Surface((w, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(s, (220, 240, 255, alpha//3), (0, 0, w, SCREEN_HEIGHT))
        pygame.draw.rect(s, (220, 240, 255, alpha),    (w//2-2, 0, 4, SCREEN_HEIGHT))
        screen.blit(s, (self.x - w//2 + ox, oy))
