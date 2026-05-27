import pygame
import math
import random
from config import ROOT_DIR
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
from .base import BossBase
from .utils import BossProjectile, ShockWave, SlamWarning, LightningWarning
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
        "armor_phase": 2,   
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
        pygame.draw.rect(surf,body,(5,H//4,W-10,H*3//4),border_radius=12)
        lava_col=(255,80,10) if state!="armored" else (100,40,5)
        for i in range(5):
            x1=random.Random(i*7).randint(20,W-20)
            y1=random.Random(i*13).randint(H//3,H-20)
            x2=x1+random.Random(i*17).randint(-30,30)
            y2=y1+random.Random(i*19).randint(10,30)
            pygame.draw.line(surf,lava_col,(x1,y1),(x2,y2),3)
        for px,py in [(0,H//2),(W,H//2)]:
            pygame.draw.circle(surf,tuple(max(0,c-15) for c in body),(px,py),42)
            pygame.draw.circle(surf,lava_col,(px,py),42,3)
            for j in range(4):
                a=math.radians(-30+j*20); r2=30
                jx=int(px+r2*math.cos(a)); jy=int(py+r2*math.sin(a))
                pygame.draw.circle(surf,tuple(max(0,c-30) for c in body),(jx,jy),8)
        pygame.draw.rect(surf,body,(W//2-45,2,90,H//4+20),border_radius=8)
        for bx2,by2,bw2,bh2 in [(W//2-50,0,20,18),(W//2+30,2,18,16),(W//2-10,0,25,14)]:
            pygame.draw.rect(surf,tuple(min(255,c+20) for c in body),(bx2,by2,bw2,bh2),border_radius=3)
        for ex,ey in [(W//2-20,H//8+5),(W//2+20,H//8+5)]:
            pygame.draw.ellipse(surf,(255,90,10),(ex-12,ey-8,24,16))
            pygame.draw.ellipse(surf,(255,200,50),(ex-6,ey-4,12,8))
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
        if self._armored and amount < 50:   
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
            for cx in [self.rect.centerx]:
                sw=ShockWave(cx,self.floor_y,T["quake_spd"][self.phase],T["quake_h"][self.phase],LAVA)
                self.shockwaves.add(sw)
            sw2=ShockWave(self.rect.centerx,self.floor_y,
                          T["quake_spd"][self.phase],T["quake_h"][self.phase],LAVA)
            sw2.spread_speed=-sw2.spread_speed  
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
