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
class ChienEnrage(BaseEnemy):
    PATROL_SPEED  = 3
    PATROL_RADIUS = 120
    CHASE_SPEED   = 4.5
    SLIDE_SPEED   = 9
    SLIDE_DECAY   = 0.15
    TURN_DELAY    = 45
    DETECT_RANGE  = 750
    LOSE_RANGE    = 1100
    ATTACK_RANGE  = 70  
    ATTACK_DAMAGE = 15
    ATTACK_CD     = 90
    JUMP_OVER_THRESHOLD = 20
    ST_WANDER = "wander"
    ST_RETURN = "return"
    ST_CHASE  = "chase"
    ST_ATTACK = "attack"
    ST_SLIDE  = "slide"
    ST_HURT   = "hurt"
    ST_DEAD   = "dead"
    def __init__(self, pos, groups):
        super().__init__(pos, hp=60, groups=groups, capacite_absorbable="dash")
        self.CONTACT_COOLDOWN = 80
        self.animations = self._load_animations()
        self.animator = Animator(self.animations, fps=12)
        if "idle" in self.animations and self.animations["idle"]:
            self.image = self.animations["idle"][0]
        else:
            self.image = self._make_placeholder()
        self.rect  = self.image.get_rect(topleft=pos)
        self.state        = self.ST_WANDER
        self.facing_right = True
        self.slide_vx     = 0.0
        self.turn_timer   = 0
        self.attack_timer = 0
        self.charge_timer = 0  
        self.vy           = 0
    def _load_animations(self):
        animations = {}
        TARGET_SIZE = (160, 160) 
        path_option1 = os.path.join(CURRENT_DIR, "assets", "images", "monstre", "wolf")
        path_option2 = os.path.join(os.path.dirname(CURRENT_DIR), "assets", "images", "monstre", "wolf")
        sheet_dir = path_option1 if os.path.isdir(path_option1) else path_option2
        file_mapping = {
            "idle":   "Idle.png",
            "wander": "walk.png",
            "return": "walk.png",
            "chase":  "Run.png",
            "attack": "Attack_1.png",
            "slide":  "Run+Attack.png",
            "hurt":   "Hurt.png",
            "dead":   "Dead.png"
        }
        for state, fname in file_mapping.items():
            path = os.path.join(sheet_dir, fname)
            frames = []
            if os.path.isfile(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    w, h = img.get_size()
                    if w > h:
                        frame_size = h
                        num_frames = w // frame_size
                        for i in range(num_frames):
                            rect = pygame.Rect(i * frame_size, 0, frame_size, frame_size)
                            frame = img.subsurface(rect).copy()
                            frame = pygame.transform.scale(frame, TARGET_SIZE)
                            frames.append(frame)
                    else:
                        frame = pygame.transform.scale(img, TARGET_SIZE)
                        frames.append(frame)
                except pygame.error as e:
                    print(f"⚠️ Erreur de chargement pour {fname} : {e}")
            if frames:
                animations[state] = frames
        if "idle" in animations:
            animations["idle_right"] = animations["idle"]
        elif "wander" in animations:
            animations["idle_right"] = animations["wander"]
        else:
            animations["idle_right"] = [self._make_placeholder()]
        return animations
    @staticmethod
    def _make_placeholder():
        s = pygame.Surface((160, 160), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        pygame.draw.ellipse(s, BROWN, (20, 60, 120, 60))
        return s
    def _get_anim_frame(self, anim_state, loop=True):
        dt = 1.0 / 60.0  
        if anim_state in ["chase", "slide"]:
            self.animator.animation_speed = 1.0 / 14
        elif anim_state == "attack":
            self.animator.animation_speed = 1.0 / 12
        else:
            self.animator.animation_speed = 1.0 / 10
        surf = self.animator.get_current_frame(dt, anim_state, loop=loop)
        if not self.facing_right:
            surf = pygame.transform.flip(surf, True, False)
        frames = self.animator.animations.get(anim_state, [])
        done = (not loop) and len(frames) > 0 and self.animator.frame_index >= len(frames) - 1
        return surf, done
    def _player_jumping_over(self, player):
        horizontalement_proche = abs(player.rect.centerx - self.rect.centerx) < 60
        clairement_au_dessus   = player.rect.bottom < self.rect.top - self.JUMP_OVER_THRESHOLD
        en_l_air               = getattr(player, 'vy', 0) != 0 or not getattr(player, 'on_ground', True)
        return horizontalement_proche and clairement_au_dessus and en_l_air
    def update(self, player, obstacles):
        if self.dead:
            surf, done = self._get_anim_frame("dead", loop=False)
            self.image = surf
            if done:
                self.death_finished = True
            return
        self.tick_contact_timer()
        self._apply_gravity(obstacles)
        dist = self.distance_to(player.rect)
        if self.attack_timer > 0: self.attack_timer -= 1
        if self.charge_timer > 0: self.charge_timer -= 1
        if self.state in (self.ST_WANDER, self.ST_RETURN):
            if dist < self.DETECT_RANGE:
                self.state = self.ST_CHASE
                if getattr(self, 'sound_manager', None):
                    self.sound_manager.play("chien_detect")
        elif self.state == self.ST_CHASE:
            if self._player_jumping_over(player):
                d = 1 if player.rect.centerx > self.rect.centerx else -1
                self._enter_slide(d)
            elif 150 < dist < 400 and self.charge_timer <= 0:
                d = 1 if player.rect.centerx > self.rect.centerx else -1
                self._enter_slide(d)
                self.charge_timer = 180 
            elif dist <= self.ATTACK_RANGE and self.attack_timer <= 0:
                self.state = self.ST_ATTACK
                self.animator.current_state = "attack"
                self.animator.frame_index = 0
            elif dist > self.LOSE_RANGE:
                self.state = self.ST_RETURN
        elif self.state == self.ST_ATTACK:
            surf, done = self._get_anim_frame("attack", loop=False)
            self.image = surf
            if done:
                if self.contact_timer <= 0 and dist <= self.ATTACK_RANGE + 30:
                    player.take_damage(self.ATTACK_DAMAGE)
                    self.contact_timer = self.CONTACT_COOLDOWN
                    if getattr(self, 'sound_manager', None):
                        self.sound_manager.play("chien_attack")
                self.attack_timer = self.ATTACK_CD
                self.state = self.ST_CHASE
            return 
        elif self.state == self.ST_SLIDE:
            if abs(self.slide_vx) < 0.5:
                self.slide_vx = 0.0
                self.state = self.ST_CHASE if dist < self.LOSE_RANGE else self.ST_RETURN
        if self.state == self.ST_WANDER:
            self._do_wander(obstacles)
            self.image, _ = self._get_anim_frame("wander")
        elif self.state == self.ST_RETURN:
            if self._do_return_to_spawn(obstacles):
                self.state = self.ST_WANDER
            self.image, _ = self._get_anim_frame("return")
        elif self.state == self.ST_CHASE:
            self._do_chase(player, obstacles)
            self.image, _ = self._get_anim_frame("chase")
        elif self.state == self.ST_SLIDE:
            self._do_slide(obstacles)
            if self.rect.colliderect(player.rect):
                self.slide_vx = 0.0 
                if self.attack_timer <= 0:
                    self.state = self.ST_ATTACK
                    self.animator.current_state = "attack"
                    self.animator.frame_index = 0
            else:
                self.image, _ = self._get_anim_frame("slide")
    def take_damage(self, amount):
        super().take_damage(amount)
        if not self.dead:
            if self.state == self.ST_ATTACK:
                self.state = self.ST_CHASE
            self.animator.current_state = "hurt"
            self.animator.frame_index = 0
            self.image, _ = self._get_anim_frame("hurt", loop=False)
    def on_death(self):
        self.animator.current_state = "dead"
        self.animator.frame_index = 0
        self.image, _ = self._get_anim_frame("dead", loop=False)
        if getattr(self, 'sound_manager', None):
            self.sound_manager.play("chien_death")
    def _do_chase(self, player, obstacles):
        if self.turn_timer > 0:
            self.turn_timer -= 1
            return
        d = 1 if player.rect.centerx > self.rect.centerx else -1
        if (d == 1) != self.facing_right:
            self.turn_timer   = self.TURN_DELAY
            self.facing_right = (d == 1)
            return
        self._try_move(d * self.CHASE_SPEED, obstacles)
    def _enter_slide(self, direction):
        self.state        = self.ST_SLIDE
        self.slide_vx     = self.SLIDE_SPEED * direction
        self.facing_right = (direction == 1)
    def _do_slide(self, obstacles):
        self._try_move(self.slide_vx, obstacles)
        if self.slide_vx > 0:
            self.slide_vx = max(0.0, self.slide_vx - self.SLIDE_DECAY)
        else:
            self.slide_vx = min(0.0, self.slide_vx + self.SLIDE_DECAY)          
class Deer(BaseEnemy):
    PATROL_SPEED  = 1.5
    PATROL_RADIUS = 100
    FLEE_SPEED    = 4.0
    DETECT_RANGE  = 400
    LOSE_RANGE    = 700
    ATTACK_DAMAGE = 0
    ST_WANDER = "wander"
    ST_RETURN = "return"
    ST_FLEE   = "flee"
    def __init__(self, pos, groups):
        super().__init__(pos, hp=20, groups=groups, capacite_absorbable=None)
        self.CONTACT_COOLDOWN = 60
        self.animations = self._load_animations()
        self.animator = Animator(self.animations, fps=8)
        if "idle" in self.animations and self.animations["idle"]:
            self.image = self.animations["idle"][0]
        else:
            self.image = pygame.Surface((64, 64))
            self.image.fill((150, 110, 80))
        self.rect  = self.image.get_rect(topleft=pos)
        self.state        = self.ST_WANDER
        self.facing_right = True
        self.vy           = 0
    def _load_animations(self):
        animations = {}
        TARGET_SIZE = (64, 64)
        path_option1 = os.path.join(CURRENT_DIR, "assets", "images", "monstre", "Deer", "Deer")
        path_option2 = os.path.join(os.path.dirname(CURRENT_DIR), "assets", "images", "monstre", "Deer", "Deer")
        sheet_dir = path_option1 if os.path.isdir(path_option1) else path_option2
        file_mapping = {
            "idle":   "Deer_Idle.png",
            "wander": "Deer_Walk.png",
            "flee":   "Deer_Run.png",
            "hurt":   "Deer_Hurt.png",
            "dead":   "Deer_Death.png"
        }
        for state, fname in file_mapping.items():
            path = os.path.join(sheet_dir, fname)
            frames = []
            if os.path.isfile(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    w, h = img.get_size()
                    row_index = 3
                    row_y = row_index * 32
                    num_frames = w // 32
                    for i in range(num_frames):
                        rect = pygame.Rect(i * 32, row_y, 32, 32)
                        frame = img.subsurface(rect).copy()
                        frame = pygame.transform.scale(frame, TARGET_SIZE)
                        frames.append(frame)
                except pygame.error as e:
                    print(f"⚠️ Erreur de chargement pour {fname} : {e}")
            if frames:
                animations[state] = frames
        if "idle" not in animations:
            if "wander" in animations:
                animations["idle"] = animations["wander"]
            else:
                s = pygame.Surface(TARGET_SIZE, pygame.SRCALPHA)
                pygame.draw.ellipse(s, (150, 110, 80), (16, 16, 32, 32))
                animations["idle"] = [s]
        return animations
    def _get_anim_frame(self, anim_state, loop=True):
        dt = 1.0 / 60.0  
        if anim_state == "flee":
            self.animator.animation_speed = 1.0 / 12
        else:
            self.animator.animation_speed = 1.0 / 8
        surf = self.animator.get_current_frame(dt, anim_state, loop=loop)
        if not self.facing_right:
            surf = pygame.transform.flip(surf, True, False)
        frames = self.animator.animations.get(anim_state, [])
        done = (not loop) and len(frames) > 0 and self.animator.frame_index >= len(frames) - 1
        return surf, done
    def update(self, player, obstacles):
        if self.dead:
            surf, done = self._get_anim_frame("dead", loop=False)
            self.image = surf
            if done:
                self.death_finished = True
            return
        self.tick_contact_timer()
        self._apply_gravity(obstacles)
        dist = self.distance_to(player.rect)
        if dist < self.DETECT_RANGE:
            self.state = self.ST_FLEE
        elif self.state == self.ST_FLEE and dist > self.LOSE_RANGE:
            self.state = self.ST_WANDER
        if self.state == self.ST_WANDER:
            tx = self._patrol_targets[self._patrol_idx]
            d = 1 if tx > self.rect.centerx else -1
            self.facing_right = (d == 1)
            self._do_wander(obstacles)
        elif self.state == self.ST_FLEE:
            d = 1 if self.rect.centerx > player.rect.centerx else -1
            self.facing_right = (d == 1)
            self._try_move(d * self.FLEE_SPEED, obstacles)
        anim_state = "idle"
        loop = True
        if self.dead:
            anim_state = "dead"
            loop = False
        elif self.state == self.ST_FLEE:
            anim_state = "flee"
        elif self.state == self.ST_WANDER:
            anim_state = "wander"
        self.image, _ = self._get_anim_frame(anim_state, loop=loop)
    def on_death(self):
        self.animator.current_state = "dead"
        self.animator.frame_index = 0
class Fox(BaseEnemy):
    PATROL_SPEED  = 2.0
    PATROL_RADIUS = 80
    FLEE_SPEED    = 4.5
    DETECT_RANGE  = 350
    LOSE_RANGE    = 600
    ATTACK_DAMAGE = 0
    ST_WANDER = "wander"
    ST_RETURN = "return"
    ST_FLEE   = "flee"
    def __init__(self, pos, groups):
        super().__init__(pos, hp=20, groups=groups, capacite_absorbable=None)
        self.CONTACT_COOLDOWN = 60
        self.animations = self._load_animations()
        self.animator = Animator(self.animations, fps=8)
        if "idle" in self.animations and self.animations["idle"]:
            self.image = self.animations["idle"][0]
        else:
            self.image = pygame.Surface((64, 64))
            self.image.fill((240, 120, 30))
        self.rect  = self.image.get_rect(topleft=pos)
        self.state        = self.ST_WANDER
        self.facing_right = True
        self.vy           = 0
    def _load_animations(self):
        animations = {}
        TARGET_SIZE = (64, 64)
        path_option1 = os.path.join(CURRENT_DIR, "assets", "images", "monstre", "Fox", "Fox")
        path_option2 = os.path.join(os.path.dirname(CURRENT_DIR), "assets", "images", "monstre", "Fox", "Fox")
        sheet_dir = path_option1 if os.path.isdir(path_option1) else path_option2
        file_mapping = {
            "idle":   "Fox_Idle.png",
            "wander": "Fox_walk.png",
            "flee":   "Fox_Run.png",
            "hurt":   "Fox_Hurt.png",
            "dead":   "Fox_Death.png"
        }
        for state, fname in file_mapping.items():
            path = os.path.join(sheet_dir, fname)
            frames = []
            if os.path.isfile(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    w, h = img.get_size()
                    row_index = 3
                    row_y = row_index * 32
                    num_frames = w // 32
                    for i in range(num_frames):
                        rect = pygame.Rect(i * 32, row_y, 32, 32)
                        frame = img.subsurface(rect).copy()
                        frame = pygame.transform.scale(frame, TARGET_SIZE)
                        frames.append(frame)
                except pygame.error as e:
                    print(f"⚠️ Erreur de chargement pour {fname} : {e}")
            if frames:
                animations[state] = frames
        if "idle" not in animations:
            if "wander" in animations:
                animations["idle"] = animations["wander"]
            else:
                s = pygame.Surface(TARGET_SIZE, pygame.SRCALPHA)
                pygame.draw.ellipse(s, (240, 120, 30), (16, 16, 32, 32))
                animations["idle"] = [s]
        return animations
    def _get_anim_frame(self, anim_state, loop=True):
        dt = 1.0 / 60.0  
        if anim_state == "flee":
            self.animator.animation_speed = 1.0 / 12
        else:
            self.animator.animation_speed = 1.0 / 8
        surf = self.animator.get_current_frame(dt, anim_state, loop=loop)
        if anim_state == "flee":
            if self.facing_right:
                surf = pygame.transform.flip(surf, True, False)
        else:
            if not self.facing_right:
                surf = pygame.transform.flip(surf, True, False)
        frames = self.animator.animations.get(anim_state, [])
        done = (not loop) and len(frames) > 0 and self.animator.frame_index >= len(frames) - 1
        return surf, done
    def update(self, player, obstacles):
        if self.dead:
            surf, done = self._get_anim_frame("dead", loop=False)
            self.image = surf
            if done:
                self.death_finished = True
            return
        self.tick_contact_timer()
        self._apply_gravity(obstacles)
        dist = self.distance_to(player.rect)
        if dist < self.DETECT_RANGE:
            self.state = self.ST_FLEE
        elif self.state == self.ST_FLEE and dist > self.LOSE_RANGE:
            self.state = self.ST_WANDER
        if self.state == self.ST_WANDER:
            tx = self._patrol_targets[self._patrol_idx]
            d = 1 if tx > self.rect.centerx else -1
            self.facing_right = (d == 1)
            self._do_wander(obstacles)
        elif self.state == self.ST_FLEE:
            d = 1 if self.rect.centerx > player.rect.centerx else -1
            self.facing_right = (d == 1)
            self._try_move(d * self.FLEE_SPEED, obstacles)
        anim_state = "idle"
        loop = True
        if self.dead:
            anim_state = "dead"
            loop = False
        elif self.state == self.ST_FLEE:
            anim_state = "flee"
        elif self.state == self.ST_WANDER:
            anim_state = "wander"
        self.image, _ = self._get_anim_frame(anim_state, loop=loop)
    def on_death(self):
        self.animator.current_state = "dead"
        self.animator.frame_index = 0
