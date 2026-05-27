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
class Gorgon(BaseEnemy):
    PATROL_SPEED     = 1
    PATROL_RADIUS    = 80
    SPEED            = 2
    DETECT_RANGE     = 670
    LOSE_RANGE       = 1050
    ATTACK_RANGE     = 48
    ATTACK_DAMAGE    = 18
    ATTACK_CD        = 80
    SPECIAL_RANGE    = 350
    SPECIAL_CD       = 180
    STUN_DURATION    = 25
    ST_WANDER  = "wander"
    ST_RETURN  = "return"
    ST_CHASE   = "chase"
    ST_ATTACK  = "attack"
    ST_SPECIAL = "special"
    ST_STUN    = "stun"
    def __init__(self, pos, groups):
        super().__init__(pos, hp=60, groups=groups, capacite_absorbable="ice_shot")
        self.CONTACT_COOLDOWN = 80
        self.animations = self._load_animations()
        self.animator = Animator(self.animations, fps=8)
        if "idle" in self.animations and self.animations["idle"]:
            self.image = self.animations["idle"][0]
        else:
            self.image = pygame.Surface((128, 128))
            self.image.fill((100, 200, 100))
        self.rect  = self.image.get_rect(topleft=pos)
        self.state            = self.ST_WANDER
        self.facing_right     = True
        self.attack_timer     = 0
        self.special_cooldown = 0
        self.special_timer    = 0
        self.stun_timer       = 0
        self.vy               = 0
    def _load_animations(self):
        animations = {}
        TARGET_SIZE = (128, 128)
        path_option1 = os.path.join(CURRENT_DIR, "assets", "images", "monstre", "Gorgon", "Gorgon_1")
        path_option2 = os.path.join(os.path.dirname(CURRENT_DIR), "assets", "images", "monstre", "Gorgon", "Gorgon_1")
        sheet_dir = path_option1 if os.path.isdir(path_option1) else path_option2
        file_mapping = {
            "idle":   "Idle.png",
            "wander": "Walk.png",
            "return": "Walk.png",
            "chase":  "Run.png",
            "attack": "Attack_1.png",
            "special": "Special.png",
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
        if "idle" not in animations:
            if "wander" in animations:
                animations["idle"] = animations["wander"]
            else:
                s = pygame.Surface(TARGET_SIZE, pygame.SRCALPHA)
                pygame.draw.ellipse(s, (100, 200, 100), (24, 24, 48, 48))
                animations["idle"] = [s]
        return animations
    def _get_anim_frame(self, anim_state, loop=True):
        dt = 1.0 / 60.0  
        if anim_state == "special":
            self.animator.animation_speed = 1.0 / 10
        elif anim_state == "attack":
            self.animator.animation_speed = 1.0 / 12
        elif anim_state == "chase":
            self.animator.animation_speed = 1.0 / 10
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
        if self.attack_timer > 0: self.attack_timer -= 1
        if self.special_cooldown > 0: self.special_cooldown -= 1
        if self.stun_timer > 0:
            self.stun_timer -= 1; self.state = self.ST_STUN; return
        if self.state in (self.ST_WANDER, self.ST_RETURN):
            if dist < self.DETECT_RANGE: 
                self.state = self.ST_CHASE
                if getattr(self, 'sound_manager', None):
                    self.sound_manager.play("gobelin_detect")
        elif self.state == self.ST_CHASE:
            if dist <= self.ATTACK_RANGE:
                self.state = self.ST_ATTACK
            elif dist <= self.SPECIAL_RANGE and self.special_cooldown == 0 and self.attack_timer == 0:
                is_facing_player = (player.rect.centerx > self.rect.centerx and self.facing_right) or                                   (player.rect.centerx < self.rect.centerx and not self.facing_right)
                if is_facing_player:
                    self.state = self.ST_SPECIAL
                    self.special_timer = 45
                    if hasattr(player, 'slow_timer'):
                        player.slow_timer = 120
                        player.slow_factor = 0.15
                        if getattr(self, 'sound_manager', None):
                            self.sound_manager.play("spirit_detect")
                    self.animator.current_state = "special"
                    self.animator.frame_index = 0
            elif dist > self.LOSE_RANGE:
                self.state = self.ST_RETURN
        elif self.state == self.ST_ATTACK:
            if dist > self.ATTACK_RANGE + 20:
                self.state = self.ST_CHASE
        elif self.state == self.ST_SPECIAL:
            self.special_timer -= 1
            if self.special_timer <= 0:
                self.special_cooldown = self.SPECIAL_CD
                self.state = self.ST_CHASE
        d = 1 if player.rect.centerx > self.rect.centerx else -1
        if self.state != self.ST_SPECIAL:
            self.facing_right = (d == 1)
        if self.state == self.ST_WANDER:
            tx = self._patrol_targets[self._patrol_idx]
            d = 1 if tx > self.rect.centerx else -1
            self.facing_right = (d == 1)
            self._do_wander(obstacles)
        elif self.state == self.ST_RETURN:
            tx = self.spawn_pos[0]
            d = 1 if tx > self.rect.centerx else -1
            self.facing_right = (d == 1)
            if self._do_return_to_spawn(obstacles): self.state = self.ST_WANDER
        elif self.state == self.ST_CHASE:
            self._try_move(d * self.SPEED, obstacles)
        elif self.state == self.ST_ATTACK:
            if self.attack_timer == 0 and self.contact_timer == 0:
                player.take_damage(self.ATTACK_DAMAGE)
                self.attack_timer  = self.ATTACK_CD
                self.contact_timer = self.CONTACT_COOLDOWN
                if getattr(self, 'sound_manager', None):
                    self.sound_manager.play("gobelin_attack")
                self.animator.current_state = "attack"
                self.animator.frame_index = 0
        anim_state = "idle"
        loop = True
        if self.dead:
            anim_state = "dead"
            loop = False
        elif self.stun_timer > 0:
            anim_state = "hurt"
            loop = False
        elif self.animator.current_state == "special" and self.animator.frame_index < len(self.animator.animations.get("special", [])) - 1:
            anim_state = "special"
            loop = False
        elif self.animator.current_state == "attack" and self.animator.frame_index < len(self.animator.animations.get("attack", [])) - 1:
            anim_state = "attack"
            loop = False
        elif self.state == self.ST_CHASE:
            anim_state = "chase"
        elif self.state in (self.ST_WANDER, self.ST_RETURN):
            anim_state = "wander"
        self.image, _ = self._get_anim_frame(anim_state, loop=loop)
    def take_damage(self, amount):
        super().take_damage(amount)
        if not self.dead:
            self.stun_timer = self.STUN_DURATION
            self.state      = self.ST_STUN
    def on_death(self):
        self.animator.current_state = "dead"
        self.animator.frame_index = 0
        if getattr(self, 'sound_manager', None):
            self.sound_manager.play("gobelin_death")
