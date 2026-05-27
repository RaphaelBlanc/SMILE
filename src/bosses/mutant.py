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
        "regen_rate":  30,   
        "regen_ivl":   5000, 
    }
    def __init__(self, pos, obstacles, floor_y):
        super().__init__(pos, obstacles, floor_y)
        self.HP_MAX=800; self.hp=800
        self._slam_landed=False; self._slam_warned=False; self._slam_warning=None
        self._shard_n=0; self._shard_t=0; self._shard_dir=1
        self._lightning_marks=[]; self._fw_count=0; self._fw_timer=0; self._fw_ox=0
        self._fusion_t=0; self._fusion_phase_t=0; self._fusion_step=0
        self._regen_t=0
        self._dominant=0; self._dom_timer=0; self.DOM_INTERVAL=12000
        self.images={s:self._draw(s) for s in ["idle","windup","attack","enrage"]}
        self.image=self.images["idle"]
        self.rect=self.image.get_rect(topleft=pos)
    def _draw(self, state):
        W,H=self.WIDTH,self.HEIGHT
        surf=pygame.Surface((W,H),pygame.SRCALPHA)
        fire_col={"idle":(160,60,20),"windup":(200,80,20),
                  "attack":(230,40,5),"enrage":(255,20,0)}[state]
        ice_col ={"idle":(60,120,200),"windup":(80,150,230),
                  "attack":(40,100,190),"enrage":(20,80,200)}[state]
        pygame.draw.rect(surf,(130,90,50),(15,H-80,50,80),border_radius=10)  
        pygame.draw.rect(surf,(50,90,160),(W-65,H-80,50,80),border_radius=10) 
        pygame.draw.ellipse(surf,fire_col,(4,H//3,W//2-2,H*2//3))
        pygame.draw.ellipse(surf,ice_col,(W//2,H//3,W//2-4,H*2//3))
        pygame.draw.line(surf,(255,255,255,120),(W//2,H//3),(W//2,H),2)
        pygame.draw.circle(surf,(100,90,85),(16,H//3+15),36)
        pygame.draw.circle(surf,LAVA,(16,H//3+15),36,3)
        pygame.draw.circle(surf,(*ICE_BLUE,180),(W-16,H//3+15),30)
        for i in range(3):
            a=math.radians(-40+i*40); bx2=int(W-16+28*math.cos(a)); by2=int(H//3+15+28*math.sin(a))
            pygame.draw.line(surf,(*ICE_BLUE,200),(W-16,H//3+15),(bx2,by2),3)
        pygame.draw.rect(surf,(90,80,75),(-4,H//3+28,35,70),border_radius=10)
        pygame.draw.circle(surf,LAVA,(17,H//3+100),24)
        pygame.draw.rect(surf,(*ICE_DARK,200),(W-31,H//3+28,22,60),border_radius=8)
        wing=(*WIND_COL,80)
        pygame.draw.polygon(surf,wing,[(W//2,H//3),(W,H//5),(W*3//4,H//2)])
        pygame.draw.polygon(surf,(*ELEC_COL,60),[(W//2,H//3),(W,H//5),(W*3//4,H//2)],1)
        shell=[(W//2,H//3-5),(W//2-35,H//3+45),(W//2-20,H//3+90),
               (W//2+20,H//3+90),(W//2+35,H//3+45)]
        pygame.draw.polygon(surf,(8,110,12,160),shell)
        pygame.draw.ellipse(surf,fire_col,(W//2-42,5,42,H//3))  
        pygame.draw.ellipse(surf,ice_col ,(W//2,5,42,H//3))     
        pygame.draw.line(surf,(255,255,255,100),(W//2,5),(W//2,H//3),2)
        pygame.draw.polygon(surf,DARK_RED,[(W//2-8,28),(W//2-22,-20),(W//2+5,20)])
        for i in range(3):
            a=math.radians(20+i*25); bx2=int(W//2+20*math.cos(a)); by2=int(H//6+20*math.sin(a)-25)
            pygame.draw.line(surf,(*ICE_BLUE,200),(W//2+5,H//6),(bx2,by2),3)
        pygame.draw.ellipse(surf,(*ICE_BLUE,230),(W//2+10,H//6+5,20,14))
        pygame.draw.ellipse(surf,(255,255,255,255),(W//2+13,H//6+7,8,8))
        pygame.draw.ellipse(surf,(255,100,10),(W//2-30,H//6+5,20,14))
        pygame.draw.ellipse(surf,(255,220,50),(W//2-26,H//6+7,8,8))
        pygame.draw.arc(surf,DARK_RED,(W//2-40,H//4+15,W-20,22),math.pi,2*math.pi,4)
        for fx2,fw2,fh2 in [(W//2-35,10,15),(W//2-20,10,18),(W//2+10,10,15),(W//2+25,10,18)]:
            pygame.draw.rect(surf,WHITE,(fx2,H//4+19,fw2,fh2),border_radius=2)
        heart=pygame.Surface((30,30),pygame.SRCALPHA)
        for cr,cc in [(14,(255,60,0,120)),(10,(0,180,255,80))]:
            pygame.draw.circle(heart,cc,(15,15),cr)
        surf.blit(heart,(W//2-15,H//2-15))
        return surf
    def _draw_aura(self, base, dt_ms):
        self._aura_tick+=dt_ms
        alpha=int(55+50*math.sin(self._aura_tick/160))
        aura=pygame.Surface((self.WIDTH+50,self.HEIGHT+50),pygame.SRCALPHA)
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
            pass  
        elif n=="ventus_lightning":
            for i in range(5):
                self._lightning_marks.append(
                    LightningWarning(random.randint(120,SCREEN_WIDTH-120),self.floor_y,900))
        elif n=="fusion_hell":
            self._fw_ox=pr.centerx
            self._fw_count=0; self._fw_timer=0
    def _exec_attack(self, dt_ms, pr):
        n=self.attack_name
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
        self._fusion_t+=dt_ms; self._fusion_phase_t+=dt_ms
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
        elif self._fusion_step==1:
            if self._fusion_t>=150:
                self._fusion_t=0
                x=random.randint(80,SCREEN_WIDTH-80)
                self.projectiles.add(BossProjectile((x,-30),0,38,
                    radius=18,color=ICE_BLUE,max_lifetime=500))
            if self._fusion_phase_t>2500:
                self._fusion_step=2
        elif self._fusion_step==2:
            self._end_attack()
    def _draw_extras(self, screen, ox, oy):
        if (self.attack_name=="pyros_slam" and self.attack_state==EXECUTING
                and self._slam_warning and not self._slam_warning.done):
            self._slam_warning.draw(screen, ox, oy)
        for m in self._lightning_marks:
            m.draw(screen, ox, oy)
