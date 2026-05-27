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
class GoblinMelee(BaseEnemy):
    PATROL_SPEED  = 1
    PATROL_RADIUS = 80
    SPEED         = 3
    DETECT_RANGE  = 720
    LOSE_RANGE    = 1050
    ATTACK_RANGE  = 38
    ATTACK_DAMAGE = 12
    ATTACK_CD     = 70
    STUN_DURATION = 20
    ST_WANDER = "wander"
    ST_RETURN = "return"
    ST_CHASE  = "chase"
    ST_ATTACK = "attack"
    ST_STUN   = "stun"
    def __init__(self, pos, groups):
        super().__init__(pos, hp=40, groups=groups, capacite_absorbable="slash")
        self.CONTACT_COOLDOWN = 70
        self.animations = self._load_animations()
        self.animator = Animator(self.animations, fps=8)
        if "idle" in self.animations and self.animations["idle"]:
            self.image = self.animations["idle"][0]
        else:
            self.image = pygame.Surface((160, 160))
            self.image.fill((0, 200, 0))
        self.rect  = self.image.get_rect(topleft=pos)
        self.state        = self.ST_WANDER
        self.facing_right = True
        self.attack_timer = 0
        self.stun_timer   = 0
        self.vy           = 0
    def _load_animations(self):
        animations = {}
        TARGET_SIZE = (100, 100)
        path_option1 = os.path.join(CURRENT_DIR, "assets", "images", "monstre", "goblin_melee")
        path_option2 = os.path.join(os.path.dirname(CURRENT_DIR), "assets", "images", "monstre", "goblin_melee")
        sheet_dir = path_option1 if os.path.isdir(path_option1) else path_option2
        file_mapping = {
            "idle":   "Idle.png",
            "wander": "Walk.png",
            "return": "Walk.png",
            "chase":  "Run.png",
            "attack": "Attack_1.png",
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
                pygame.draw.ellipse(s, GREEN_DARK, (16, 16, 32, 48))
                animations["idle"] = [s]
        return animations
    def _get_anim_frame(self, anim_state, loop=True):
        dt = 1.0 / 60.0  
        if anim_state == "chase":
            self.animator.animation_speed = 1.0 / 12
        elif anim_state == "attack":
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
        if self.stun_timer > 0:
            self.stun_timer -= 1; self.state = self.ST_STUN; return
        if self.state in (self.ST_WANDER, self.ST_RETURN):
            if dist < self.DETECT_RANGE: 
                self.state = self.ST_CHASE
                if getattr(self, 'sound_manager', None):
                    self.sound_manager.play("gobelin_detect")
        elif self.state == self.ST_CHASE:
            if dist <= self.ATTACK_RANGE: self.state = self.ST_ATTACK
            elif dist > self.LOSE_RANGE:  self.state = self.ST_RETURN
        elif self.state == self.ST_ATTACK:
            if dist > self.LOSE_RANGE:
                self.state = self.ST_RETURN
            elif self.attack_timer == 0 and dist > self.ATTACK_RANGE:
                self.state = self.ST_CHASE
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
            d = 1 if player.rect.centerx > self.rect.centerx else -1
            self.facing_right = (d == 1)
            self._try_move(d * self.SPEED, obstacles)
        elif self.state == self.ST_ATTACK:
            d = 1 if player.rect.centerx > self.rect.centerx else -1
            self.facing_right = (d == 1)
            if self.attack_timer > 0:
                self._try_move(-d * self.SPEED * 1.2, obstacles)
            else:
                if self.attack_timer == 0 and self.contact_timer == 0:
                    player.take_damage(self.ATTACK_DAMAGE)
                    self.attack_timer  = self.ATTACK_CD
                    self.contact_timer = self.CONTACT_COOLDOWN
                    if getattr(self, 'sound_manager', None):
                        self.sound_manager.play("gobelin_attack")
        anim_state = "idle"
        loop = True
        if self.dead:
            anim_state = "dead"
            loop = False
        elif self.stun_timer > 0:
            anim_state = "hurt"
            loop = False
        elif self.state == self.ST_ATTACK:
            if self.attack_timer > 0:
                anim_state = "wander"  
            else:
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
class Arrow(pygame.sprite.Sprite):
    SPEED = 10
    def __init__(self, pos, direction, groups):
        super().__init__(groups)
        path_option1 = os.path.join(CURRENT_DIR, "assets", "images", "monstre", "goblin_archer", "Arrow.png")
        path_option2 = os.path.join(os.path.dirname(CURRENT_DIR), "assets", "images", "monstre", "goblin_archer", "Arrow.png")
        path = path_option1 if os.path.isfile(path_option1) else path_option2
        if os.path.isfile(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                img = pygame.transform.scale(img, (32, 32))
                if direction == -1:
                    img = pygame.transform.flip(img, True, False)
                self.image = img
            except Exception:
                self.image = self._create_placeholder(direction)
        else:
            self.image = self._create_placeholder(direction)
        self.rect      = self.image.get_rect(center=pos)
        self.direction = direction
        self.damage    = 10
        self.lifetime  = 180
    def _create_placeholder(self, direction):
        s = pygame.Surface((18, 6), pygame.SRCALPHA)
        pygame.draw.rect(s, BROWN, (0, 2, 14, 2))
        pygame.draw.polygon(s, (200, 200, 220), [(14, 0), (18, 3), (14, 6)])
        pygame.draw.polygon(s, WHITE,           [(0, 0), (4, 3), (0, 6)])
        if direction == -1:
            s = pygame.transform.flip(s, True, False)
        return s
    def update(self, obstacles):
        self.rect.x += self.SPEED * self.direction
        if pygame.sprite.spritecollide(self, obstacles, False): self.kill()
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()
class GoblinArcher(BaseEnemy):
    PATROL_SPEED   = 1
    PATROL_RADIUS  = 80
    PREFERRED_DIST = 250
    RETREAT_DIST   = 180
    DETECT_RANGE   = 900
    LOSE_RANGE     = 1250
    SHOOT_CD       = 120
    SPEED          = 2
    ST_WANDER   = "wander"
    ST_RETURN   = "return"
    ST_POSITION = "position"
    ST_SHOOT    = "shoot"
    ST_RETREAT  = "retreat"
    def __init__(self, pos, groups, arrow_groups):
        super().__init__(pos, hp=30, groups=groups, capacite_absorbable="arrow")
        self.CONTACT_COOLDOWN = 100
        self.animations = self._load_animations()
        self.animator = Animator(self.animations, fps=8)
        if "idle" in self.animations and self.animations["idle"]:
            self.image = self.animations["idle"][0]
        else:
            self.image = pygame.Surface((160, 160))
            self.image.fill((0, 255, 0))
        self.rect  = self.image.get_rect(topleft=pos)
        self.state        = self.ST_WANDER
        self.facing_right = True
        self.shoot_timer  = 0
        self.vy           = 0
        self.arrow_groups = arrow_groups
        self.arrows       = pygame.sprite.Group()
    def _load_animations(self):
        animations = {}
        TARGET_SIZE = (100, 100)
        path_option1 = os.path.join(CURRENT_DIR, "assets", "images", "monstre", "goblin_archer")
        path_option2 = os.path.join(os.path.dirname(CURRENT_DIR), "assets", "images", "monstre", "goblin_archer")
        sheet_dir = path_option1 if os.path.isdir(path_option1) else path_option2
        file_mapping = {
            "idle":     "Idle.png",
            "wander":   "Walk.png",
            "return":   "Walk.png",
            "position": "Walk.png",
            "retreat":  "Walk.png",
            "shoot":    "Shot_1.png",
            "dead":     "Dead.png"
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
                pygame.draw.ellipse(s, GREEN_DARK, (16, 16, 32, 48))
                animations["idle"] = [s]
        return animations
    def _get_anim_frame(self, anim_state, loop=True):
        dt = 1.0 / 60.0  
        if anim_state == "shoot":
            self.animator.animation_speed = 1.0 / 15
        elif anim_state in ("wander", "position", "retreat"):
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
        if self.shoot_timer > 0: self.shoot_timer -= 1
        if self.state in (self.ST_WANDER, self.ST_RETURN):
            if dist < self.DETECT_RANGE: 
                self.state = self.ST_POSITION
                if getattr(self, 'sound_manager', None):
                    self.sound_manager.play("gobelin_detect")
        elif self.state in (self.ST_POSITION, self.ST_SHOOT, self.ST_RETREAT):
            if dist > self.LOSE_RANGE:
                self.state = self.ST_RETURN
            elif dist < self.RETREAT_DIST:
                self.state = self.ST_RETREAT
            else:
                self.state = self.ST_SHOOT
        d = 1 if player.rect.centerx > self.rect.centerx else -1
        self.facing_right = (d == 1)
        is_moving = False
        if self.state == self.ST_WANDER:
            self._do_wander(obstacles)
            is_moving = True
        elif self.state == self.ST_RETURN:
            if self._do_return_to_spawn(obstacles): self.state = self.ST_WANDER
            is_moving = True
        elif self.state in (self.ST_POSITION, self.ST_SHOOT):
            if dist > self.PREFERRED_DIST + 40:
                self._try_move(d * self.SPEED, obstacles)
                is_moving = True
            elif dist < self.PREFERRED_DIST - 40:
                self._try_move(-d * self.SPEED, obstacles)
                is_moving = True
            if self.shoot_timer == 0:
                Arrow(self.rect.center, d, [self.arrows] + list(self.arrow_groups))
                self.shoot_timer = self.SHOOT_CD
                if getattr(self, 'sound_manager', None):
                    self.sound_manager.play("gobelin_archer_attack")
                self.animator.current_state = "shoot"
                self.animator.frame_index = 0
        elif self.state == self.ST_RETREAT:
            self._try_move(-d * self.SPEED * 2, obstacles)
            is_moving = True
            if self.shoot_timer == 0:
                Arrow(self.rect.center, d, [self.arrows] + list(self.arrow_groups))
                self.shoot_timer = self.SHOOT_CD
                if getattr(self, 'sound_manager', None):
                    self.sound_manager.play("gobelin_archer_attack")
                self.animator.current_state = "shoot"
                self.animator.frame_index = 0
        if dist < 40 and self.contact_timer == 0:
            player.take_damage(8)
            self.contact_timer = self.CONTACT_COOLDOWN
        pass
        anim_state = "idle"
        loop = True
        if self.dead:
            anim_state = "dead"
            loop = False
        elif self.animator.current_state == "shoot" and self.animator.frame_index < len(self.animator.animations.get("shoot", [])) - 1:
            anim_state = "shoot"
            loop = False
        elif is_moving:
            anim_state = "wander"
        else:
            anim_state = "idle"
        self.image, _ = self._get_anim_frame(anim_state, loop=loop)
    def on_death(self):
        self.animator.current_state = "dead"
        self.animator.frame_index = 0
        if getattr(self, 'sound_manager', None):
            self.sound_manager.play("gobelin_death")
class GoblinLancier(BaseEnemy):
    PATROL_SPEED  = 1
    PATROL_RADIUS = 80
    SPEED         = 3
    LUNGE_SPEED   = 7.5
    DETECT_RANGE  = 720
    LOSE_RANGE    = 1050
    ATTACK_RANGE  = 60
    ATTACK_DAMAGE = 14
    LUNGE_DAMAGE  = 20
    ATTACK_CD     = 75
    LUNGE_CD      = 150
    STUN_DURATION = 20
    ST_WANDER = "wander"
    ST_RETURN = "return"
    ST_CHASE  = "chase"
    ST_ATTACK = "attack"
    ST_LUNGE  = "lunge"
    ST_STUN   = "stun"
    def __init__(self, pos, groups):
        super().__init__(pos, hp=50, groups=groups, capacite_absorbable="slash")
        self.CONTACT_COOLDOWN = 75
        self.animations = self._load_animations()
        self.animator = Animator(self.animations, fps=8)
        if "idle" in self.animations and self.animations["idle"]:
            self.image = self.animations["idle"][0]
        else:
            self.image = pygame.Surface((160, 160))
            self.image.fill((0, 160, 200))
        self.rect  = self.image.get_rect(topleft=pos)
        self.state          = self.ST_WANDER
        self.facing_right   = True
        self.attack_timer   = 0
        self.lunge_cooldown = 0
        self.lunge_timer    = 0
        self.lunge_vx       = 0
        self.stun_timer     = 0
        self.vy             = 0
    def _load_animations(self):
        animations = {}
        TARGET_SIZE = (100, 100)
        path_option1 = os.path.join(CURRENT_DIR, "assets", "images", "monstre", "goblin_lancier")
        path_option2 = os.path.join(os.path.dirname(CURRENT_DIR), "assets", "images", "monstre", "goblin_lancier")
        sheet_dir = path_option1 if os.path.isdir(path_option1) else path_option2
        file_mapping = {
            "idle":   "Idle.png",
            "wander": "Walk.png",
            "return": "Walk.png",
            "chase":  "Run.png",
            "attack": "Attack_1.png",
            "lunge":  "Run+attack.png",
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
                pygame.draw.ellipse(s, GREEN_DARK, (24, 24, 48, 48))
                animations["idle"] = [s]
        return animations
    def _get_anim_frame(self, anim_state, loop=True):
        dt = 1.0 / 60.0  
        if anim_state == "lunge":
            self.animator.animation_speed = 1.0 / 12
        elif anim_state == "chase":
            self.animator.animation_speed = 1.0 / 10
        elif anim_state == "attack":
            self.animator.animation_speed = 1.0 / 8
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
        if self.lunge_cooldown > 0: self.lunge_cooldown -= 1
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
            elif 100 < dist < 220 and self.lunge_cooldown == 0 and self.attack_timer == 0:
                self.state = self.ST_LUNGE
                self.lunge_timer = 30
                self.lunge_vx = self.LUNGE_SPEED * (1 if player.rect.centerx > self.rect.centerx else -1)
                self.facing_right = (self.lunge_vx > 0)
                self.animator.current_state = "lunge"
                self.animator.frame_index = 0
            elif dist > self.LOSE_RANGE:
                self.state = self.ST_RETURN
        elif self.state == self.ST_ATTACK:
            if dist > self.ATTACK_RANGE + 20:
                self.state = self.ST_CHASE
        elif self.state == self.ST_LUNGE:
            self.lunge_timer -= 1
            if self.lunge_timer <= 0:
                self.lunge_cooldown = self.LUNGE_CD
                self.state = self.ST_CHASE
            else:
                self._try_move(self.lunge_vx, obstacles)
                if self.rect.colliderect(player.rect) and self.contact_timer == 0:
                    player.take_damage(self.LUNGE_DAMAGE)
                    self.contact_timer = self.CONTACT_COOLDOWN
                    self.lunge_vx = 0
                    self.lunge_timer = 0
                    self.lunge_cooldown = self.LUNGE_CD
                    self.state = self.ST_CHASE
        d = 1 if player.rect.centerx > self.rect.centerx else -1
        if self.state != self.ST_LUNGE:
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
        elif self.animator.current_state == "lunge" and self.animator.frame_index < len(self.animator.animations.get("lunge", [])) - 1:
            anim_state = "lunge"
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
