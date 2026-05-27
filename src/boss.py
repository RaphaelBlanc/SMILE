"""
boss.py  –  SMILE
═════════════════════════════════════════════════════════════════
5 boss élémentaires + 1 boss final mutant

  Boss 1 – PYROS   (Feu)    ★★☆☆☆  Colosse brutal
  Boss 2 – GLACIUS (Glace)  ★★★☆☆  Seigneur calculateur
  Boss 3 – GRANIT  (Pierre) ★★★★☆  Titan impassible
  Boss 4 – VENTUS  (Air)    ★★★★☆  Fantôme insaisissable
  Boss 5 – MUTANT  (Tout)   ★★★★★  Convergence finale

RÉGLAGES : chaque boss possède son propre dict TUNING en tête de classe.
═════════════════════════════════════════════════════════════════
"""

import pygame
import math
import random
from config import ROOT_DIR

# ── Physique globale ──────────────────────────────────────────────────────────
GRAVITY       = 0.8
SCREEN_WIDTH  = 1920
SCREEN_HEIGHT = 1072

# ── États machine à attaques ──────────────────────────────────────────────────
IDLE      = "idle"
WINDUP    = "windup"
EXECUTING = "executing"
COOLDOWN  = "cooldown"

# ── Palette commune ───────────────────────────────────────────────────────────
WHITE    = (255, 255, 255)
BLACK    = (0,   0,   0  )
RED      = (255, 0,   0  )
DARK_RED = (139, 0,   0  )
GREEN    = (0,   200, 0  )
ORANGE   = (255, 140, 0  )
YELLOW   = (255, 230, 0  )
CYAN     = (0,   220, 255)
GREY     = (140, 130, 120)
BROWN    = (110, 72,  35 )
ICE_BLUE = (140, 210, 255)
ICE_DARK = (60,  120, 200)
STONE    = (110, 105, 100)
LAVA     = (255, 80,  10 )
WIND_COL = (200, 230, 255)
ELEC_COL = (220, 240, 255)

# ══════════════════════════════════════════════════════════════════════════════
#  CLASSES DE BASE PARTAGÉES
# ══════════════════════════════════════════════════════════════════════════════

class BossProjectile(pygame.sprite.Sprite):
    """Projectile universel. radius contrôle la taille visuelle ET la hitbox."""

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


