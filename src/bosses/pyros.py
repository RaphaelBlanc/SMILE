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
class Pyros(BossBase):
    NAME     = "PYROS"
    HP_MAX   = 400
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
        return {1:["groundslam","fireline"],
                2:["groundslam","firewall","grab_walk"],
                3:["groundslam","meteor","enrage_rush","firewall"]}[self.phase]
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
    def _exec_attack(self, dt_ms, pr):
        n=self.attack_name; T=self.TUNING
        if   n=="groundslam":  self._ex_slam(dt_ms)
        elif n=="fireline":    self._ex_fire(dt_ms)
        elif n=="firewall":    self._ex_fw(dt_ms)
        elif n=="grab_walk":   self._ex_grab(dt_ms,pr)
        elif n=="meteor":      self._ex_meteor(dt_ms)
        elif n=="enrage_rush": self._ex_rush(dt_ms)
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
