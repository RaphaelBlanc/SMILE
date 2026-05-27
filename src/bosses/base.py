import pygame
import math
import random
from config import ROOT_DIR
from .utils import BossProjectile, ShockWave, SlamWarning, LightningWarning
GRAVITY       = 0.8
SCREEN_WIDTH  = 1920
SCREEN_HEIGHT = 1072
IDLE      = "idle"
WINDUP    = "windup"
EXECUTING = "executing"
COOLDOWN  = "cooldown"
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
class RoomTile(pygame.sprite.Sprite):
    def __init__(self, rect, color, border=None):
        super().__init__()
        self.image = pygame.Surface((rect.width, rect.height))
        self.image.fill(color)
        if border:
            pygame.draw.rect(self.image, border, (0,0,rect.width,rect.height), 3)
        self.rect = rect
class BossBase(pygame.sprite.Sprite):
    HP_MAX = 400
    WIDTH  = 160
    HEIGHT = 220
    NAME   = "???"
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
        self.hazards      = pygame.sprite.Group()  
        self.particles    = []
        self._aura_tick   = 0
        self._aura_alpha  = 0
        self.images       = {}
        self.image        = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)
        self.rect         = self.image.get_rect(topleft=pos)
        self._font_warn   = pygame.font.SysFont("Arial Black", 30, bold=True)
        self.sound_manager = None
    def _play(self, name):
        if self.sound_manager:
            self.sound_manager.play(name)
    def _get_attack_pool(self):      return []
    def _get_windup(self, name):     return 900
    def _get_cooldown(self, name):   return 1200
    def _get_global_cd(self):        return self.TUNING["global_cd"][self.phase]
    def _start_attack(self, pr):     pass
    def _exec_attack(self, dt, pr):  pass
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
class BossRoom:
    SHAKE_DURATION = 350
    def __init__(self, player, boss_class=None):
        if boss_class is None:
            from .pyros import Pyros
            boss_class = Pyros
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
        for i in range(W//80):
            pygame.draw.line(surf,bc.THEME_WALL,(i*80+40,H-64),(i*80+40,H),2)
        return surf
    def _trigger_shake(self):
        self._shake_timer=self.SHAKE_DURATION
    def _update_shake(self, dt_ms):
        if self._shake_timer>0:
            self._shake_timer-=dt_ms
            s=int(16*self._shake_timer/self.SHAKE_DURATION)
            self._shake_off=(random.randint(-s,s),random.randint(-s,s))
        else:
            self._shake_off=(0,0)
    def update(self, dt):
        if self.finished: return
        dt_ms=dt*1000
        self.boss.update(self.player.rect, dt)
        if getattr(self.boss,"_screen_shake_flag",False):
            self._trigger_shake()
        self._update_shake(dt_ms)
        self.boss.hazards.update()
        for _ in pygame.sprite.spritecollide(self.player,self.boss.projectiles,True):
            self.player.hp_current=max(0,self.player.hp_current-12)
        if pygame.sprite.spritecollide(self.player,self.boss.shockwaves,False):
            self.player.hp_current=max(0,self.player.hp_current-1)
        for h in pygame.sprite.spritecollide(self.player,self.boss.hazards,False):
            if isinstance(h,IceSpike):
                self.player.hp_current=max(0,self.player.hp_current-8)
            elif isinstance(h,FrozenGround):
                pass  
        for _ in pygame.sprite.spritecollide(self.boss,self.player.capacite.projectiles,True):
            self.boss.take_damage(25)
        if pygame.sprite.collide_rect(self.player,self.boss):
            self.boss.take_damage(1)
        if not self.boss.alive:
            self.finished=True
    def draw(self, screen):
        ox,oy=self._shake_off
        screen.blit(self.background,(ox,oy))
        for tile in self.obstacle_sprites:
            screen.blit(tile.image,(tile.rect.x+ox,tile.rect.y+oy))
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