class IceSpike(pygame.sprite.Sprite):
    """Pique de glace plantée dans le sol – zone de danger persistante."""

    def __init__(self, x, floor_y, lifetime=3500):
        super().__init__()
        w, h  = 22, 70
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        pts = [(w//2, 0), (w, h), (w//2, h-10), (0, h)]
        pygame.draw.polygon(self.image, ICE_BLUE, pts)
        pygame.draw.polygon(self.image, WHITE,    pts, 2)
        pygame.draw.circle(self.image, WHITE, (w//2, 5), 4)
        self.rect  = self.image.get_rect(midbottom=(x, floor_y))
        self.born  = pygame.time.get_ticks()
        self.life  = lifetime

    def update(self, obstacles=None):
        if pygame.time.get_ticks() - self.born > self.life:
            self.kill()


class ShockWave(pygame.sprite.Sprite):
    """Onde de choc au sol (Pyros / Granit / Mutant)."""

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
        # Cœur brillant
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
    """Cercle d'avertissement qui se referme au point d'impact (GroundSlam)."""

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
    """Marqueur au sol avant un éclair (Ventus / Mutant)."""

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


class FrozenGround(pygame.sprite.Sprite):
    """Zone de sol gelé qui fait glisser le joueur (Glacius)."""

    def __init__(self, x, floor_y, width=200, lifetime=5000):
        super().__init__()
        h          = 16
        self.image = pygame.Surface((width, h), pygame.SRCALPHA)
        self.image.fill((140, 210, 255, 80))
        pygame.draw.rect(self.image, (200, 235, 255, 140), (0,0,width,h), 3)
        for i in range(0, width, 30):
            pygame.draw.line(self.image,(255,255,255,60),(i,0),(i+15,h),1)
        self.rect  = self.image.get_rect(topleft=(x, floor_y - h))
        self.born  = pygame.time.get_ticks()
        self.life  = lifetime

    def update(self, obstacles=None):
        if pygame.time.get_ticks() - self.born > self.life:
            self.kill()


class RoomTile(pygame.sprite.Sprite):
    def __init__(self, rect, color, border=None):
        super().__init__()
        self.image = pygame.Surface((rect.width, rect.height))
        self.image.fill(color)
        if border:
            pygame.draw.rect(self.image, border, (0,0,rect.width,rect.height), 3)
        self.rect = rect


# ══════════════════════════════════════════════════════════════════════════════
#  BOSS BASE
# ══════════════════════════════════════════════════════════════════════════════

class BossBase(pygame.sprite.Sprite):
    """Classe mère partagée par tous les boss."""

    HP_MAX = 400
    WIDTH  = 160
    HEIGHT = 220
    NAME   = "???"

    # Couleurs de thème (override dans chaque boss)
    THEME_PROJ   = ORANGE
    THEME_SHOCK  = ORANGE
    THEME_BG_TOP = (8,  0, 20)
    THEME_BG_BOT = (28, 4, 55)
    THEME_FLOOR  = (40, 12, 60)
    THEME_WALL   = (22,  6, 38)
    THEME_PLAT   = (75, 35,105)
    THEME_PBORD  = (110,60,150)

    def __init__(self, pos, room_obstacles, floor_y):
        super().__init__()
        self.id           = -1
        self.dead         = False
        self.hp           = self.HP_MAX
        self.phase        = 1
        self.alive        = True
        self.death_finished = True
        self.floor_y      = floor_y
        self.obstacles    = room_obstacles
        self.vy           = 0.0
        self.vx           = 0.0
        self.on_ground    = False
        self.facing_right = True
        self._hit_wall    = False
        self._screen_shake_flag = False

        self.attack_state = IDLE
        self.attack_name  = None
        self.windup_timer = 0
        self.exec_timer   = 0
        self.cd_timer     = 0
        self.global_cd    = 800

        self.projectiles  = pygame.sprite.Group()
        self.shockwaves   = pygame.sprite.Group()
        self.hazards      = pygame.sprite.Group()  # piques, sol gelé…
        self.particles    = []

        self._aura_tick   = 0
        self._aura_alpha  = 0

        # Construit par la sous-classe
        self.images       = {}
        self.image        = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)
        self.rect         = self.image.get_rect(topleft=pos)
        self._font_warn   = pygame.font.SysFont("Arial Black", 30, bold=True)

        # Son — assigné depuis main.py après création
        self.sound_manager = None

    def _play(self, name):
        """Joue un son si le sound_manager est disponible."""
        if self.sound_manager:
            self.sound_manager.play(name)

    # ── Surcharger dans chaque boss ───────────────────────────────────────────
    def _get_attack_pool(self):      return []
    def _get_windup(self, name):     return 900
    def _get_cooldown(self, name):   return 1200
    def _get_global_cd(self):        return self.TUNING["global_cd"][self.phase]
    def _start_attack(self, pr):     pass
    def _exec_attack(self, dt, pr):  pass

    # ── Machine à états commune ───────────────────────────────────────────────
    def _choose_attack(self):
        pool      = self._get_attack_pool()
        available = [a for a in pool if a != self.attack_name]
        if not available: available = pool
        self.attack_name  = random.choice(available)
        self.attack_state = WINDUP
        self.windup_timer = self._get_windup(self.attack_name)
        self._play("boss_detect")

    def _end_attack(self, name=None):
        n = name or self.attack_name
        self.attack_state = COOLDOWN
        self.cd_timer     = self._get_cooldown(n)
        self.vx           = 0

    def _update_phase(self):
        ratio = self.hp / self.HP_MAX
        old   = self.phase
        self.phase = 1 if ratio > 0.66 else (2 if ratio > 0.33 else 3)
        if self.phase != old:
            self._phase_burst()

    def _phase_burst(self):
        cx, cy = self.rect.center
        for a in range(0, 360, 15):
            rad = math.radians(a)
            p   = BossProjectile((cx,cy), math.cos(rad)*7, math.sin(rad)*7,
                                 radius=10, color=YELLOW, max_lifetime=700)
            self.projectiles.add(p)

    # ── Physique commune ──────────────────────────────────────────────────────
    def _apply_gravity(self):
        if not self.on_ground:
            self.vy = min(self.vy + GRAVITY, 28)

    def _move_and_collide(self):
        self._hit_wall = False
        self.rect.x += int(self.vx)
        for h in pygame.sprite.spritecollide(self, self.obstacles, False):
            if self.vx > 0: self.rect.right = h.rect.left
            elif self.vx < 0: self.rect.left = h.rect.right
            self._hit_wall = True
        self.rect.y += int(self.vy)
        self.on_ground = False
        for h in pygame.sprite.spritecollide(self, self.obstacles, False):
            if self.vy > 0:
                self.rect.bottom = h.rect.top
                self.vy = 0; self.on_ground = True
            elif self.vy < 0:
                self.rect.top = h.rect.bottom; self.vy = 0
        if self.rect.left < 36:
            self.rect.left = 36; self._hit_wall = True
        if self.rect.right > SCREEN_WIDTH - 36:
            self.rect.right = SCREEN_WIDTH - 36; self._hit_wall = True

    # ── Particules ────────────────────────────────────────────────────────────
    def _emit_dust(self, count=10, colors=None):
        cols = colors or [(220,180,140),(255,130,30),(255,220,50)]
        for _ in range(count):
            self.particles.append({
                "x":  random.randint(self.rect.left+10, self.rect.right-10),
                "y":  self.rect.bottom,
                "vx": random.uniform(-5,5), "vy": random.uniform(-8,-2),
                "life": random.randint(25,55), "max": 55,
                "col": random.choice(cols),
            })

    def _update_particles(self):
        alive = []
        for p in self.particles:
            p["x"] += p["vx"]; p["y"] += p["vy"]; p["vy"] += 0.28
            p["life"] -= 1
            if p["life"] > 0: alive.append(p)
        self.particles = alive

    def _draw_particles(self, screen, ox=0, oy=0):
        for p in self.particles:
            a = int(210 * p["life"] / p["max"])
            r = max(2, int(9 * p["life"] / p["max"]))
            s = pygame.Surface((r*2,r*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*p["col"], a), (r,r), r)
            screen.blit(s, (int(p["x"])-r+ox, int(p["y"])-r+oy))

    # ── Dégâts ────────────────────────────────────────────────────────────────
    def take_damage(self, amount):
        self.hp = max(0, self.hp - amount)
        if self.hp == 0:
            self.alive = False
            self.dead = True

    @property
    def hp_current(self):
        return self.hp

    @hp_current.setter
    def hp_current(self, value):
        self.hp = value
        if self.hp <= 0:
            self.alive = False
            self.dead = True

    @property
    def hp_max(self):
        return self.HP_MAX

    @hp_max.setter
    def hp_max(self, value):
        self.HP_MAX = value

    # ── Update commun ─────────────────────────────────────────────────────────
    def update(self, player_rect, dt):
        if not self.alive:
            if getattr(self, "death_finished", True):
                return
            dt_ms = dt * 1000
            self._apply_gravity()
            self._move_and_collide()
            self._update_visual(dt_ms)
            return
        dt_ms = dt * 1000
        self._screen_shake_flag = False
        self._update_phase()

        if self.attack_state == IDLE:
            self.global_cd -= dt_ms
            self.facing_right = player_rect.centerx > self.rect.centerx
            if self.global_cd <= 0: self._choose_attack()
            else:
                dist = player_rect.centerx - self.rect.centerx
                if abs(dist) > 150:
                    self.vx = 1.2 if dist > 0 else -1.2
                else:
                    self.vx = 0

        elif self.attack_state == WINDUP:
            self.vx = 0
            self.facing_right = player_rect.centerx > self.rect.centerx
            self.windup_timer -= dt_ms
            if self.windup_timer <= 0:
                self.attack_state = EXECUTING
                self.exec_timer   = 5000
                self._start_attack(player_rect)

        elif self.attack_state == EXECUTING:
            self._exec_attack(dt_ms, player_rect)

        elif self.attack_state == COOLDOWN:
            self.vx = 0
            self.cd_timer -= dt_ms
            if self.cd_timer <= 0:
                self.attack_state = IDLE
                self.global_cd    = self._get_global_cd()

        self._apply_gravity()
        self._move_and_collide()
        self.projectiles.update(self.obstacles)
        self.shockwaves.update()
        self.hazards.update()
        self._update_particles()
        self._update_visual(dt_ms)

    def _update_visual(self, dt_ms):
        key = ("enrage"  if self.phase == 3             else
               "windup"  if self.attack_state == WINDUP  else
               "attack"  if self.attack_state == EXECUTING else
               "idle")
        if key not in self.images: key = "idle"
        base = self.images[key].copy()
        if self.phase == 3 and hasattr(self, '_draw_aura'):
            base = self._draw_aura(base, dt_ms)
        if not self.facing_right:
            base = pygame.transform.flip(base, True, False)
        self.image = base

    # ── Draw commun ───────────────────────────────────────────────────────────
    def draw(self, screen, ox=0, oy=0):
        for sw in self.shockwaves: sw.draw_self(screen, ox, oy)
        for h in self.hazards: screen.blit(h.image, (h.rect.x+ox, h.rect.y+oy))
        for p in self.projectiles: screen.blit(p.image, (p.rect.x+ox, p.rect.y+oy))
        if hasattr(self, '_draw_extras'): self._draw_extras(screen, ox, oy)
        self._draw_particles(screen, ox, oy)
        screen.blit(self.image, (self.rect.x+ox, self.rect.y+oy))
        if self.attack_state == WINDUP:
            pct   = max(0, 1 - self.windup_timer / max(1, self._get_windup(self.attack_name)))
            bw    = 80
            bx    = self.rect.centerx - bw//2 + ox
            by    = self.rect.top - 22 + oy
            pygame.draw.rect(screen, (60,0,0),   (bx,by,bw,10), border_radius=4)
            pygame.draw.rect(screen, (255,80,0),  (bx,by,int(bw*pct),10), border_radius=4)
            pygame.draw.rect(screen, WHITE,       (bx,by,bw,10), 2, border_radius=4)

    def draw_health_bar(self, screen):
        bw, bh = 600, 28
        x  = (SCREEN_WIDTH - bw)//2
        y  = 28
        r  = self.hp / self.HP_MAX
        col = (int(220*(1-r)), int(210*r), 0)
        pygame.draw.rect(screen, (55,0,0),   (x-4,y-4,bw+8,bh+8), border_radius=6)
        pygame.draw.rect(screen, DARK_RED,   (x,y,bw,bh))
        pygame.draw.rect(screen, col,        (x,y,int(bw*r),bh))
        for frac, c in [(0.33,ORANGE),(0.66,YELLOW)]:
            mx = x + int(bw*frac)
            pygame.draw.line(screen, c, (mx,y-3),(mx,y+bh+3),3)
        pygame.draw.rect(screen, WHITE, (x,y,bw,bh), 3, border_radius=3)
        f1  = pygame.font.SysFont("Arial Black", 22, bold=True)
        lbl = f1.render(f"☠  {self.NAME}  ☠", True, WHITE)
        screen.blit(lbl, lbl.get_rect(center=(SCREEN_WIDTH//2, y-18)))
        f2   = pygame.font.SysFont("Arial", 18, bold=True)
        pcol = [YELLOW, ORANGE, RED][self.phase-1]
        screen.blit(f2.render(f"Phase {self.phase}", True, pcol), (x+bw+14,y+4))


# ══════════════════════════════════════════════════════════════════════════════
#  BOSS 1 – PYROS  (Feu)  ★★☆☆☆
# ══════════════════════════════════════════════════════════════════════════════

class Pyros(BossBase):
    NAME     = "PYROS"
    HP_MAX   = 800
    WIDTH    = 576
    HEIGHT   = 320
    THEME_PROJ   = (255, 100, 20)
    THEME_SHOCK  = ORANGE
    THEME_BG_TOP = (18,  2,  2)
    THEME_BG_BOT = (50, 10,  5)
    THEME_FLOOR  = (55, 15, 10)
    THEME_WALL   = (30,  8,  5)
    THEME_PLAT   = (100,35, 20)
    THEME_PBORD  = (180,80, 30)

    TUNING = {
        "global_cd":  {1:2200, 2:1600, 3:1000},
        "windup":     {"groundslam":900,"fireline":700,"firewall":1000,
                       "grab_walk":600,"meteor":1100,"enrage_rush":700},
        "cooldown":   {"groundslam":1200,"fireline":1000,"firewall":1300,
                       "grab_walk":900,"meteor":1400,"enrage_rush":1800},
        "slam_jump":  -24,
        "slam_warn":  240,
        "slam_sw_spd":{1:14,2:18,3:22},
        "slam_sw_h":  {1:55,2:75,3:95},
        "slam_shake": 16,
        "fire_count": 3, "fire_ivl":600, "fire_spd":6, "fire_r":28,
        "fw_cols":8,  "fw_ivl":200, "fw_vmin":9,"fw_vmax":14,"fw_r":20,
        "grab_spd":   {1:4.0,2:5.0,3:6.5}, "grab_rng":90, "grab_fist_r":32,
        "meteor_n":16,"meteor_ivl":170,"meteor_vmin":11,"meteor_vmax":17,"meteor_r":22,
        "rush_spd":24,"rush_dur":1600,
    }

    def __init__(self, pos, obstacles, floor_y):
        super().__init__(pos, obstacles, floor_y)
        self.death_finished = False
        self._slam_landed = False
        self._slam_warned = False
        self._slam_warning= None
        self._fire_count  = 0
        self._fire_timer  = 0
        self._fire_dir    = 1
        self._fw_count    = 0
        self._fw_timer    = 0
        self._fw_ox       = 0
        self._grab_hit    = False
        self._meteor_n    = 0
        self._meteor_t    = 0
        self._rush_dir    = 1
        
        self.anim_idx = 0
        self.anim_timer = 0
        self.current_anim_key = "idle"
        self._load_sprites()
        self.image = self.animations["idle"][0]
        self.rect  = self.image.get_rect(topleft=pos)

    def _load_sprites(self):
        import os
        base_path = os.path.join(ROOT_DIR, 'assets', 'images', 'monstre', 'boss_feu', 'individual sprites')
        
        def load_seq(folder_name, prefix):
            frames = []
            dir_path = os.path.join(base_path, folder_name)
            
            if not os.path.exists(dir_path):
                s = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)
                return [s]
                
            files = [f for f in os.listdir(dir_path) if f.endswith('.png')]
            for i in range(1, len(files) + 1):
                path = os.path.join(dir_path, f"{prefix}_{i}.png")
                if os.path.exists(path):
                    try:
                        surf = pygame.image.load(path).convert_alpha()
                        surf = pygame.transform.scale(surf, (self.WIDTH, self.HEIGHT))
                        frames.append(surf)
                    except Exception:
                        pass
            if not frames:
                s = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)
                return [s]
            return frames

        self.animations = {}
        self.animations["idle"] = load_seq("01_demon_idle", "demon_idle")
        self.animations["walk"] = load_seq("02_demon_walk", "demon_walk")
        
        cleave = load_seq("03_demon_cleave", "demon_cleave")
        self.animations["groundslam"]  = cleave
        self.animations["fireline"]    = cleave
        self.animations["firewall"]    = cleave
        self.animations["grab_walk"]   = cleave
        self.animations["meteor"]      = cleave
        self.animations["enrage_rush"] = cleave
        
        self.animations["dead"]        = load_seq("05_demon_death", "demon_death")
        self.animations["hurt"]        = load_seq("04_demon_take_hit", "demon_take_hit")

    def _update_visual(self, dt_ms):
        anim_key = "idle"
        if not self.alive:
            anim_key = "dead"
        elif getattr(self, 'attack_state', 0) in (WINDUP, EXECUTING):
            anim_key = self.attack_name
        elif self.vx != 0:
            anim_key = "walk"
            
        if anim_key not in self.animations:
            anim_key = "idle"
            
        if self.current_anim_key != anim_key:
            self.current_anim_key = anim_key
            self.anim_idx = 0
            self.anim_timer = 0
            
        frames = self.animations[anim_key]
        if self.anim_idx >= len(frames):
            self.anim_idx = 0
            
        fps = 10
        if anim_key in ["groundslam", "fireline", "firewall", "grab_walk", "meteor", "enrage_rush"]:
            fps = 15
            
        if getattr(self, 'attack_state', 0) == WINDUP:
            self.anim_idx = 0
        else:
            self.anim_timer += dt_ms
            if self.anim_timer >= 1000 / fps:
                self.anim_timer = 0
                self.anim_idx += 1
                if self.anim_idx >= len(frames):
                    if anim_key == "dead":
                        self.anim_idx = len(frames) - 1
                        self.death_finished = True
                    else:
                        self.anim_idx = 0
                        
        base = frames[self.anim_idx].copy()
        
        if self.phase == 3 and hasattr(self, '_draw_aura'):
            base = self._draw_aura(base, dt_ms)
            
        if not self.facing_right:
            base = pygame.transform.flip(base, True, False)
            
        self.image = base

    def _draw_aura(self, base, dt_ms):
        self._aura_tick += dt_ms
        alpha = int(70 + 55*math.sin(self._aura_tick/180))
        aura  = pygame.Surface((self.WIDTH+48,self.HEIGHT+48), pygame.SRCALPHA)
        pygame.draw.ellipse(aura,(255,60,0,alpha),(0,0,self.WIDTH+48,self.HEIGHT+48))
        combo = pygame.Surface((self.WIDTH+48,self.HEIGHT+48), pygame.SRCALPHA)
        combo.blit(aura,(0,0)); combo.blit(base,(24,24))
        old = self.rect.center
        self.rect = combo.get_rect(center=old)
        return combo


    def _get_attack_pool(self):
        return {1:["groundslam","fireline", "charge_melee"],
                2:["groundslam","firewall","grab_walk", "charge_melee"],
                3:["groundslam","meteor","enrage_rush","firewall", "charge_melee"]}[self.phase]
    def _get_windup(self,n):   return self.TUNING["windup"].get(n,900)
    def _get_cooldown(self,n): return self.TUNING["cooldown"].get(n,1200)
    def _get_global_cd(self):  return self.TUNING["global_cd"][self.phase]

    def _start_attack(self, pr):
        n = self.attack_name
        T = self.TUNING
        if n == "groundslam":
            self.vy=T["slam_jump"]; self._slam_landed=False
            self._slam_warned=False; self._slam_warning=None
        elif n == "fireline":
            self._fire_count=0; self._fire_timer=0
            self._fire_dir=1 if pr.centerx>self.rect.centerx else -1
        elif n == "firewall":
            self._fw_count=0; self._fw_timer=0; self._fw_ox=pr.centerx
        elif n == "grab_walk":
            self._grab_hit=False
        elif n == "meteor":
            self._meteor_n=0; self._meteor_t=0
        elif n == "enrage_rush":
            self._rush_dir=1 if pr.centerx>self.rect.centerx else -1
            self.facing_right=self._rush_dir==1
            self.exec_timer=T["rush_dur"]
        elif n == "charge_melee":
            self._charge_dir=1 if pr.centerx>self.rect.centerx else -1
            self.facing_right=self._charge_dir==1
            self.exec_timer=800

    def _exec_attack(self, dt_ms, pr):
        n=self.attack_name; T=self.TUNING
        if   n=="groundslam":  self._ex_slam(dt_ms)
        elif n=="fireline":    self._ex_fire(dt_ms)
        elif n=="firewall":    self._ex_fw(dt_ms)
        elif n=="grab_walk":   self._ex_grab(dt_ms,pr)
        elif n=="meteor":      self._ex_meteor(dt_ms)
        elif n=="enrage_rush": self._ex_rush(dt_ms)
        elif n=="charge_melee": self._ex_charge_melee(dt_ms)

    def _ex_charge_melee(self, dt_ms):
        self.vx = self._charge_dir * 14
        self.exec_timer -= dt_ms
        if self.exec_timer <= 0 or getattr(self, '_hit_wall', False):
            self.vx = 0
            if getattr(self, '_hit_wall', False):
                self._screen_shake_flag = True
                self._play("boss_hit")
            self._end_attack()

    def _ex_slam(self, dt_ms):
        T=self.TUNING
        if self.vy>=0 and not self._slam_warned:
            self._slam_warned=True
            self._slam_warning=SlamWarning(self.rect.centerx,self.floor_y,700,T["slam_warn"])
        if self._slam_warning and not self._slam_warning.done:
            self._slam_warning.update(dt_ms)
        if self.on_ground and self.vy==0 and not self._slam_landed:
            self._slam_landed=True; self.exec_timer=500
            sw=ShockWave(self.rect.centerx,self.floor_y,
                         T["slam_sw_spd"][self.phase],T["slam_sw_h"][self.phase])
            self.shockwaves.add(sw)
            self._screen_shake_flag=True; self._emit_dust(20)
            if self._slam_warning: self._slam_warning.done=True
        if self._slam_landed:
            self.exec_timer-=dt_ms
            if self.exec_timer<=0: self._end_attack()

    def _ex_fire(self, dt_ms):
        T=self.TUNING
        self._fire_timer+=dt_ms
        if self._fire_count<T["fire_count"] and self._fire_timer>=T["fire_ivl"]:
            self._fire_timer=0; self._fire_count+=1
            cx=(self.rect.right+15 if self._fire_dir==1 else self.rect.left-15)
            self.projectiles.add(BossProjectile(
                (cx,self.rect.centery+30),self._fire_dir*T["fire_spd"],0,
                radius=T["fire_r"],color=(255,100,20),max_lifetime=3800))
            self._play("boss_projectile")
        if self._fire_count>=T["fire_count"]:
            self._fire_timer+=0
            if self._fire_timer>=300: self._end_attack()

    def _ex_fw(self, dt_ms):
        T=self.TUNING
        self._fw_timer+=dt_ms
        if self._fw_count<T["fw_cols"] and self._fw_timer>=T["fw_ivl"]:
            self._fw_timer=0; self._fw_count+=1
            offset=(self._fw_count-T["fw_cols"]//2)*100
            x=max(80,min(SCREEN_WIDTH-80,self._fw_ox+offset))
            vy=random.uniform(T["fw_vmin"],T["fw_vmax"])
            self.projectiles.add(BossProjectile(
                (x,-40),0,vy,radius=T["fw_r"],color=(255,80,0),max_lifetime=3200))
            self._play("boss_projectile")
        if self._fw_count>=T["fw_cols"]:
            self.exec_timer-=dt_ms
            if self.exec_timer<=500: self._end_attack()

    def _ex_grab(self, dt_ms, pr):
        T=self.TUNING
        dx=pr.centerx-self.rect.centerx
        if not self._grab_hit:
            spd=T["grab_spd"][self.phase]
            self.vx=spd*(1 if dx>0 else -1); self.facing_right=dx>0
            if abs(dx)<T["grab_rng"]:
                self._grab_hit=True; self.vx=0; self.exec_timer=500
                d=1 if self.facing_right else -1
                cx=(self.rect.right+10 if d==1 else self.rect.left-10)
                self.projectiles.add(BossProjectile(
                    (cx,self.rect.centery+20),d*3,0,
                    radius=T["grab_fist_r"],color=BROWN,max_lifetime=600))
                self._play("boss_hit")
        else:
            self.exec_timer-=dt_ms
            if self.exec_timer<=0: self._end_attack()

    def _ex_meteor(self, dt_ms):
        T=self.TUNING
        self._meteor_t+=dt_ms
        if self._meteor_n<T["meteor_n"] and self._meteor_t>=T["meteor_ivl"]:
            self._meteor_t=0; self._meteor_n+=1
            a=random.uniform(-55,55); spd=random.uniform(T["meteor_vmin"],T["meteor_vmax"])
            rad=math.radians(a-82)
            self.projectiles.add(BossProjectile(
                (self.rect.centerx,self.rect.top-10),
                math.cos(rad)*spd,math.sin(rad)*spd,
                radius=T["meteor_r"],color=GREY,use_gravity=True,max_lifetime=4000))
            self._play("boss_projectile")
        if self._meteor_n>=T["meteor_n"]:
            self.exec_timer-=dt_ms
            if self.exec_timer<=600: self._end_attack()

    def _ex_rush(self, dt_ms):
        self.vx=self._rush_dir*self.TUNING["rush_spd"]
        self.exec_timer-=dt_ms
        if self.exec_timer<=0 or self._hit_wall:
            self.vx=0; self._end_attack()

    def _draw_extras(self, screen, ox, oy):
        if (self.attack_name=="groundslam" and self.attack_state==EXECUTING
                and self._slam_warning and not self._slam_warning.done):
            self._slam_warning.draw(screen, ox, oy)

# ══════════════════════════════════════════════════════════════════════════════
#  BOSS 2 – GLACIUS  (Glace)  ★★★☆☆
# ══════════════════════════════════════════════════════════════════════════════

class Glacius(BossBase):
    NAME     = "GLACIUS"
    HP_MAX   = 2500
    WIDTH    = 552
    HEIGHT   = 288
    THEME_PROJ   = ICE_BLUE
    THEME_SHOCK  = ICE_BLUE
    THEME_BG_TOP = (2,  8, 20)
    THEME_BG_BOT = (5, 20, 50)
    THEME_FLOOR  = (10, 30, 60)
    THEME_WALL   = (5,  15, 38)
    THEME_PLAT   = (30, 70,130)
    THEME_PBORD  = (80,160,220)

    TUNING = {
        "global_cd":  {1: 2500, 2: 1800, 3: 1200},
        "windup":     {
            1: {"punch": 1200, "kick_wave": 1400, "laser_beam": 1500, "massive_smash": 2000},
            2: {"punch": 900,  "kick_wave": 1100, "laser_beam": 1200, "massive_smash": 1600},
            3: {"punch": 600,  "kick_wave": 800,  "laser_beam": 900,  "massive_smash": 1200},
        },
        "cooldown":   {
            1: {"punch": 2000, "kick_wave": 2500, "laser_beam": 3500, "massive_smash": 4000},
            2: {"punch": 1500, "kick_wave": 1800, "laser_beam": 2500, "massive_smash": 3000},
            3: {"punch": 1000, "kick_wave": 1200, "laser_beam": 1800, "massive_smash": 2000},
        }
    }

    def __init__(self, pos, obstacles, floor_y):
        super().__init__(pos, obstacles, floor_y)
        self.HP_MAX = 2500
        self.hp = 2500
        self.phase = 1
        
        self.anim_idx = 0
        self.anim_timer = 0
        self.current_anim_key = "idle"
        self.animations = {}
        self._load_sprites()
        self.image = self.animations["idle"][0]
        self.rect = self.image.get_rect(topleft=pos)
        
        self._laser_placed = False
        
        # Anti-camp variables
        self.camp_timer = 0
        self.last_player_pos = (pos[0], pos[1])
        
        self._kick_hitbox = None

    def _load_sprites(self):
        import os
        base_path = os.path.join(ROOT_DIR, 'assets', 'images', 'monstre', 'boss_glace')
        
        def load_seq(folder_name, prefix):
            frames = []
            dir_path = os.path.join(base_path, folder_name)
            
            actual_dir = dir_path
            if os.path.exists(os.path.join(dir_path, folder_name)):
                actual_dir = os.path.join(dir_path, folder_name)
                
            if not os.path.exists(actual_dir):
                import pygame
                s = pygame.Surface((552, 288), pygame.SRCALPHA)
                return [s]
                
            files = [f for f in os.listdir(actual_dir) if f.endswith('.png')]
            for i in range(1, len(files) + 1):
                path = os.path.join(actual_dir, f"{prefix}_{i}.png")
                if os.path.exists(path):
                    try:
                        import pygame
                        surf = pygame.image.load(path).convert_alpha()
                        cropped = pygame.Surface((184, 96), pygame.SRCALPHA)
                        cropped.blit(surf, (0, 0), (3, 17, 184, 96))
                        cropped = pygame.transform.scale(cropped, (552, 288))
                        frames.append(cropped)
                    except Exception:
                        pass
            if not frames:
                import pygame
                s = pygame.Surface((552, 288), pygame.SRCALPHA)
                return [s]
            return frames

        self.animations["idle"] = load_seq("idle", "idle")
        self.animations["walk"] = load_seq("walk", "walk")
        atk = load_seq("1_atk", "1_atk")
        self.animations["punch"] = atk
        self.animations["kick_wave"] = atk
        self.animations["laser_beam"] = atk
        self.animations["massive_smash"] = atk

    def update(self, player_rect, dt):
        if getattr(self, 'alive', True) == False:
            return
            
        dt_ms = dt * 1000
        
        # Anti-camp tracking
        if getattr(self, 'attack_state', 0) not in (WINDUP, EXECUTING) and getattr(self, 'hp', 0) > 0:
            import math
            dist = math.hypot(player_rect.centerx - self.last_player_pos[0], player_rect.centery - self.last_player_pos[1])
            if dist < 200:
                self.camp_timer += dt_ms
                if self.camp_timer > 3000:
                    self._trigger_teleport(player_rect)
            else:
                self.camp_timer = 0
                self.last_player_pos = (player_rect.centerx, player_rect.centery)
                
        # Call base logic to run state machine
        super().update(player_rect, dt)
        
        # Phase Speed Boost: override the slow 1.2 default speed
        if getattr(self, 'attack_state', 0) == IDLE and self.vx != 0:
            speed = 1.5 + (self.phase * 1.5) # Phase 1: 3.0, Phase 2: 4.5, Phase 3: 6.0
            self.vx = speed if self.vx > 0 else -speed

        self._update_visual(dt_ms)

    def _trigger_teleport(self, pr):
        self.camp_timer = 0
        self.last_player_pos = (pr.centerx, pr.centery) 
        
        target_x = pr.centerx + 250 if pr.centerx < self.rect.centerx else pr.centerx - 250
        test_rect = self.rect.copy()
        test_rect.centerx = target_x
        
        # FIX: Align Y to player's bottom so he doesn't teleport under the stairs
        test_rect.bottom = pr.bottom - 10 
        
        # Slide towards player until safe
        step = -15 if target_x > pr.centerx else 15
        for _ in range(30):
            collision = False
            for obs in self.obstacles:
                if test_rect.colliderect(obs.rect):
                    collision = True
                    break
            if not collision:
                break
            test_rect.x += step
            
        self.rect.topleft = test_rect.topleft
        self.vx = 0
        self.vy = 0 # Prevent gravity buildup
        self.facing_right = pr.centerx > self.rect.centerx
        
        self.attack_name = "massive_smash"
        self.attack_state = WINDUP
        self._massive_windup = 2500
        self.windup_timer = 2500 
        self.cd_timer = 0

    def _update_phase(self):
        if self.hp > 1800:
            new_phase = 1
        elif self.hp > 800:
            new_phase = 2
        else:
            new_phase = 3
            
        if self.phase != new_phase:
            self.phase = new_phase
            self._phase_burst()

    def take_damage(self, amount):
        if self.attack_name == "laser_beam" and getattr(self, 'attack_state', 0) in (WINDUP, EXECUTING):
            return 
        super().take_damage(amount)

    def _get_attack_pool(self):
        pool = ["punch", "massive_smash"]
        if self.phase >= 2:
            pool.append("kick_wave")
            pool.append("laser_beam")
        return pool

    def _get_windup(self, n):   return self.TUNING["windup"][self.phase].get(n, 900)
    def _get_cooldown(self, n): return self.TUNING["cooldown"][self.phase].get(n, 1000)
    def _get_global_cd(self):  return self.TUNING["global_cd"][self.phase]

    def _start_attack(self, pr):
        n = self.attack_name
        self.anim_idx = 0
        self.anim_timer = 0
        
        if n == "laser_beam":
            self._laser_placed = False
            self.exec_timer = 1500
            self._laser_target = (pr.centerx, pr.centery)
        elif n == "kick_wave":
            self._dir = 1 if pr.centerx > self.rect.centerx else -1
            self.facing_right = self._dir == 1
            self.exec_timer = 900 
            self._kick_hitbox = None
        elif n == "punch":
            self._dir = 1 if pr.centerx > self.rect.centerx else -1
            self.facing_right = self._dir == 1
            self.exec_timer = 900
        elif n == "massive_smash":
            self.exec_timer = 900

    def _exec_attack(self, dt_ms, pr):
        n = self.attack_name
        if n == "punch":
            self._ex_punch(dt_ms)
        elif n == "kick_wave":
            self._ex_kick(dt_ms)
        elif n == "laser_beam":
            self._ex_laser(dt_ms)
        elif n == "massive_smash":
            self._ex_massive(dt_ms)

    def _ex_punch(self, dt_ms):
        if self.exec_timer == 900: 
            cx = self.rect.centerx + 130 if self.facing_right else self.rect.centerx - 130
            p = BossProjectile((cx, self.rect.centery), 0, 0, radius=30, color=ICE_BLUE, max_lifetime=150)
            self.projectiles.add(p)
            self._play("boss_hit")
            
        self.exec_timer -= dt_ms
        if self.exec_timer <= 0:
            self._end_attack()

    def _ex_kick(self, dt_ms):
        if self.exec_timer == 900:
            cx = self.rect.right + 10 if self.facing_right else self.rect.left - 10
            self._kick_hitbox = (cx, self.floor_y - 20)
            p = BossProjectile((cx, self.floor_y - 20), self._dir * 12, 0, radius=30, color=ICE_BLUE, max_lifetime=2000)
            p.freezes_player = True
            import pygame
            pygame.draw.polygon(p.image, (255,255,255), [(30, 60), (0, 0), (60, 0)])
            self.projectiles.add(p)
            self._play("boss_projectile")
            
        self.exec_timer -= dt_ms
        if self.exec_timer <= 0:
            self._end_attack()
            self._kick_hitbox = None
            
    def _ex_massive(self, dt_ms):
        if self.exec_timer == 900:
            sw1 = ShockWave(self.rect.centerx, self.floor_y, spread_speed=25, wave_height=120, color=ICE_BLUE)
            self.shockwaves.add(sw1)
            self._screen_shake_flag = True
            self._emit_dust(50, [ICE_BLUE, WHITE])
            self._play("boss_hit")
            self._play("boss_hit")
            
        self.exec_timer -= dt_ms
        if self.exec_timer <= 0:
            self._end_attack()

    def _ex_laser(self, dt_ms):
        if not self._laser_placed:
            self._laser_placed = True
            laser = GlaciusLaserHazard(self.rect.centerx, self.rect.centery - 20, self._laser_target[0], self._laser_target[1])
            self.hazards.add(laser)
            
        self.exec_timer -= dt_ms
        if self.exec_timer <= 0:
            self._end_attack()

    def _update_visual(self, dt_ms):
        anim_key = "idle"
        if getattr(self, 'attack_state', 0) in (WINDUP, EXECUTING):
            anim_key = self.attack_name
        elif self.vx != 0:
            anim_key = "walk"
            
        if anim_key not in self.animations:
            anim_key = "idle"
            
        if self.current_anim_key != anim_key:
            self.current_anim_key = anim_key
            self.anim_idx = 0
            self.anim_timer = 0
            
        frames = self.animations[anim_key]
        if self.anim_idx >= len(frames):
            self.anim_idx = 0
            
        fps = 10
        if anim_key in ["punch", "kick_wave", "laser_beam", "massive_smash"]:
            fps = 15
            
        if getattr(self, 'attack_state', 0) == WINDUP:
            self.anim_idx = 0
        else:
            self.anim_timer += dt_ms
            if self.anim_timer >= 1000 / fps:
                self.anim_timer = 0
                self.anim_idx = (self.anim_idx + 1) % len(frames)
            
        base = frames[self.anim_idx].copy()
        
        if self.attack_name == "laser_beam" and getattr(self, 'attack_state', 0) in (WINDUP, EXECUTING):
            import pygame
            pygame.draw.circle(base, (0, 200, 255, 100), (276, 144), 140, 15)
            pygame.draw.circle(base, (255, 255, 255, 150), (276, 144), 130, 5)
            
        if getattr(self, 'facing_right', True):
            import pygame
            base = pygame.transform.flip(base, True, False)
            
        self.image = base

    def _draw_extras(self, screen, ox, oy):
        import math
        import pygame
        
        if self.attack_name == "massive_smash" and getattr(self, 'attack_state', 0) == WINDUP:
            pct = 1 - (self.windup_timer / max(1, getattr(self, '_massive_windup', self._get_windup("massive_smash"))))
            r = int(400 * pct) 
            if r > 5:
                surf = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                pygame.draw.circle(surf, (0, 150, 255, 80), (r, r), r)
                pygame.draw.circle(surf, (0, 200, 255, 150), (r, r), r, 4)
                screen.blit(surf, (self.rect.centerx - r + ox, self.floor_y - r + oy))
                
        elif self.attack_name == "laser_beam" and getattr(self, 'attack_state', 0) == WINDUP:
            if hasattr(self, '_laser_target'):
                pygame.draw.line(screen, (0, 200, 255, 150), (self.rect.centerx + ox, self.rect.centery + oy), (self._laser_target[0] + ox, self._laser_target[1] + oy), 2)

        if getattr(self, 'attack_state', 0) == EXECUTING:
            if self.attack_name == "kick_wave" and getattr(self, '_kick_hitbox', None):
                hx, hy = self._kick_hitbox
                surf = pygame.Surface((100, 100), pygame.SRCALPHA)
                surf.fill((0, 200, 255, 120))
                pygame.draw.rect(surf, (255, 255, 255, 200), (0, 0, 100, 100), 4)
                screen.blit(surf, (hx - 50 + ox, hy - 50 + oy))


class GlaciusLaserHazard(pygame.sprite.Sprite):
    def __init__(self, x, y, target_x, target_y, duration=1500):
        super().__init__()
        import pygame
        self.born = pygame.time.get_ticks()
        self.life = duration
        self.damage = 5
        
        import math
        dx = target_x - x
        dy = target_y - y
        self.angle = math.atan2(dy, dx)
        self.length = 2500
        
        end_x = x + math.cos(self.angle) * self.length
        end_y = y + math.sin(self.angle) * self.length
        
        min_x = min(x, end_x) - 40
        max_x = max(x, end_x) + 40
        min_y = min(y, end_y) - 40
        max_y = max(y, end_y) + 40
        
        w = int(max_x - min_x)
        h = int(max_y - min_y)
        
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        
        lx1 = x - min_x
        ly1 = y - min_y
        lx2 = end_x - min_x
        ly2 = end_y - min_y
        
        pygame.draw.line(self.image, (0, 100, 255, 80), (lx1, ly1), (lx2, ly2), 80)
        pygame.draw.line(self.image, (0, 150, 255, 120), (lx1, ly1), (lx2, ly2), 60)
        pygame.draw.line(self.image, (0, 200, 255, 180), (lx1, ly1), (lx2, ly2), 30)
        pygame.draw.line(self.image, (255, 255, 255, 255), (lx1, ly1), (lx2, ly2), 10)
        
        self.rect = self.image.get_rect(topleft=(min_x, min_y))
        try:
            self.mask = pygame.mask.from_surface(self.image)
        except Exception:
            pass

    def update(self, obstacles=None):
        import pygame
        if pygame.time.get_ticks() - self.born > self.life:
            self.kill()

# ══════════════════════════════════════════════════════════════════════════════
#  BOSS 3 – GRANIT  (Pierre)  ★★★★☆
# ══════════════════════════════════════════════════════════════════════════════

class Granit(BossBase):
    NAME     = "GRANIT"
    HP_MAX   = 560
    WIDTH    = 190
    HEIGHT   = 200
    THEME_PROJ   = (160,150,140)
    THEME_SHOCK  = LAVA
    THEME_BG_TOP = (12, 8,  5)
    THEME_BG_BOT = (35, 18, 8)
    THEME_FLOOR  = (50, 30, 10)
    THEME_WALL   = (30, 16,  6)
    THEME_PLAT   = (90, 60, 25)
    THEME_PBORD  = (180,100,30)

    TUNING = {
        "global_cd":   {1:2600, 2:1900, 3:1200},
        "windup":      {"double_quake":1200,"rock_hail":1000,"stone_charge":900,
                        "avalanche":1400},
        "cooldown":    {"double_quake":1600,"rock_hail":1400,"stone_charge":1200,
                        "avalanche":2000},
        "quake_spd":   {1:16,2:21,3:26},
        "quake_h":     {1:65,2:85,3:105},
        "hail_n":      7, "hail_ivl":220,"hail_r":24,"hail_vmin":10,"hail_vmax":16,
        "charge_spd":  {1:9,2:12,3:15},
        "aval_n":      18,"aval_ivl":130,
        "armor_phase": 2,   # la phase à partir de laquelle l'armure existe
    }

    def __init__(self, pos, obstacles, floor_y):
        super().__init__(pos, obstacles, floor_y)
        self.HP_MAX=560; self.hp=560
        self._armored=False; self._armor_timer=0
        self._hail_n=0; self._hail_t=0
        self._charge_dir=1
        self._aval_n=0; self._aval_t=0
        self.images={s:self._draw(s) for s in ["idle","windup","attack","enrage","armored"]}
        self.image=self.images["idle"]
        self.rect=self.image.get_rect(topleft=pos)

    def _draw(self, state):
        W, H = self.WIDTH, self.HEIGHT
        surf = pygame.Surface((W,H), pygame.SRCALPHA)
        body = {"idle":(105,100,95),"windup":(130,120,110),
                "attack":(90,85,80),"enrage":(80,70,65),"armored":(140,135,130)}[state]
        # Corps trapu et massif
        pygame.draw.rect(surf,body,(5,H//4,W-10,H*3//4),border_radius=12)
        # Veinures de lave
        lava_col=(255,80,10) if state!="armored" else (100,40,5)
        for i in range(5):
            x1=random.Random(i*7).randint(20,W-20)
            y1=random.Random(i*13).randint(H//3,H-20)
            x2=x1+random.Random(i*17).randint(-30,30)
            y2=y1+random.Random(i*19).randint(10,30)
            pygame.draw.line(surf,lava_col,(x1,y1),(x2,y2),3)
        # Poings ÉNORMES
        for px,py in [(0,H//2),(W,H//2)]:
            pygame.draw.circle(surf,tuple(max(0,c-15) for c in body),(px,py),42)
            pygame.draw.circle(surf,lava_col,(px,py),42,3)
            # Jointures
            for j in range(4):
                a=math.radians(-30+j*20); r2=30
                jx=int(px+r2*math.cos(a)); jy=int(py+r2*math.sin(a))
                pygame.draw.circle(surf,tuple(max(0,c-30) for c in body),(jx,jy),8)
        # Tête sans cou (directement posée sur les épaules)
        pygame.draw.rect(surf,body,(W//2-45,2,90,H//4+20),border_radius=8)
        # Blocs de roche sur la tête
        for bx2,by2,bw2,bh2 in [(W//2-50,0,20,18),(W//2+30,2,18,16),(W//2-10,0,25,14)]:
            pygame.draw.rect(surf,tuple(min(255,c+20) for c in body),(bx2,by2,bw2,bh2),border_radius=3)
        # Yeux-braises
        for ex,ey in [(W//2-20,H//8+5),(W//2+20,H//8+5)]:
            pygame.draw.ellipse(surf,(255,90,10),(ex-12,ey-8,24,16))
            pygame.draw.ellipse(surf,(255,200,50),(ex-6,ey-4,12,8))
        # Armure visible
        if state=="armored":
            pygame.draw.rect(surf,(180,175,170,160),(10,H//4,W-20,H*3//4),border_radius=10)
        return surf

    def _draw_aura(self, base, dt_ms):
        self._aura_tick+=dt_ms
        alpha=int(60+50*math.sin(self._aura_tick/160))
        aura=pygame.Surface((self.WIDTH+40,self.HEIGHT+40),pygame.SRCALPHA)
        pygame.draw.ellipse(aura,(*LAVA,alpha),(0,0,self.WIDTH+40,self.HEIGHT+40))
        combo=pygame.Surface((self.WIDTH+40,self.HEIGHT+40),pygame.SRCALPHA)
        combo.blit(aura,(0,0)); combo.blit(base,(20,20))
        old=self.rect.center; self.rect=combo.get_rect(center=old)
        return combo

    def _get_attack_pool(self):
        return {1:["double_quake","rock_hail"],
                2:["double_quake","rock_hail","stone_charge"],
                3:["double_quake","rock_hail","stone_charge","avalanche"]}[self.phase]
    def _get_windup(self,n):   return self.TUNING["windup"].get(n,1000)
    def _get_cooldown(self,n): return self.TUNING["cooldown"].get(n,1400)
    def _get_global_cd(self):  return self.TUNING["global_cd"][self.phase]

    def take_damage(self, amount):
        if self._armored and amount < 50:   # armure bloque les petits dégâts
            amount = 0
        super().take_damage(amount)

    def _start_attack(self, pr):
        n=self.attack_name; T=self.TUNING
        self._hail_n=0; self._hail_t=0
        self._aval_n=0; self._aval_t=0
        if n=="double_quake":
            self._armored=False
        elif n=="stone_charge":
            self._charge_dir=1 if pr.centerx>self.rect.centerx else -1
            self.facing_right=self._charge_dir==1
        elif n=="rock_hail":
            self._armored=(self.phase>=T["armor_phase"])
            if self._armored: self._armor_timer=3500

    def _exec_attack(self, dt_ms, pr):
        n=self.attack_name
        if n=="double_quake":   self._ex_quake(dt_ms)
        elif n=="rock_hail":    self._ex_hail(dt_ms,pr)
        elif n=="stone_charge": self._ex_charge(dt_ms)
        elif n=="avalanche":    self._ex_aval(dt_ms,pr)
        # Gestion armure
        if self._armored:
            self._armor_timer-=dt_ms
            if self._armor_timer<=0:
                self._armored=False
                key="enrage" if self.phase==3 else "idle"
                self._update_image_key(key)
        if self._armored:
            self._update_image_key("armored")

    def _update_image_key(self, key):
        if key in self.images:
            base=self.images[key].copy()
            if not self.facing_right: base=pygame.transform.flip(base,True,False)
            self.image=base

    def _ex_quake(self, dt_ms):
        T=self.TUNING
        if not hasattr(self,'_quake_done'): self._quake_done=False
        if not self._quake_done:
            self._quake_done=True
            # Deux ondes simultanées (gauche ET droite)
            for cx in [self.rect.centerx]:
                sw=ShockWave(cx,self.floor_y,T["quake_spd"][self.phase],T["quake_h"][self.phase],LAVA)
                self.shockwaves.add(sw)
            # Onde inverse
            sw2=ShockWave(self.rect.centerx,self.floor_y,
                          T["quake_spd"][self.phase],T["quake_h"][self.phase],LAVA)
            sw2.spread_speed=-sw2.spread_speed  # hack: on en ajoute une deuxième miroir
            self.shockwaves.add(sw2)
            self._screen_shake_flag=True; self._emit_dust(25,[(180,160,130),(255,100,20)])
            self.exec_timer=800
            self._play("boss_hit")
        self.exec_timer-=dt_ms
        if self.exec_timer<=0:
            self._quake_done=False; self._end_attack()

    def _ex_hail(self, dt_ms, pr):
        T=self.TUNING
        self._hail_t+=dt_ms
        if self._hail_n<T["hail_n"] and self._hail_t>=T["hail_ivl"]:
            self._hail_t=0; self._hail_n+=1
            x=pr.centerx+random.randint(-200,200)
            x=max(80,min(SCREEN_WIDTH-80,x))
            vy=random.uniform(T["hail_vmin"],T["hail_vmax"])
            self.projectiles.add(BossProjectile(
                (x,-50),0,vy,radius=T["hail_r"],color=STONE,max_lifetime=3000))
            self._play("boss_projectile")
        if self._hail_n>=T["hail_n"]:
            self.exec_timer-=dt_ms
            if self.exec_timer<=500:
                self._armored=False; self._end_attack()

    def _ex_charge(self, dt_ms):
        T=self.TUNING
        self.vx=self._charge_dir*T["charge_spd"][self.phase]
        self.exec_timer-=dt_ms
        if self.exec_timer<=0 or self._hit_wall:
            self.vx=0; self._screen_shake_flag=self._hit_wall
            self._end_attack()

    def _ex_aval(self, dt_ms, pr):
        T=self.TUNING
        self._aval_t+=dt_ms
        if self._aval_n<T["aval_n"] and self._aval_t>=T["aval_ivl"]:
            self._aval_t=0; self._aval_n+=1
            x=random.randint(60,SCREEN_WIDTH-60)
            spd=random.uniform(12,18)
            self.projectiles.add(BossProjectile(
                (x,-40),random.uniform(-1.5,1.5),spd,
                radius=20,color=STONE,use_gravity=False,max_lifetime=3000))
            self._play("boss_projectile")
        if self._aval_n>=T["aval_n"]:
            self.exec_timer-=dt_ms
            if self.exec_timer<=400: self._end_attack()

    def _draw_extras(self, screen, ox, oy): pass


# ══════════════════════════════════════════════════════════════════════════════
#  BOSS 4 – VENTUS  (Air)  ★★★★☆
# ══════════════════════════════════════════════════════════════════════════════

class Ventus(BossBase):
    NAME     = "VENTUS"
    HP_MAX   = 520
    WIDTH    = 130
    HEIGHT   = 210
    THEME_PROJ   = WIND_COL
    THEME_SHOCK  = ELEC_COL
    THEME_BG_TOP = (4,  6, 18)
    THEME_BG_BOT = (8, 14, 35)
    THEME_FLOOR  = (15, 22, 50)
    THEME_WALL   = (8,  12, 30)
    THEME_PLAT   = (40, 55,110)
    THEME_PBORD  = (100,140,220)

    TUNING = {
        "global_cd":   {1:1800, 2:1300, 3:800},
        "windup":      {"tornado":900,"lightning_zenith":1100,"dash_phantom":600,
                        "wind_push":800,"eye_storm":1300},
        "cooldown":    {"tornado":1200,"lightning_zenith":1500,"dash_phantom":700,
                        "wind_push":1000,"eye_storm":2000},
        "tornado_spd": 4, "tornado_r":26,
        "lightning_n": {1:2,2:4,3:6}, "lightning_delay":900,
        "dash_spd":    28, "dash_copies": {1:0,2:1,3:2},
        "push_force":  {1:8,2:11,3:14},
        "storm_shrink":{1:3,2:4,3:5},  # pixels/frame de rétrécissement de la zone
    }

    def __init__(self, pos, obstacles, floor_y):
        super().__init__(pos, obstacles, floor_y)
        self.HP_MAX=520; self.hp=520
        self._invisible=False; self._invis_alpha=255
        self._tornado_t=0; self._tornado_dir=1
        self._lightning_marks=[]  # liste de LightningWarning
        self._lightning_n=0; self._lightning_t=0
        self._dash_done=False
        self._push_done=False
        self._storm_active=False; self._storm_left=80; self._storm_right=SCREEN_WIDTH-80
        self.images={s:self._draw(s) for s in ["idle","windup","attack","enrage"]}
        self.image=self.images["idle"]
        self.rect=self.image.get_rect(topleft=pos)

    def _draw(self, state):
        W,H=self.WIDTH,self.HEIGHT
        surf=pygame.Surface((W,H),pygame.SRCALPHA)
        alpha={"idle":160,"windup":200,"attack":220,"enrage":240}[state]
        body=(180,210,255)
        # Silhouette éthérée (distorsion d'air)
        pygame.draw.ellipse(surf,(*body,alpha//2),(6,H//3,W-12,H*2//3))
        # Ailes de libellule
        wing_col=(200,225,255,alpha-40)
        for pts in [[(W//2,H//3),(0,H//5),(W//4,H//2)],
                    [(W//2,H//3),(W,H//5),(W*3//4,H//2)]]:
            pygame.draw.polygon(surf,wing_col,pts)
            pygame.draw.polygon(surf,(*ELEC_COL,alpha//2),pts,2)
        # Veinures d'électricité dans les ailes
        for i in range(4):
            x1=random.Random(i*3+state.__hash__()%10).randint(W//4,W*3//4)
            y1=random.Random(i*5+state.__hash__()%10).randint(H//5,H//3)
            pygame.draw.line(surf,(*ELEC_COL,alpha),(x1,y1),(x1+random.Random(i*7).randint(-20,20),y1+20),1)
        # Corps central
        pygame.draw.ellipse(surf,(*body,alpha),(W//2-30,H//3-10,60,H//2))
        # Bras fins
        for bx2,d in [(W//2-30,-1),(W//2+30,1)]:
            pygame.draw.line(surf,(*body,alpha),(bx2,H//3+20),(bx2+d*35,H//2+20),8)
        # Tête
        pygame.draw.ellipse(surf,(*body,alpha),(W//2-28,8,56,H//3-10))
        # Yeux électriques
        for ex in [W//2-12,W//2+12]:
            pygame.draw.ellipse(surf,(*ELEC_COL,alpha),(ex-7,H//6,14,10))
            pygame.draw.ellipse(surf,(255,255,255,255),(ex-3,H//6+2,6,6))
        # Éclairs statiques autour du corps
        cx2,cy2=W//2,H//2
        for i in range(6):
            a=math.radians(i*60+state.__hash__()%60)
            r2=40; ex2=int(cx2+r2*math.cos(a)); ey2=int(cy2+r2*math.sin(a))
            pygame.draw.line(surf,(*ELEC_COL,alpha//2),(cx2,cy2),(ex2,ey2),1)
        return surf

    def _draw_aura(self, base, dt_ms):
        self._aura_tick+=dt_ms
        alpha=int(50+45*math.sin(self._aura_tick/150))
        aura=pygame.Surface((self.WIDTH+36,self.HEIGHT+36),pygame.SRCALPHA)
        pygame.draw.ellipse(aura,(*ELEC_COL,alpha),(0,0,self.WIDTH+36,self.HEIGHT+36))
        combo=pygame.Surface((self.WIDTH+36,self.HEIGHT+36),pygame.SRCALPHA)
        combo.blit(aura,(0,0)); combo.blit(base,(18,18))
        old=self.rect.center; self.rect=combo.get_rect(center=old)
        return combo

    def _get_attack_pool(self):
        return {1:["tornado","wind_push"],
                2:["tornado","lightning_zenith","dash_phantom"],
                3:["tornado","lightning_zenith","dash_phantom","eye_storm"]}[self.phase]
    def _get_windup(self,n):   return self.TUNING["windup"].get(n,900)
    def _get_cooldown(self,n): return self.TUNING["cooldown"].get(n,1200)
    def _get_global_cd(self):  return self.TUNING["global_cd"][self.phase]

    def _start_attack(self, pr):
        n=self.attack_name; T=self.TUNING
        self._dash_done=False; self._push_done=False
        self._lightning_marks=[]; self._lightning_n=0; self._lightning_t=0
        if n=="tornado":
            self._tornado_dir=1 if pr.centerx>self.rect.centerx else -1
        elif n=="lightning_zenith":
            count=T["lightning_n"][self.phase]
            for i in range(count):
                x=random.randint(100,SCREEN_WIDTH-100)
                self._lightning_marks.append(LightningWarning(x,self.floor_y,T["lightning_delay"]))
        elif n=="dash_phantom":
            self._dash_target_x=pr.centerx
        elif n=="eye_storm":
            self._storm_active=True
            self._storm_left=80; self._storm_right=SCREEN_WIDTH-80

    def _exec_attack(self, dt_ms, pr):
        n=self.attack_name
        if   n=="tornado":          self._ex_tornado(dt_ms,pr)
        elif n=="lightning_zenith": self._ex_lightning(dt_ms,pr)
        elif n=="dash_phantom":     self._ex_dash(dt_ms,pr)
        elif n=="wind_push":        self._ex_push(dt_ms,pr)
        elif n=="eye_storm":        self._ex_storm(dt_ms,pr)

    def _ex_tornado(self, dt_ms, pr):
        T=self.TUNING
        self._tornado_t+=dt_ms
        if self._tornado_t>=120:
            self._tornado_t=0
            # Tornade = projectile large qui va lentement
            cx=self.rect.right+10 if self._tornado_dir==1 else self.rect.left-10
            self.projectiles.add(BossProjectile(
                (cx,self.rect.centery+20),self._tornado_dir*T["tornado_spd"],0,
                radius=T["tornado_r"],color=WIND_COL,max_lifetime=2200))
            self._play("boss_projectile")
        self.exec_timer-=dt_ms
        if self.exec_timer<=2800: self._end_attack()

    def _ex_lightning(self, dt_ms, pr):
        T=self.TUNING
        for m in self._lightning_marks:
            m.update(dt_ms)
            if m.done and not m.fired:
                m.fired=True
                # Éclair instantané = grand projectile vertical rapide
                self.projectiles.add(BossProjectile(
                    (m.x,-10),0,40,radius=14,color=ELEC_COL,max_lifetime=600))
                self._play("boss_projectile")
        all_done=all(m.fired for m in self._lightning_marks)
        if all_done:
            self.exec_timer-=dt_ms
            if self.exec_timer<=500: self._end_attack()

    def _ex_dash(self, dt_ms, pr):
        T=self.TUNING
        if not self._dash_done:
            self._dash_done=True
            self._invisible=True; self._invis_alpha=30
            tx=pr.rect.left-self.WIDTH-20
            tx=max(50,min(SCREEN_WIDTH-self.WIDTH-50,tx))
            self.rect.x=tx; self.rect.bottom=self.floor_y; self.vy=0
            self.exec_timer=600
            self.projectiles.add(BossProjectile(
                (pr.centerx,pr.centery),0,0,radius=30,color=ELEC_COL,max_lifetime=300))
        self._invis_alpha=min(255,self._invis_alpha+12)
        if self._invis_alpha>=200: self._invisible=False
        self.exec_timer-=dt_ms
        if self.exec_timer<=0: self._end_attack()

    def _ex_push(self, dt_ms, pr):
        if not self._push_done:
            self._push_done=True
            # Projectile de vent (large, rapide, horizontal)
            d=1 if pr.centerx>self.rect.centerx else -1
            for dy in [-20,0,20]:
                self.projectiles.add(BossProjectile(
                    (self.rect.centerx,self.rect.centery+dy),
                    d*self.TUNING["push_force"][self.phase],0,
                    radius=24,color=WIND_COL,max_lifetime=1500))
            self._play("boss_hit")
        self.exec_timer-=dt_ms
        if self.exec_timer<=2500: self._end_attack()

    def _ex_storm(self, dt_ms, pr):
        T=self.TUNING
        shrink=T["storm_shrink"][self.phase]
        self._storm_left +=shrink*dt_ms/16
        self._storm_right-=shrink*dt_ms/16
        if self._storm_right-self._storm_left<300 or self.exec_timer<=0:
            self._storm_active=False; self._end_attack()
        self.exec_timer-=dt_ms

    def _draw_extras(self, screen, ox, oy):
        # Marqueurs d'éclairs
        for m in self._lightning_marks:
            m.draw(screen, ox, oy)
        # Murs de la tempête
        if self._storm_active:
            for x in [int(self._storm_left), int(self._storm_right)-20]:
                s=pygame.Surface((20,SCREEN_HEIGHT),pygame.SRCALPHA)
                for y2 in range(0,SCREEN_HEIGHT,4):
                    a=random.randint(80,180)
                    pygame.draw.line(s,(*ELEC_COL,a),(0,y2),(20,y2),2)
                screen.blit(s,(x+ox,oy))

    def _update_visual(self, dt_ms):
        super()._update_visual(dt_ms)
        if self._invisible:
            self.image.set_alpha(self._invis_alpha)

# ══════════════════════════════════════════════════════════════════════════════
#  BOSS 5 – LE MUTANT  (Tous éléments)  ★★★★★
# ══════════════════════════════════════════════════════════════════════════════

class Mutant(BossBase):
    NAME     = "LE MUTANT"
    HP_MAX   = 800
    WIDTH    = 200
    HEIGHT   = 250
    THEME_PROJ   = (255, 100, 20)
    THEME_SHOCK  = LAVA
    THEME_BG_TOP = (5,   2,  10)
    THEME_BG_BOT = (20,  8,  25)
    THEME_FLOOR  = (30, 15,  35)
    THEME_WALL   = (18,  8,  22)
    THEME_PLAT   = (60, 30,  80)
    THEME_PBORD  = (120,50, 150)

    TUNING = {
        "global_cd":   {1:2000, 2:1400, 3:800},
        "windup":      {"pyros_slam":1000,"glacius_shards":850,"granit_quake":1100,
                        "ventus_lightning":1000,"fusion_hell":1500,"regen_tick":0},
        "cooldown":    {"pyros_slam":1200,"glacius_shards":900,"granit_quake":1400,
                        "ventus_lightning":1100,"fusion_hell":2500,"regen_tick":0},
        "regen_rate":  30,   # HP regagnés par tick en phase 3
        "regen_ivl":   5000, # ms entre chaque regen
    }

    def __init__(self, pos, obstacles, floor_y):
        super().__init__(pos, obstacles, floor_y)
        self.HP_MAX=800; self.hp=800
        # Données communes aux attaques héritées
        self._slam_landed=False; self._slam_warned=False; self._slam_warning=None
        self._shard_n=0; self._shard_t=0; self._shard_dir=1
        self._lightning_marks=[]; self._fw_count=0; self._fw_timer=0; self._fw_ox=0
        self._fusion_t=0; self._fusion_phase_t=0; self._fusion_step=0
        self._regen_t=0
        # Élément dominant actuel (change en phase 3)
        self._dominant=0; self._dom_timer=0; self.DOM_INTERVAL=12000
        self.images={s:self._draw(s) for s in ["idle","windup","attack","enrage"]}
        self.image=self.images["idle"]
        self.rect=self.image.get_rect(topleft=pos)

    def _draw(self, state):
        W,H=self.WIDTH,self.HEIGHT
        surf=pygame.Surface((W,H),pygame.SRCALPHA)
        # Côté droit : feu/pierre (Pyros+Granit)
        fire_col={"idle":(160,60,20),"windup":(200,80,20),
                  "attack":(230,40,5),"enrage":(255,20,0)}[state]
        # Côté gauche : glace/air (Glacius+Ventus)
        ice_col ={"idle":(60,120,200),"windup":(80,150,230),
                  "attack":(40,100,190),"enrage":(20,80,200)}[state]
        # Jambes asymétriques
        pygame.draw.rect(surf,(130,90,50),(15,H-80,50,80),border_radius=10)  # jambe droite (pierre)
        pygame.draw.rect(surf,(50,90,160),(W-65,H-80,50,80),border_radius=10) # jambe gauche (glace)
        # Corps central fendu en deux
        pygame.draw.ellipse(surf,fire_col,(4,H//3,W//2-2,H*2//3))
        pygame.draw.ellipse(surf,ice_col,(W//2,H//3,W//2-4,H*2//3))
        pygame.draw.line(surf,(255,255,255,120),(W//2,H//3),(W//2,H),2)
        # Épaule droite = pierre massive
        pygame.draw.circle(surf,(100,90,85),(16,H//3+15),36)
        pygame.draw.circle(surf,LAVA,(16,H//3+15),36,3)
        # Épaule gauche = glace translucide avec stalactites
        pygame.draw.circle(surf,(*ICE_BLUE,180),(W-16,H//3+15),30)
        for i in range(3):
            a=math.radians(-40+i*40); bx2=int(W-16+28*math.cos(a)); by2=int(H//3+15+28*math.sin(a))
            pygame.draw.line(surf,(*ICE_BLUE,200),(W-16,H//3+15),(bx2,by2),3)
        # Bras droit : lave et pierre (gros)
        pygame.draw.rect(surf,(90,80,75),(-4,H//3+28,35,70),border_radius=10)
        pygame.draw.circle(surf,LAVA,(17,H//3+100),24)
        # Bras gauche : glace fin
        pygame.draw.rect(surf,(*ICE_DARK,200),(W-31,H//3+28,22,60),border_radius=8)
        # Ailes de Ventus (gauche)
        wing=(*WIND_COL,80)
        pygame.draw.polygon(surf,wing,[(W//2,H//3),(W,H//5),(W*3//4,H//2)])
        pygame.draw.polygon(surf,(*ELEC_COL,60),[(W//2,H//3),(W,H//5),(W*3//4,H//2)],1)
        # Carapace de Granit sur le dos
        shell=[(W//2,H//3-5),(W//2-35,H//3+45),(W//2-20,H//3+90),
               (W//2+20,H//3+90),(W//2+35,H//3+45)]
        pygame.draw.polygon(surf,(8,110,12,160),shell)
        # Tête hybride
        pygame.draw.ellipse(surf,fire_col,(W//2-42,5,42,H//3))  # moitié droite feu
        pygame.draw.ellipse(surf,ice_col ,(W//2,5,42,H//3))     # moitié gauche glace
        pygame.draw.line(surf,(255,255,255,100),(W//2,5),(W//2,H//3),2)
        # Corne Pyros (droite)
        pygame.draw.polygon(surf,DARK_RED,[(W//2-8,28),(W//2-22,-20),(W//2+5,20)])
        # Couronne de glace (gauche)
        for i in range(3):
            a=math.radians(20+i*25); bx2=int(W//2+20*math.cos(a)); by2=int(H//6+20*math.sin(a)-25)
            pygame.draw.line(surf,(*ICE_BLUE,200),(W//2+5,H//6),(bx2,by2),3)
        # Œil gauche (Glacius : vide, blanc-bleu)
        pygame.draw.ellipse(surf,(*ICE_BLUE,230),(W//2+10,H//6+5,20,14))
        pygame.draw.ellipse(surf,(255,255,255,255),(W//2+13,H//6+7,8,8))
        # Œil droit (Pyros : braise orange)
        pygame.draw.ellipse(surf,(255,100,10),(W//2-30,H//6+5,20,14))
        pygame.draw.ellipse(surf,(255,220,50),(W//2-26,H//6+7,8,8))
        # Crocs de Pyros
        pygame.draw.arc(surf,DARK_RED,(W//2-40,H//4+15,W-20,22),math.pi,2*math.pi,4)
        for fx2,fw2,fh2 in [(W//2-35,10,15),(W//2-20,10,18),(W//2+10,10,15),(W//2+25,10,18)]:
            pygame.draw.rect(surf,WHITE,(fx2,H//4+19,fw2,fh2),border_radius=2)
        # Cœur en fusion (visible à travers le torse)
        heart=pygame.Surface((30,30),pygame.SRCALPHA)
        for cr,cc in [(14,(255,60,0,120)),(10,(0,180,255,80))]:
            pygame.draw.circle(heart,cc,(15,15),cr)
        surf.blit(heart,(W//2-15,H//2-15))
        return surf

    def _draw_aura(self, base, dt_ms):
        self._aura_tick+=dt_ms
        alpha=int(55+50*math.sin(self._aura_tick/160))
        aura=pygame.Surface((self.WIDTH+50,self.HEIGHT+50),pygame.SRCALPHA)
        # Aura bicolore feu/glace
        pygame.draw.ellipse(aura,(255,60,0,alpha//2),(0,0,self.WIDTH+50,self.HEIGHT+50))
        pygame.draw.ellipse(aura,(*ICE_BLUE,alpha//2),(10,10,self.WIDTH+30,self.HEIGHT+30))
        combo=pygame.Surface((self.WIDTH+50,self.HEIGHT+50),pygame.SRCALPHA)
        combo.blit(aura,(0,0)); combo.blit(base,(25,25))
        old=self.rect.center; self.rect=combo.get_rect(center=old)
        return combo

    def _get_attack_pool(self):
        return {1:["pyros_slam","glacius_shards","granit_quake"],
                2:["pyros_slam","glacius_shards","granit_quake","ventus_lightning"],
                3:["pyros_slam","glacius_shards","granit_quake",
                   "ventus_lightning","fusion_hell"]}[self.phase]
    def _get_windup(self,n):   return self.TUNING["windup"].get(n,1000)
    def _get_cooldown(self,n): return self.TUNING["cooldown"].get(n,1400)
    def _get_global_cd(self):  return self.TUNING["global_cd"][self.phase]

    def _start_attack(self, pr):
        n=self.attack_name
        self._slam_landed=False; self._slam_warned=False; self._slam_warning=None
        self._shard_n=0; self._shard_t=0
        self._lightning_marks=[]; self._fw_count=0; self._fw_timer=0
        self._fusion_t=0; self._fusion_phase_t=0; self._fusion_step=0
        if n=="pyros_slam":
            self.vy=-28
        elif n=="glacius_shards":
            self._shard_dir=1 if pr.centerx>self.rect.centerx else -1
        elif n=="granit_quake":
            pass  # déclenché immédiatement dans _exec
        elif n=="ventus_lightning":
            for i in range(5):
                self._lightning_marks.append(
                    LightningWarning(random.randint(120,SCREEN_WIDTH-120),self.floor_y,900))
        elif n=="fusion_hell":
            self._fw_ox=pr.centerx
            self._fw_count=0; self._fw_timer=0

    def _exec_attack(self, dt_ms, pr):
        n=self.attack_name
        # Régénération phase 3
        if self.phase==3:
            self._regen_t+=dt_ms
            if self._regen_t>=self.TUNING["regen_ivl"]:
                self._regen_t=0
                old_hp = self.hp
                self.hp=min(self.HP_MAX, self.hp+self.TUNING["regen_rate"])
                if self.hp > old_hp:
                    self._play("boss_regen")
        if   n=="pyros_slam":       self._ex_mut_slam(dt_ms)
        elif n=="glacius_shards":   self._ex_mut_shards(dt_ms)
        elif n=="granit_quake":     self._ex_mut_quake(dt_ms)
        elif n=="ventus_lightning": self._ex_mut_lightning(dt_ms)
        elif n=="fusion_hell":      self._ex_fusion(dt_ms,pr)

    def _ex_mut_slam(self, dt_ms):
        if self.vy>=0 and not self._slam_warned:
            self._slam_warned=True
            self._slam_warning=SlamWarning(self.rect.centerx,self.floor_y,700,260,LAVA)
        if self._slam_warning and not self._slam_warning.done:
            self._slam_warning.update(dt_ms)
        if self.on_ground and self.vy==0 and not self._slam_landed:
            self._slam_landed=True; self.exec_timer=700
            self.shockwaves.add(ShockWave(self.rect.centerx,self.floor_y,20,100,LAVA))
            self.shockwaves.add(ShockWave(self.rect.centerx,self.floor_y,16,80,ICE_BLUE))
            self._screen_shake_flag=True; self._emit_dust(30)
            self._play("boss_hit")
            # Aussi des éclats de glace
            for a in range(0,360,45):
                rad=math.radians(a)
                self.projectiles.add(BossProjectile(
                    (self.rect.centerx,self.floor_y-20),
                    math.cos(rad)*6,math.sin(rad)*6,
                    radius=14,color=ICE_BLUE,max_lifetime=1200))
            self._play("boss_projectile")
            if self._slam_warning: self._slam_warning.done=True
        if self._slam_landed:
            self.exec_timer-=dt_ms
            if self.exec_timer<=0: self._end_attack()

    def _ex_mut_shards(self, dt_ms):
        self._shard_t+=dt_ms
        if self._shard_n<5 and self._shard_t>=500:
            self._shard_t=0; self._shard_n+=1
            cx=(self.rect.right+15 if self._shard_dir==1 else self.rect.left-15)
            # Boule de feu ET éclat de glace simultanément
            self.projectiles.add(BossProjectile((cx,self.rect.centery+20),
                self._shard_dir*8,0,radius=26,color=(255,100,20),max_lifetime=3000))
            self.projectiles.add(BossProjectile((cx,self.rect.centery-20),
                self._shard_dir*6,0,radius=20,color=ICE_BLUE,max_lifetime=3000))
            self._play("boss_projectile")
        if self._shard_n>=5:
            self.exec_timer-=dt_ms
            if self.exec_timer<=400: self._end_attack()

    def _ex_mut_quake(self, dt_ms):
        if not hasattr(self,'_mut_quake_done'): self._mut_quake_done=False
        if not self._mut_quake_done:
            self._mut_quake_done=True
            self.shockwaves.add(ShockWave(self.rect.centerx,self.floor_y,22,110,LAVA))
            # Rochers
            for i in range(8):
                x=random.randint(80,SCREEN_WIDTH-80)
                self.projectiles.add(BossProjectile((x,-40),0,random.uniform(12,18),
                    radius=22,color=STONE,max_lifetime=3000))
            self._screen_shake_flag=True; self.exec_timer=900
            self._play("boss_hit")
            self._play("boss_projectile")
        self.exec_timer-=dt_ms
        if self.exec_timer<=0:
            self._mut_quake_done=False; self._end_attack()

    def _ex_mut_lightning(self, dt_ms):
        for m in self._lightning_marks:
            m.update(dt_ms)
            if m.done and not m.fired:
                m.fired=True
                self.projectiles.add(BossProjectile((m.x,-10),0,45,
                    radius=16,color=ELEC_COL,max_lifetime=500))
                self._play("boss_projectile")
        if all(m.fired for m in self._lightning_marks):
            self.exec_timer-=dt_ms
            if self.exec_timer<=400: self._end_attack()

    def _ex_fusion(self, dt_ms, pr):
        """Attaque signature : vortex de feu puis éclairs gelants."""
        self._fusion_t+=dt_ms; self._fusion_phase_t+=dt_ms
        # Étape 0 : vortex de feu (premières 4s)
        if self._fusion_step==0:
            if self._fusion_phase_t<=4000 and self._fusion_t>=100:
                self._fusion_t=0
                a=math.radians(self._fusion_phase_t/4000*720)
                r2=180
                cx=int(pr.centerx+r2*math.cos(a)); cy=int(self.floor_y-100+r2*math.sin(a)*0.3)
                self.projectiles.add(BossProjectile((cx,cy),
                    math.cos(a+math.pi/2)*5,math.sin(a+math.pi/2)*5,
                    radius=22,color=(255,100,20),max_lifetime=1500))
            if self._fusion_phase_t>4000:
                self._fusion_step=1; self._fusion_phase_t=0
        # Étape 1 : éclairs gelants (2s)
        elif self._fusion_step==1:
            if self._fusion_t>=150:
                self._fusion_t=0
                x=random.randint(80,SCREEN_WIDTH-80)
                self.projectiles.add(BossProjectile((x,-30),0,38,
                    radius=18,color=ICE_BLUE,max_lifetime=500))
            if self._fusion_phase_t>2500:
                self._fusion_step=2
        # Étape 2 : fin
        elif self._fusion_step==2:
            self._end_attack()

    def _draw_extras(self, screen, ox, oy):
        if (self.attack_name=="pyros_slam" and self.attack_state==EXECUTING
                and self._slam_warning and not self._slam_warning.done):
            self._slam_warning.draw(screen, ox, oy)
        for m in self._lightning_marks:
            m.draw(screen, ox, oy)


# ══════════════════════════════════════════════════════════════════════════════
#  BOSS ROOM  (universelle – s'adapte au boss passé en paramètre)
# ══════════════════════════════════════════════════════════════════════════════

class BossRoom:
    """
    Arène générique. Passe le boss voulu via boss_class=.
    Interface :
        boss_room.update(dt)
        boss_room.draw(screen)
        boss_room.finished  → True quand le boss est mort
    """

    SHAKE_DURATION = 350

    def __init__(self, player, boss_class=Pyros):
        self.player   = player
        self.finished = False

        self.obstacle_sprites = pygame.sprite.Group()
        W, H = SCREEN_WIDTH, SCREEN_HEIGHT
        self.floor_y = H - 64

        self._build_room(W, H, boss_class)

        bx = W//2 - boss_class.WIDTH//2
        by = self.floor_y - boss_class.HEIGHT - 8
        self.boss = boss_class((bx,by), self.obstacle_sprites, self.floor_y)

        self.background   = self._make_background(W, H, boss_class)
        self._shake_timer = 0
        self._shake_off   = (0,0)
        self._font_big    = pygame.font.SysFont("Comic Sans MS", 80, bold=True)
        self._font_sub    = pygame.font.SysFont("Arial", 36)

    # ── Salle ──────────────────────────────────────────────────────────────────

    def _build_room(self, W, H, bc):
        layout = [
            (pygame.Rect(0,      H-64, W,   64), bc.THEME_FLOOR, None         ),
            (pygame.Rect(0,      0,    36,  H ), bc.THEME_WALL,  None         ),
            (pygame.Rect(W-36,   0,    36,  H ), bc.THEME_WALL,  None         ),
            (pygame.Rect(0,      0,    W,   36), bc.THEME_WALL,  None         ),
            (pygame.Rect(55,     H-300,220, 20), bc.THEME_PLAT,  bc.THEME_PBORD),
            (pygame.Rect(W-275,  H-300,220, 20), bc.THEME_PLAT,  bc.THEME_PBORD),
        ]
        for rect,col,bord in layout:
            t=RoomTile(rect,col,bord)
            self.obstacle_sprites.add(t)

    def _make_background(self, W, H, bc):
        surf=pygame.Surface((W,H))
        for y in range(H):
            t=y/H
            r=int(bc.THEME_BG_TOP[0]*(1-t)+bc.THEME_BG_BOT[0]*t)
            g=int(bc.THEME_BG_TOP[1]*(1-t)+bc.THEME_BG_BOT[1]*t)
            b=int(bc.THEME_BG_TOP[2]*(1-t)+bc.THEME_BG_BOT[2]*t)
            pygame.draw.line(surf,(r,g,b),(0,y),(W,y))
        rng=random.Random(bc.NAME.__hash__()%1000)
        for i in range(4):
            px=int(W*(i+0.5)/4)
            pygame.draw.rect(surf,tuple(max(0,c-15) for c in bc.THEME_FLOOR),
                             (px-20,H//2,40,H//2))
            pygame.draw.rect(surf,bc.THEME_WALL,(px-20,H//2,40,H//2),3)
            pygame.draw.rect(surf,bc.THEME_FLOOR,(px-28,H//2-12,56,16))
            pygame.draw.rect(surf,bc.THEME_PBORD,(px-6,H//2-45,12,28))
            pygame.draw.ellipse(surf,bc.THEME_PROJ if hasattr(bc,'THEME_PROJ') else ORANGE,
                                (px-10,H//2-62,20,24))
        for _ in range(30):
            rx=rng.randint(70,W-70); ry=rng.randint(60,H-80)
            rc=tuple(min(255,c+rng.randint(20,60)) for c in bc.THEME_PLAT)
            pygame.draw.circle(surf,rc,(rx,ry),rng.randint(3,9),2)
        # Dalles de sol
        for i in range(W//80):
            pygame.draw.line(surf,bc.THEME_WALL,(i*80+40,H-64),(i*80+40,H),2)
        return surf

    # ── Screen shake ───────────────────────────────────────────────────────────

    def _trigger_shake(self):
        self._shake_timer=self.SHAKE_DURATION

    def _update_shake(self, dt_ms):
        if self._shake_timer>0:
            self._shake_timer-=dt_ms
            s=int(16*self._shake_timer/self.SHAKE_DURATION)
            self._shake_off=(random.randint(-s,s),random.randint(-s,s))
        else:
            self._shake_off=(0,0)

    # ── Update ─────────────────────────────────────────────────────────────────

    def update(self, dt):
        if self.finished: return
        dt_ms=dt*1000
        self.boss.update(self.player.rect, dt)
        if getattr(self.boss,"_screen_shake_flag",False):
            self._trigger_shake()
        self._update_shake(dt_ms)

        # Hazards boss (sol gelé…)
        self.boss.hazards.update()

        # Dégâts projectiles boss → joueur
        for _ in pygame.sprite.spritecollide(self.player,self.boss.projectiles,True):
            self.player.hp_current=max(0,self.player.hp_current-12)
        # Ondes de choc
        if pygame.sprite.spritecollide(self.player,self.boss.shockwaves,False):
            self.player.hp_current=max(0,self.player.hp_current-1)
        # Hazards (piques, sol gelé)
        for h in pygame.sprite.spritecollide(self.player,self.boss.hazards,False):
            if isinstance(h,IceSpike):
                self.player.hp_current=max(0,self.player.hp_current-8)
            elif isinstance(h,FrozenGround):
                pass  # Glissement géré dans main (on peut ajouter plus tard)

        # Dégâts joueur → boss
        for _ in pygame.sprite.spritecollide(self.boss,self.player.capacite.projectiles,True):
            self.boss.take_damage(25)
        if pygame.sprite.collide_rect(self.player,self.boss):
            self.boss.take_damage(1)

        if not self.boss.alive:
            self.finished=True

    # ── Draw ───────────────────────────────────────────────────────────────────

    def draw(self, screen):
        ox,oy=self._shake_off
        screen.blit(self.background,(ox,oy))

        for tile in self.obstacle_sprites:
            screen.blit(tile.image,(tile.rect.x+ox,tile.rect.y+oy))

        # Hazards (sol gelé visuels déjà gérés dans draw_extras du boss)
        for h in self.boss.hazards:
            if not isinstance(h,FrozenGround):
                screen.blit(h.image,(h.rect.x+ox,h.rect.y+oy))
            else:
                screen.blit(h.image,(h.rect.x+ox,h.rect.y+oy))

        screen.blit(self.player.image,(self.player.rect.x+ox,self.player.rect.y+oy))

        saved=self.boss.rect.copy()
        self.boss.draw(screen,ox,oy)
        self.boss.rect=saved

        for proj in self.boss.projectiles:
            screen.blit(proj.image,(proj.rect.x+ox,proj.rect.y+oy))
        for proj in self.player.capacite.projectiles:
            screen.blit(proj.image,proj.rect)

        if self.boss.alive:
            self.boss.draw_health_bar(screen)

        if self.finished:
            self._draw_victory(screen)

    def _draw_victory(self,screen):
        ov=pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT),pygame.SRCALPHA)
        ov.fill((0,0,0,160)); screen.blit(ov,(0,0))
        f1=pygame.font.SysFont("Comic Sans MS",80,bold=True)
        f2=pygame.font.SysFont("Arial",36)
        t1=f1.render("BOSS VAINCU !",True,YELLOW)
        t2=f2.render("R = Recommencer   |   ECHAP = Quitter",True,WHITE)
        screen.blit(t1,t1.get_rect(center=(SCREEN_WIDTH//2,SCREEN_HEIGHT//2-55)))
        screen.blit(t2,t2.get_rect(center=(SCREEN_WIDTH//2,SCREEN_HEIGHT//2+40)))


# ══════════════════════════════════════════════════════════════════════════════
#  FACTORY – crée la BossRoom avec le bon boss selon l'index
# ══════════════════════════════════════════════════════════════════════════════

BOSS_ROSTER = [Pyros, Glacius, Granit, Ventus, Mutant]

def make_boss_room(player, boss_index):
    """
    boss_index : 0=Pyros 1=Glacius 2=Granit 3=Ventus 4=Mutant
    Retourne une BossRoom prête à être appelée avec .update(dt) / .draw(screen).
    """
    cls = BOSS_ROSTER[boss_index % len(BOSS_ROSTER)]
    return BossRoom(player, cls)
