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
class GolemPierre(BaseEnemy):
    PATROL_SPEED   = 0
    PATROL_RADIUS  = 0
    SPEED          = 1
    DETECT_RANGE   = 900
    LOSE_RANGE     = 1350
    STOMP_RANGE    = 90
    QUAKE_RANGE    = 350
    STOMP_DAMAGE   = 25
    QUAKE_DAMAGE   = 15
    QUAKE_SLOW_DUR = 120
    QUAKE_SLOW_FAC = 0.4
    ATTACK_CD      = 90
    REINFORCE_DUR  = 60
    ST_SLEEP     = "sleep"
    ST_RETURN    = "return"
    ST_CHASE     = "chase"
    ST_REINFORCE = "reinforce"
    ST_STOMP     = "stomp"
    ST_QUAKE     = "quake"
    def __init__(self, pos, groups, screen_shake_ref=None):
        super().__init__(pos, hp=200, groups=groups, capacite_absorbable="stone_armor")
        self.CONTACT_COOLDOWN = 120
        self.screen_shake_ref = screen_shake_ref
        w, h = 56, 72
        self._img_sleep  = self._build_img(w, h, active=False)
        self._img_active = self._build_img(w, h, active=True)
        self._img_blink0 = self._build_img(w, h, active=True)
        self._img_blink1 = self._build_img(w, h, active=False)
        self.image = self._img_sleep
        self.rect  = self.image.get_rect(topleft=pos)
        self.state           = self.ST_SLEEP
        self.facing_right    = True
        self.attack_timer    = 0
        self.reinforce_timer = 0
        self._pending_attack = self.ST_STOMP
        self.vy              = 0
    @staticmethod
    def _build_img(w, h, active=True):
        eye_col  = (220, 30, 30) if active else (50, 20, 20)
        glow_col = (255, 60, 60) if active else (40, 10, 10)
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        pygame.draw.rect(s, GRAY,        (8, 16, 40, 56))
        pygame.draw.rect(s, GRAY,        (4,  0, 48, 24))
        pygame.draw.line(s, (80, 70, 60), (14, 20), (28, 42), 2)
        pygame.draw.line(s, (80, 70, 60), (38, 14), (30, 36), 2)
        pygame.draw.rect(s, eye_col,  (10, 6, 12, 10))
        pygame.draw.rect(s, eye_col,  (34, 6, 12, 10))
        pygame.draw.circle(s, glow_col, (16, 11), 4)
        pygame.draw.circle(s, glow_col, (40, 11), 4)
        pygame.draw.rect(s, (90, 80, 70),   (0,  24, 10, 32))
        pygame.draw.rect(s, (90, 80, 70),   (46, 24, 10, 32))
        pygame.draw.rect(s, (110, 100, 90), (0,  52, 12, 14))
        pygame.draw.rect(s, (110, 100, 90), (44, 52, 12, 14))
        return s
    def update(self, player, obstacles):
        if self.dead: return
        self.tick_contact_timer()
        self._apply_gravity(obstacles)
        dist = self.distance_to(player.rect)
        if self.attack_timer > 0: self.attack_timer -= 1
        if self.reinforce_timer > 0:
            self.reinforce_timer -= 1
            self.image = self._img_blink0 if (self.reinforce_timer // 8) % 2 == 0                         else self._img_blink1
            return
        if self.state == self.ST_SLEEP:
            if dist < self.DETECT_RANGE:
                self.image = self._img_active
                self.state = self.ST_CHASE
        elif self.state == self.ST_RETURN:
            pass
        elif self.state == self.ST_CHASE:
            if dist > self.LOSE_RANGE:
                self.image = self._img_sleep
                self.state = self.ST_RETURN
            elif dist <= self.STOMP_RANGE:
                self._pending_attack = self.ST_STOMP
                self.reinforce_timer = self.REINFORCE_DUR
            elif dist <= self.QUAKE_RANGE:
                self._pending_attack = self.ST_QUAKE
                self.reinforce_timer = self.REINFORCE_DUR
        elif self.state == self.ST_REINFORCE:
            self.state = self._pending_attack
        elif self.state in (self.ST_STOMP, self.ST_QUAKE):
            self.state = self.ST_CHASE
        d = 1 if player.rect.centerx > self.rect.centerx else -1
        self.facing_right = (d == 1)
        if self.state == self.ST_CHASE:
            self._try_move(d * self.SPEED, obstacles)
        elif self.state == self.ST_RETURN:
            if self._do_return_to_spawn(obstacles):
                self.image = self._img_sleep
                self.state = self.ST_SLEEP
        elif self.state == self.ST_STOMP:
            if self.attack_timer == 0 and self.contact_timer == 0:
                player.take_damage(self.STOMP_DAMAGE)
                self.contact_timer = self.CONTACT_COOLDOWN
                self.attack_timer  = self.ATTACK_CD
                self.state         = self.ST_CHASE
        elif self.state == self.ST_QUAKE:
            if self.attack_timer == 0:
                self._do_quake(player)
                self.attack_timer = self.ATTACK_CD
                self.state        = self.ST_CHASE
    def _do_quake(self, player):
        dist = self.distance_to(player.rect)
        if dist <= self.QUAKE_RANGE:
            player.take_damage(self.QUAKE_DAMAGE)
            player.slow_timer  = self.QUAKE_SLOW_DUR
            player.slow_factor = self.QUAKE_SLOW_FAC
        if self.screen_shake_ref is not None:
            self.screen_shake_ref[0] = 20
class LaserBeam(pygame.sprite.Sprite):
    def __init__(self, pos, facing_right, groups):
        super().__init__(groups)
        self.frames = []
        path_option1 = os.path.join(CURRENT_DIR, "assets", "images", "monstre", "golem", "Laser_sheet.png")
        path_option2 = os.path.join(os.path.dirname(CURRENT_DIR), "assets", "images", "monstre", "golem", "Laser_sheet.png")
        path = path_option1 if os.path.isfile(path_option1) else path_option2
        if os.path.isfile(path):
            try:
                sheet = pygame.image.load(path).convert_alpha()
                for i in range(5):
                    rect = pygame.Rect(0, i * 300, 300, 300)
                    frame = sheet.subsurface(rect).copy()
                    frame = pygame.transform.scale(frame, (500, 100))
                    if not facing_right:
                        frame = pygame.transform.flip(frame, True, False)
                    self.frames.append(frame)
            except Exception as e:
                print(f"⚠️ Erreur de chargement laser : {e}")
        if not self.frames:
            s = pygame.Surface((500, 100), pygame.SRCALPHA)
            pygame.draw.rect(s, (255, 60, 60, 200), (0, 35, 500, 30))
            self.frames = [s]
        self.frame_index = 0
        self.image = self.frames[0]
        self.facing_right = facing_right
        if facing_right:
            self.rect = self.image.get_rect(midleft=pos)
        else:
            self.rect = self.image.get_rect(midright=pos)
        self.duration = 45 
        self.damage = 20 
    def update(self, obstacles):
        self.duration -= 1
        if self.duration <= 0:
            self.kill()
            return
        self.frame_index = (self.frame_index + 0.15) % len(self.frames)
        self.image = self.frames[int(self.frame_index)]
class MechaGolemArm(pygame.sprite.Sprite):
    SPEED = 8
    def __init__(self, pos, direction, groups):
        super().__init__(groups)
        path_option1 = os.path.join(CURRENT_DIR, "assets", "images", "monstre", "golem", "arm_projectile_glowing.png")
        path_option2 = os.path.join(os.path.dirname(CURRENT_DIR), "assets", "images", "monstre", "golem", "arm_projectile_glowing.png")
        path = path_option1 if os.path.isfile(path_option1) else path_option2
        if os.path.isfile(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                img = pygame.transform.scale(img, (40, 40))
                if direction == -1:
                    img = pygame.transform.flip(img, True, False)
                self.image = img
            except Exception:
                self.image = self._create_placeholder(direction)
        else:
            self.image = self._create_placeholder(direction)
        self.rect      = self.image.get_rect(center=pos)
        self.direction = direction
        self.damage    = 15
        self.lifetime  = 120
    def _create_placeholder(self, direction):
        s = pygame.Surface((30, 20), pygame.SRCALPHA)
        pygame.draw.rect(s, (200, 100, 0), (0, 5, 25, 10))
        if direction == -1:
            s = pygame.transform.flip(s, True, False)
        return s
    def update(self, obstacles):
        self.rect.x += self.SPEED * self.direction
        if pygame.sprite.spritecollide(self, obstacles, False): self.kill()
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()
class MechaGolem(BaseEnemy):
    PATROL_SPEED   = 1
    PATROL_RADIUS  = 80
    SPEED          = 2
    DETECT_RANGE   = 800
    LOSE_RANGE     = 1200
    ATTACK_RANGE   = 75
    THROW_RANGE    = 320
    LASER_RANGE    = 500
    ATTACK_DAMAGE  = 25
    ATTACK_CD      = 100
    STUN_DURATION  = 25
    ST_WANDER      = "wander"
    ST_RETURN      = "return"
    ST_CHASE       = "chase"
    ST_ATTACK      = "attack"
    ST_THROW       = "throw"
    ST_LASER       = "laser"
    ST_STUN        = "stun"
    def __init__(self, pos, groups, arrow_groups):
        super().__init__(pos, hp=180, groups=groups, capacite_absorbable="stone_armor")
        self.CONTACT_COOLDOWN = 100
        self.animations = self._load_animations()
        self.animator = Animator(self.animations, fps=8)
        if "idle" in self.animations and self.animations["idle"]:
            self.image = self.animations["idle"][0]
        else:
            self.image = pygame.Surface((160, 160))
            self.image.fill((120, 120, 120))
        self.rect  = self.image.get_rect(topleft=pos)
        self.state          = self.ST_WANDER
        self.facing_right   = True
        self.attack_timer   = 0
        self.throw_cooldown = 0
        self.laser_cooldown = 0
        self.throw_timer    = 0
        self.laser_timer    = 0
        self.laser_charged  = False
        self.stun_timer     = 0
        self.vy             = 0
        self.arrow_groups   = arrow_groups
        self.arrows         = pygame.sprite.Group()
    def _load_animations(self):
        animations = {}
        TARGET_SIZE = (160, 160)
        path_option1 = os.path.join(CURRENT_DIR, "assets", "images", "monstre", "golem", "Character_sheet.png")
        path_option2 = os.path.join(os.path.dirname(CURRENT_DIR), "assets", "images", "monstre", "golem", "Character_sheet.png")
        path = path_option1 if os.path.isfile(path_option1) else path_option2
        file_mapping = {
            "idle":         (0, 4),
            "wander":       (1, 8),
            "return":       (1, 8),
            "chase":        (1, 8),
            "attack":       (2, 9),
            "laser_charge": (3, 8),
            "hurt":         (4, 7),
            "dead":         (5, 7),
            "block":        (6, 10),
            "throw":        (7, 10),
            "spawn":        (8, 4)
        }
        if os.path.isfile(path):
            try:
                sheet = pygame.image.load(path).convert_alpha()
                cell_w, cell_h = 100, 100
                for state, (row, count) in file_mapping.items():
                    frames = []
                    for col in range(count):
                        rect = pygame.Rect(col * cell_w, row * cell_h, cell_w, cell_h)
                        frame = sheet.subsurface(rect).copy()
                        frame = pygame.transform.scale(frame, TARGET_SIZE)
                        frames.append(frame)
                    animations[state] = frames
            except Exception as e:
                print(f"⚠️ Erreur de découpage de la sheet Golem : {e}")
        if "idle" not in animations:
            s = pygame.Surface(TARGET_SIZE, pygame.SRCALPHA)
            pygame.draw.rect(s, (100, 100, 100), (20, 20, 120, 120))
            animations["idle"] = [s]
        return animations
    def _get_anim_frame(self, anim_state, loop=True):
        dt = 1.0 / 60.0
        if anim_state == "laser_charge":
            self.animator.animation_speed = 1.0 / 12
        elif anim_state == "throw":
            self.animator.animation_speed = 1.0 / 10
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
        if self.throw_cooldown > 0: self.throw_cooldown -= 1
        if self.laser_cooldown > 0: self.laser_cooldown -= 1
        if self.stun_timer > 0:
            self.stun_timer -= 1
            self.state = self.ST_STUN
            return
        if self.state in (self.ST_WANDER, self.ST_RETURN):
            if dist < self.DETECT_RANGE:
                self.state = self.ST_CHASE
                if getattr(self, 'sound_manager', None):
                    self.sound_manager.play("gobelin_detect")
        elif self.state == self.ST_CHASE:
            if dist <= self.ATTACK_RANGE and self.attack_timer == 0:
                self.state = self.ST_ATTACK
                self.animator.current_state = "attack"
                self.animator.frame_index = 0
            elif dist <= self.LASER_RANGE and self.laser_cooldown == 0 and self.attack_timer == 0:
                self.state = self.ST_LASER
                self.laser_timer = 90
                self.laser_charged = False
                self.animator.current_state = "laser_charge"
                self.animator.frame_index = 0
            elif dist <= self.THROW_RANGE and self.throw_cooldown == 0 and self.attack_timer == 0:
                self.state = self.ST_THROW
                self.throw_timer = 45
                self.animator.current_state = "throw"
                self.animator.frame_index = 0
            elif dist > self.LOSE_RANGE:
                self.state = self.ST_RETURN
        elif self.state == self.ST_ATTACK:
            pass
        elif self.state == self.ST_THROW:
            self.throw_timer -= 1
            if self.throw_timer == 25:
                d = 1 if player.rect.centerx > self.rect.centerx else -1
                MechaGolemArm(self.rect.center, d, [self.arrows] + list(self.arrow_groups))
                if getattr(self, 'sound_manager', None):
                    self.sound_manager.play("gobelin_archer_attack")
            if self.throw_timer <= 0:
                self.throw_cooldown = 120
                self.state = self.ST_CHASE
        elif self.state == self.ST_LASER:
            self.laser_timer -= 1
            if self.laser_timer == 45 and not self.laser_charged:
                self.laser_charged = True
                d = 1 if player.rect.centerx > self.rect.centerx else -1
                LaserBeam(self.rect.center, d == 1, [self.arrows] + list(self.arrow_groups))
                if getattr(self, 'sound_manager', None):
                    self.sound_manager.play("spirit_detect")
            if self.laser_timer <= 0:
                self.laser_cooldown = 200
                self.state = self.ST_CHASE
        d = 1 if player.rect.centerx > self.rect.centerx else -1
        if self.state not in (self.ST_LASER, self.ST_THROW):
            self.facing_right = (d == 1)
        if self.state == self.ST_WANDER:
            tx = self._patrol_targets[self._patrol_idx]
            d_patrol = 1 if tx > self.rect.centerx else -1
            self.facing_right = (d_patrol == 1)
            self._do_wander(obstacles)
        elif self.state == self.ST_RETURN:
            tx = self.spawn_pos[0]
            d_return = 1 if tx > self.rect.centerx else -1
            self.facing_right = (d_return == 1)
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
            if self.animator.current_state == "attack" and self.animator.frame_index >= len(self.animator.animations.get("attack", [])) - 1:
                self.state = self.ST_CHASE
        anim_state = "idle"
        loop = True
        if self.dead:
            anim_state = "dead"
            loop = False
        elif self.stun_timer > 0:
            anim_state = "hurt"
            loop = False
        elif self.state == self.ST_ATTACK:
            anim_state = "attack"
            loop = False
        elif self.state == self.ST_THROW:
            anim_state = "throw"
            loop = False
        elif self.state == self.ST_LASER:
            anim_state = "laser_charge"
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
