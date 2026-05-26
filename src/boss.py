import pygame
import math
import random

GRAVITY       = 0.8
SCREEN_WIDTH  = 1920
SCREEN_HEIGHT = 1072

IDLE, WINDUP, EXECUTING, COOLDOWN = "idle", "windup", "executing", "cooldown"

WHITE, BLACK, RED, DARK_RED = (255,255,255), (0,0,0), (255,0,0), (139,0,0)
YELLOW, ORANGE, ICE_BLUE, GREY = (255,230,0), (255,140,0), (140,210,255), (140,130,120)

class BossProjectile(pygame.sprite.Sprite):
    def __init__(self, pos, vx, vy, radius=10, color=ORANGE, use_gravity=False, max_lifetime=4000):
        super().__init__()
        self.radius = radius
        self.use_grav = use_gravity
        self.born = pygame.time.get_ticks()
        self.max_life = max_lifetime
        self.vx, self.vy = vx, vy
        
        size = self.radius * 2 + 10
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (size//2, size//2), self.radius)
        
        self.rect = self.image.get_rect(center=pos)
        # Hitbox très précise (légèrement plus petite que le rayon visuel)
        self.hitbox = self.rect.inflate(-self.radius, -self.radius)
        self.fx, self.fy = float(self.rect.x), float(self.rect.y)

    def update(self, obstacles=None):
        if self.use_grav: self.vy = min(self.vy + GRAVITY * 0.55, 22)
        self.fx += self.vx; self.fy += self.vy
        self.rect.x, self.rect.y = int(self.fx), int(self.fy)
        self.hitbox.center = self.rect.center # Synchro
        
        if pygame.time.get_ticks() - self.born > self.max_life or self.rect.right < -80 or self.rect.left > SCREEN_WIDTH + 80:
            self.kill()

class FrozenGround(pygame.sprite.Sprite):
    def __init__(self, x, floor_y, width=200, lifetime=5000):
        super().__init__()
        self.image = pygame.Surface((width, 16), pygame.SRCALPHA)
        self.image.fill((140, 210, 255, 80))
        self.rect = self.image.get_rect(topleft=(x, floor_y - 16))
        self.hitbox = self.rect.copy()
        self.born = pygame.time.get_ticks()
        self.life = lifetime

    def update(self, obstacles=None):
        if pygame.time.get_ticks() - self.born > self.life: self.kill()

class BossBase(pygame.sprite.Sprite):
    HP_MAX = 400
    WIDTH, HEIGHT = 160, 220
    NAME = "???"

    def __init__(self, pos, room_obstacles, floor_y):
        super().__init__()
        self.hp = self.HP_MAX
        self.alive = True
        self.floor_y = floor_y
        self.obstacles = room_obstacles
        self.vx = self.vy = 0.0
        self.on_ground = False
        self.facing_right = True

        self.image = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=pos)
        
        # HITBOX REDUITE DE 50%
        self.hitbox = pygame.Rect(0, 0, self.WIDTH * 0.5, self.HEIGHT * 0.5)
        self.hitbox.center = self.rect.center

        self.attack_state = IDLE
        self.attack_name = None
        self.windup_timer = self.exec_timer = self.cd_timer = 0
        self.global_cd = 800

        self.projectiles = pygame.sprite.Group()
        self.shockwaves = pygame.sprite.Group()
        self.hazards = pygame.sprite.Group()

    def take_damage(self, amount):
        self.hp = max(0, self.hp - amount)
        if self.hp == 0: self.alive = False

    def update(self, player_rect, dt):
        if not self.alive: return
        self.hitbox.center = self.rect.center # Synchro hitbox

        # Machine à état très simplifiée (voir ta propre logique pour le Windup/Execute)
        self.global_cd -= dt * 1000
        if self.global_cd <= 0 and self.attack_state == IDLE:
            self.attack_state = EXECUTING
            self.exec_timer = 2000
            self._start_attack(player_rect)

        if self.attack_state == EXECUTING:
            self.exec_timer -= dt * 1000
            self._exec_attack(dt * 1000, player_rect)
            if self.exec_timer <= 0:
                self.attack_state = IDLE
                self.global_cd = 1500

        self.projectiles.update(self.obstacles)
        self.hazards.update()

    def _start_attack(self, pr): pass
    def _exec_attack(self, dt, pr): pass

    def draw_health_bar(self, screen):
        bw, bh = 600, 28
        x, y = (SCREEN_WIDTH - bw)//2, 28
        r = self.hp / self.HP_MAX
        pygame.draw.rect(screen, DARK_RED, (x, y, bw, bh))
        pygame.draw.rect(screen, ORANGE, (x, y, int(bw * r), bh))

class Glacius(BossBase):
    NAME = "GLACIUS"
    WIDTH, HEIGHT = 140, 230

    def __init__(self, pos, obstacles, floor_y):
        super().__init__(pos, obstacles, floor_y)
        self.image.fill((80,140,210)) # Placeholder
        self._shard_timer = 0

    def _start_attack(self, pr):
        self._shard_timer = 0
        self.facing_right = pr.centerx > self.rect.centerx

    def _exec_attack(self, dt_ms, pr):
        self._shard_timer += dt_ms
        if self._shard_timer >= 500:
            self._shard_timer = 0
            d = 1 if self.facing_right else -1
            # Rayon réduit pour l'attaque (11 au lieu de 22)
            self.projectiles.add(BossProjectile((self.rect.centerx, self.rect.centery), d * 7, 0, radius=11, color=ICE_BLUE))