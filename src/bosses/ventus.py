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
        "storm_shrink":{1:3,2:4,3:5},  
    }
    def __init__(self, pos, obstacles, floor_y):
        super().__init__(pos, obstacles, floor_y)
        self.HP_MAX=520; self.hp=520
        self._invisible=False; self._invis_alpha=255
        self._tornado_t=0; self._tornado_dir=1
        self._lightning_marks=[]  
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
        pygame.draw.ellipse(surf,(*body,alpha//2),(6,H//3,W-12,H*2//3))
        wing_col=(200,225,255,alpha-40)
        for pts in [[(W//2,H//3),(0,H//5),(W//4,H//2)],
                    [(W//2,H//3),(W,H//5),(W*3//4,H//2)]]:
            pygame.draw.polygon(surf,wing_col,pts)
            pygame.draw.polygon(surf,(*ELEC_COL,alpha//2),pts,2)
        for i in range(4):
            x1=random.Random(i*3+state.__hash__()%10).randint(W//4,W*3//4)
            y1=random.Random(i*5+state.__hash__()%10).randint(H//5,H//3)
            pygame.draw.line(surf,(*ELEC_COL,alpha),(x1,y1),(x1+random.Random(i*7).randint(-20,20),y1+20),1)
        pygame.draw.ellipse(surf,(*body,alpha),(W//2-30,H//3-10,60,H//2))
        for bx2,d in [(W//2-30,-1),(W//2+30,1)]:
            pygame.draw.line(surf,(*body,alpha),(bx2,H//3+20),(bx2+d*35,H//2+20),8)
        pygame.draw.ellipse(surf,(*body,alpha),(W//2-28,8,56,H//3-10))
        for ex in [W//2-12,W//2+12]:
            pygame.draw.ellipse(surf,(*ELEC_COL,alpha),(ex-7,H//6,14,10))
            pygame.draw.ellipse(surf,(255,255,255,255),(ex-3,H//6+2,6,6))
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
        for m in self._lightning_marks:
            m.draw(screen, ox, oy)
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
