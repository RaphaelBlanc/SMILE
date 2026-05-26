import pygame
import math
import random
import os
from animator import Animator

# Calcule automatiquement le dossier dans lequel se trouve ce fichier
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# ================================================================
#  MONSTRE.PY  —  Ennemis avec machine à états — SMILE
# ================================================================

# ────────────────────────────────────────────
#  COULEURS
# ────────────────────────────────────────────
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

# ================================================================
#  UTILITAIRE
# ================================================================

def _make_surf(w, h, draw_fn, *args):
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    draw_fn(surf, *args)
    return surf

# ================================================================
#  CLASSE DE BASE
# ================================================================

class BaseEnemy(pygame.sprite.Sprite):

    DETECT_RANGE  = 400
    LOSE_RANGE    = 600
    PATROL_SPEED  = 1
    PATROL_RADIUS = 100

    def __init__(self, pos, hp, groups, capacite_absorbable=None):
        super().__init__(groups)

        self.spawn_pos  = (int(pos[0]), int(pos[1]))
        self.hp_max     = hp
        self.hp_current = hp
        self.dead       = False
        self.capacite_absorbable = capacite_absorbable

        self.contact_timer    = 0
        self.CONTACT_COOLDOWN = 90

        self._patrol_targets = [
            self.spawn_pos[0] - self.PATROL_RADIUS,
            self.spawn_pos[0] + self.PATROL_RADIUS,
        ]
        self._patrol_idx = 0

        self.image = pygame.Surface((32, 32))
        self.image.fill((200, 0, 200))
        self.rect  = self.image.get_rect(topleft=pos)

        self._sprites    = {}
        self._anim_timer = 0.0
        self._anim_index = 0
        self._anim_speed = 0.12

    def take_damage(self, amount):
        self.hp_current -= amount
        if self.hp_current <= 0:
            self.hp_current = 0
            self.dead = True
            self.on_death()

    def on_death(self):
        pass # Let main.py handle the actual kill() so it can process death logic

    def tick_contact_timer(self):
        if self.contact_timer > 0:
            self.contact_timer -= 1

    def _do_return_to_spawn(self, obstacles):
        tx = self.spawn_pos[0]
        if abs(self.rect.centerx - tx) < 8:
            return True
        d = 1 if tx > self.rect.centerx else -1
        self._try_move(d * self.PATROL_SPEED, obstacles)
        return False

    def _do_wander(self, obstacles):
        if self.PATROL_SPEED == 0:
            return
        tx = self._patrol_targets[self._patrol_idx]
        if abs(self.rect.centerx - tx) < 8:
            self._patrol_idx = (self._patrol_idx + 1) % 2
        d = 1 if tx > self.rect.centerx else -1
        self._try_move(d * self.PATROL_SPEED, obstacles)

    def draw_health_bar(self, surface):
        if self.dead:
            return
        bw, bh = self.rect.width, 6
        x, y   = self.rect.left, self.rect.top - 12
        ratio  = max(0.0, self.hp_current / self.hp_max)
        pygame.draw.rect(surface, DARK_RED,    (x, y, bw, bh))
        pygame.draw.rect(surface, (0, 220, 0), (x, y, int(bw * ratio), bh))
        pygame.draw.rect(surface, BLACK,       (x, y, bw, bh), 1)

    def distance_to(self, other_rect):
        a = pygame.math.Vector2(self.rect.center)
        b = pygame.math.Vector2(other_rect.center)
        return a.distance_to(b)

    def _try_move(self, dx, obstacles):
        self.rect.x += int(dx)
        for hit in pygame.sprite.spritecollide(self, obstacles, False):
            if dx > 0: self.rect.right = hit.rect.left
            else:      self.rect.left  = hit.rect.right

    def _apply_gravity(self, obstacles):
        self.vy += 0.8
        if self.vy > 18: self.vy = 18
        self.rect.y += int(self.vy)
        for hit in pygame.sprite.spritecollide(self, obstacles, False):
            if self.vy > 0:
                self.rect.bottom = hit.rect.top
                self.vy = 0


# ================================================================
#  1. CHIEN ENRAGÉ (Utilise Animator)
# ================================================================

class ChienEnrage(BaseEnemy):

    PATROL_SPEED  = 2
    PATROL_RADIUS = 120
    CHASE_SPEED   = 3
    SLIDE_SPEED   = 7
    SLIDE_DECAY   = 0.15
    TURN_DELAY    = 45
    DETECT_RANGE  = 500
    LOSE_RANGE    = 750
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

        # Chargement et préparation des animations
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
        self.charge_timer = 0  # NOUVEAU : Temps d'attente entre deux charges
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
        if self.dead: return
        self.tick_contact_timer()
        self._apply_gravity(obstacles)
        
        dist = self.distance_to(player.rect)

        # Gestion des chronos
        if self.attack_timer > 0: self.attack_timer -= 1
        if self.charge_timer > 0: self.charge_timer -= 1

        # 1. DÉTECTION DU JOUEUR
        if self.state in (self.ST_WANDER, self.ST_RETURN):
            if dist < self.DETECT_RANGE:
                self.state = self.ST_CHASE
                if getattr(self, 'sound_manager', None):
                    self.sound_manager.play("chien_detect")

        # 2. LOGIQUE DE POURSUITE ET DÉCLENCHEMENT D'ATTAQUE
        elif self.state == self.ST_CHASE:
            
            # Cas A : Le joueur saute par dessus -> Le loup charge (slide)
            if self._player_jumping_over(player):
                d = 1 if player.rect.centerx > self.rect.centerx else -1
                self._enter_slide(d)
                
            # Cas B : Le joueur est à moyenne distance -> Le loup a une chance de charger
            elif 150 < dist < 400 and self.charge_timer <= 0:
                d = 1 if player.rect.centerx > self.rect.centerx else -1
                self._enter_slide(d)
                self.charge_timer = 180 # Il attend 3 secondes avant de pouvoir re-charger
                
            # Cas C : Le joueur est collé -> Le loup lance la vraie attaque
            elif dist <= self.ATTACK_RANGE and self.attack_timer <= 0:
                self.state = self.ST_ATTACK
                self.animator.current_state = "attack"
                self.animator.frame_index = 0
                
            # Cas D : Le joueur est trop loin -> Retour à la niche
            elif dist > self.LOSE_RANGE:
                self.state = self.ST_RETURN

        # 3. GESTION DE LA VRAIE ATTAQUE (MORSURE)
        elif self.state == self.ST_ATTACK:
            surf, done = self._get_anim_frame("attack", loop=False)
            self.image = surf
            
            # Quand l'animation de morsure est terminée :
            if done:
                # Si le joueur est toujours à portée, il prend les dégâts
                if self.contact_timer <= 0 and dist <= self.ATTACK_RANGE + 30:
                    player.take_damage(self.ATTACK_DAMAGE)
                    self.contact_timer = self.CONTACT_COOLDOWN
                    if getattr(self, 'sound_manager', None):
                        self.sound_manager.play("chien_attack")
                self.attack_timer = self.ATTACK_CD
                self.state = self.ST_CHASE
            return # On quitte ici pour ne pas écraser l'image en dessous

        # 4. FIN DE LA CHARGE (SLIDE)
        elif self.state == self.ST_SLIDE:
            if abs(self.slide_vx) < 0.5:
                self.slide_vx = 0.0
                self.state = self.ST_CHASE if dist < self.LOSE_RANGE else self.ST_RETURN


        # --- MISE À JOUR DES POSITIONS ET DES IMAGES ---
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
            
            # S'il fonce dans le joueur pendant sa charge :
            if self.rect.colliderect(player.rect):
                self.slide_vx = 0.0 # Il s'arrête net
                
                # S'il peut attaquer, il lance la vraie attaque
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
        # Let main.py handle self.kill()

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
# ================================================================
#  2a. GOBELIN CORPS-À-CORPS
# ================================================================

class GoblinMelee(BaseEnemy):

    PATROL_SPEED  = 1
    PATROL_RADIUS = 80
    SPEED         = 3
    DETECT_RANGE  = 480
    LOSE_RANGE    = 700
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

        w, h = 28, 40
        self.image = self._build_img(w, h)
        self.rect  = self.image.get_rect(topleft=pos)

        self.state        = self.ST_WANDER
        self.facing_right = True
        self.attack_timer = 0
        self.stun_timer   = 0
        self.vy           = 0

    @staticmethod
    def _build_img(w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        pygame.draw.rect(s, GREEN_DARK,  (4, 16, 20, 24))
        pygame.draw.ellipse(s, GREEN_LIGHT, (4, 0, 20, 20))
        pygame.draw.circle(s, YELLOW, (9,  7), 3)
        pygame.draw.circle(s, YELLOW, (19, 7), 3)
        pygame.draw.circle(s, BLACK,  (10, 7), 1)
        pygame.draw.circle(s, BLACK,  (20, 7), 1)
        pygame.draw.rect(s, ORANGE, (22, 8, 6, 14))
        pygame.draw.polygon(s, (200, 100, 0), [(22, 8), (28, 4), (28, 14)])
        return s

    def update(self, player, obstacles):
        if self.dead: return
        self.tick_contact_timer()
        self._apply_gravity(obstacles)
        
        dist = self.distance_to(player.rect)

        if self.attack_timer > 0: self.attack_timer -= 1
        if self.stun_timer > 0:
            self.stun_timer -= 1; self.state = self.ST_STUN; return

        if self.state in (self.ST_WANDER, self.ST_RETURN):
            if dist < self.DETECT_RANGE: self.state = self.ST_CHASE
        elif self.state == self.ST_CHASE:
            if dist <= self.ATTACK_RANGE: self.state = self.ST_ATTACK
            elif dist > self.LOSE_RANGE:  self.state = self.ST_RETURN
        elif self.state == self.ST_ATTACK:
            if dist > self.ATTACK_RANGE + 20: self.state = self.ST_CHASE

        if self.state == self.ST_WANDER:
            self._do_wander(obstacles)
        elif self.state == self.ST_RETURN:
            if self._do_return_to_spawn(obstacles): self.state = self.ST_WANDER
        elif self.state == self.ST_CHASE:
            d = 1 if player.rect.centerx > self.rect.centerx else -1
            self.facing_right = (d == 1)
            self._try_move(d * self.SPEED, obstacles)
        elif self.state == self.ST_ATTACK:
            if self.attack_timer == 0 and self.contact_timer == 0:
                player.take_damage(self.ATTACK_DAMAGE)
                self.attack_timer  = self.ATTACK_CD
                self.contact_timer = self.CONTACT_COOLDOWN

    def take_damage(self, amount):
        super().take_damage(amount)
        if not self.dead:
            self.stun_timer = self.STUN_DURATION
            self.state      = self.ST_STUN

# ================================================================
#  2b. GOBELIN ARCHER
# ================================================================

class Arrow(pygame.sprite.Sprite):
    SPEED = 10

    def __init__(self, pos, direction, groups):
        super().__init__(groups)
        s = pygame.Surface((18, 6), pygame.SRCALPHA)
        pygame.draw.rect(s, BROWN, (0, 2, 14, 2))
        pygame.draw.polygon(s, (200, 200, 220), [(14, 0), (18, 3), (14, 6)])
        pygame.draw.polygon(s, WHITE,           [(0, 0), (4, 3), (0, 6)])
        if direction == -1:
            s = pygame.transform.flip(s, True, False)
        self.image     = s
        self.rect      = self.image.get_rect(center=pos)
        self.direction = direction
        self.damage    = 10

    def update(self, obstacles):
        self.rect.x += self.SPEED * self.direction
        if pygame.sprite.spritecollide(self, obstacles, False): self.kill()
        if self.rect.right < 0 or self.rect.left > SCREEN_WIDTH: self.kill()

class GoblinArcher(BaseEnemy):

    PATROL_SPEED   = 1
    PATROL_RADIUS  = 80
    PREFERRED_DIST = 250
    RETREAT_DIST   = 180
    DETECT_RANGE   = 600
    LOSE_RANGE     = 850
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

        w, h = 28, 40
        self.image = self._build_img(w, h)
        self.rect  = self.image.get_rect(topleft=pos)

        self.state        = self.ST_WANDER
        self.facing_right = True
        self.shoot_timer  = 0
        self.vy           = 0
        self.arrow_groups = arrow_groups
        self.arrows       = pygame.sprite.Group()

    @staticmethod
    def _build_img(w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        pygame.draw.rect(s, GREEN_DARK,    (4, 16, 20, 24))
        pygame.draw.ellipse(s, GREEN_LIGHT, (4, 0, 20, 20))
        pygame.draw.circle(s, YELLOW, (9,  7), 3)
        pygame.draw.circle(s, YELLOW, (19, 7), 3)
        pygame.draw.circle(s, BLACK,  (10, 7), 1)
        pygame.draw.circle(s, BLACK,  (20, 7), 1)
        pygame.draw.arc(s, BROWN, pygame.Rect(20, 6, 10, 22),
                        math.radians(60), math.radians(300), 2)
        pygame.draw.line(s, WHITE, (25, 8), (25, 26), 1)
        return s

    def update(self, player, obstacles):
        if self.dead: return
        self.tick_contact_timer()
        self._apply_gravity(obstacles)
        
        dist = self.distance_to(player.rect)

        if self.shoot_timer > 0: self.shoot_timer -= 1

        if self.state in (self.ST_WANDER, self.ST_RETURN):
            if dist < self.DETECT_RANGE: self.state = self.ST_POSITION
        elif self.state == self.ST_POSITION:
            if dist > self.LOSE_RANGE: self.state = self.ST_RETURN
            elif dist < self.RETREAT_DIST: self.state = self.ST_RETREAT
            elif abs(dist - self.PREFERRED_DIST) < 40: self.state = self.ST_SHOOT
        elif self.state == self.ST_SHOOT:
            if dist > self.LOSE_RANGE: self.state = self.ST_RETURN
            elif dist < self.RETREAT_DIST: self.state = self.ST_RETREAT
            elif abs(dist - self.PREFERRED_DIST) > 60: self.state = self.ST_POSITION
        elif self.state == self.ST_RETREAT:
            if dist > self.LOSE_RANGE: self.state = self.ST_RETURN
            elif dist > self.PREFERRED_DIST: self.state = self.ST_POSITION

        d = 1 if player.rect.centerx > self.rect.centerx else -1
        self.facing_right = (d == 1)

        if self.state == self.ST_WANDER:
            self._do_wander(obstacles)
        elif self.state == self.ST_RETURN:
            if self._do_return_to_spawn(obstacles): self.state = self.ST_WANDER
        elif self.state == self.ST_POSITION:
            if dist > self.PREFERRED_DIST + 40: self._try_move(d * self.SPEED, obstacles)
            elif dist < self.PREFERRED_DIST - 40: self._try_move(-d * self.SPEED, obstacles)
        elif self.state == self.ST_RETREAT:
            self._try_move(-d * self.SPEED * 2, obstacles)
        elif self.state == self.ST_SHOOT:
            if self.shoot_timer == 0:
                Arrow(self.rect.center, d, [self.arrows] + list(self.arrow_groups))
                self.shoot_timer = self.SHOOT_CD

        if dist < 40 and self.contact_timer == 0:
            player.take_damage(8)
            self.contact_timer = self.CONTACT_COOLDOWN

        self.arrows.update(obstacles)

# ================================================================
#  ESPRITS ÉLÉMENTAIRES
# ================================================================

class ExplosionVFX(pygame.sprite.Sprite):
    def __init__(self, pos, color, radius, groups):
        super().__init__(groups)
        d = radius * 2
        self.image = pygame.Surface((d, d), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (*color, 180), (radius, radius), radius)
        pygame.draw.circle(self.image, (*color[:3], 80), (radius, radius), radius, 4)
        self.rect  = self.image.get_rect(center=pos)
        self.timer = 18

    def update(self, *args):
        self.timer -= 1
        alpha = max(0, int(255 * self.timer / 18))
        self.image.set_alpha(alpha)
        if self.timer <= 0:
            self.kill()

class EspritBase(BaseEnemy):

    PATROL_SPEED     = 0
    PATROL_RADIUS    = 0
    SPEED            = 3
    JUMP_FORCE       = -11
    DETECT_RANGE     = 380
    LOSE_RANGE       = 560
    EXPLOSION_RADIUS = 50

    COULEUR_CORPS = PURPLE
    COULEUR_AURA  = (180, 0, 255)

    ST_WANDER  = "wander"
    ST_RETURN  = "return"
    ST_CHASE   = "chase"
    ST_EXPLODE = "explode"

    def __init__(self, pos, groups, hp, capacite, vfx_groups=None):
        super().__init__(pos, hp=hp, groups=groups, capacite_absorbable=capacite)

        w = h = 30
        self.image = self._build_img(w, h)
        self.rect  = self.image.get_rect(topleft=pos)

        self.state        = self.ST_WANDER
        self.vy           = 0
        self.on_floor     = False
        self.bounce_timer = random.randint(60, 120)

        self.vfx_groups = vfx_groups or []

    def _build_img(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        pygame.draw.ellipse(s, self.COULEUR_CORPS, (0, 4, w, h - 4))
        pygame.draw.ellipse(s, self.COULEUR_AURA,  (5, 0, w - 10, h // 2))
        pygame.draw.circle(s, WHITE,  (9,  9), 3)
        pygame.draw.circle(s, WHITE,  (21, 9), 3)
        pygame.draw.circle(s, BLACK,  (10, 9), 1)
        pygame.draw.circle(s, BLACK,  (22, 9), 1)
        return s

    def _apply_explosion(self, player):
        player.take_damage(10)

    def update(self, player, obstacles):
        if self.dead: return
        self.tick_contact_timer()

        dist = self.distance_to(player.rect)

        if self.state in (self.ST_WANDER, self.ST_RETURN):
            if dist < self.DETECT_RANGE:
                self.state = self.ST_CHASE

        elif self.state == self.ST_CHASE:
            if dist > self.LOSE_RANGE:
                self.state = self.ST_RETURN
            
            player_contact = self.rect.colliderect(player.rect)
            floor_under_player = (
                self.on_floor
                and abs(self.rect.centerx - player.rect.centerx) < self.EXPLOSION_RADIUS
                and abs(self.rect.bottom - player.rect.bottom) < 40
            )
            if player_contact or floor_under_player:
                self.state = self.ST_EXPLODE

        elif self.state == self.ST_EXPLODE:
            self._apply_explosion(player)
            ExplosionVFX(
                self.rect.center,
                self.COULEUR_CORPS,
                self.EXPLOSION_RADIUS,
                self.vfx_groups
            )
            self.dead = True
            self.on_death()
            return

        self._apply_gravity_esprit(obstacles)

        if self.state == self.ST_WANDER:
            self.bounce_timer -= 1
            if self.bounce_timer <= 0 and self.on_floor:
                self.vy = self.JUMP_FORCE * 0.4
                self.bounce_timer = random.randint(80, 140)

        elif self.state == self.ST_RETURN:
            if self._do_return_to_spawn(obstacles):
                self.state = self.ST_WANDER

        elif self.state == self.ST_CHASE:
            d = 1 if player.rect.centerx > self.rect.centerx else -1
            self._try_move(d * self.SPEED, obstacles)
            
            if self.on_floor:
                player_above = player.rect.centery < self.rect.centery - 20
                force = self.JUMP_FORCE * 1.1 if player_above else self.JUMP_FORCE * 0.9
                self.vy = force

    def _apply_gravity_esprit(self, obstacles):
        self.vy += 0.8
        if self.vy > 14: self.vy = 14
        self.rect.y  += int(self.vy)
        self.on_floor = False
        for hit in pygame.sprite.spritecollide(self, obstacles, False):
            if self.vy > 0:
                self.rect.bottom = hit.rect.top
                self.vy = 0; self.on_floor = True

# ── Esprit du Feu ──────────────────────────────────────────────

class EspritFeu(EspritBase):
    SPEED            = 4
    JUMP_FORCE       = -12
    DETECT_RANGE     = 450
    LOSE_RANGE       = 650
    EXPLOSION_RADIUS = 60
    COULEUR_CORPS    = (220, 60,  0)
    COULEUR_AURA     = (255, 200, 0)
    BURN_DPS         = 5
    BURN_DUR         = 3

    def __init__(self, pos, groups, vfx_groups=None):
        super().__init__(pos, groups, hp=30, capacite="fireball",
                         vfx_groups=vfx_groups)
        self.image = self._build_img(30, 30)

    def _apply_explosion(self, player):
        player.take_damage(12)
        if hasattr(player, 'burn_timer'):
            player.burn_timer = self.BURN_DUR * 60
            player.burn_dps   = self.BURN_DPS

# ── Esprit de Glace ────────────────────────────────────────────

class EspritGlace(EspritBase):
    SPEED            = 1
    JUMP_FORCE       = -8
    DETECT_RANGE     = 350
    LOSE_RANGE       = 500
    EXPLOSION_RADIUS = 70
    COULEUR_CORPS    = BLUE_ICE
    COULEUR_AURA     = CYAN
    SLOW_DUR         = 180
    SLOW_FAC         = 0.25

    def __init__(self, pos, groups, vfx_groups=None):
        super().__init__(pos, groups, hp=35, capacite="ice_shot",
                         vfx_groups=vfx_groups)
        self.image = self._build_img_ice(30, 30)

    def _build_img_ice(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        pygame.draw.ellipse(s, BLUE_ICE, (0, 4, w, h - 4))
        pygame.draw.ellipse(s, CYAN,     (5, 0, w - 10, h // 2))
        for cx, cy in [(5, 18), (15, 22), (24, 16)]:
            pygame.draw.polygon(s, WHITE,
                                [(cx, cy-6), (cx+3, cy), (cx, cy+4), (cx-3, cy)])
        pygame.draw.circle(s, WHITE,    (9,  9), 3)
        pygame.draw.circle(s, WHITE,    (21, 9), 3)
        pygame.draw.circle(s, BLUE_DARK, (10, 9), 1)
        pygame.draw.circle(s, BLUE_DARK, (22, 9), 1)
        return s

    def _apply_explosion(self, player):
        player.take_damage(8)
        player.slow_timer  = self.SLOW_DUR
        player.slow_factor = self.SLOW_FAC

# ── Esprit de Foudre ───────────────────────────────────────────

class EspritFoudre(EspritBase):
    SPEED            = 5
    JUMP_FORCE       = -14
    DETECT_RANGE     = 500
    LOSE_RANGE       = 700
    EXPLOSION_RADIUS = 55
    COULEUR_CORPS    = (180, 180, 0)
    COULEUR_AURA     = ELECTRIC
    SHOCK_DAMAGE     = 18
    TELEPORT_CD      = 150

    def __init__(self, pos, groups, vfx_groups=None):
        super().__init__(pos, groups, hp=25, capacite="thunder",
                         vfx_groups=vfx_groups)
        self.image   = self._build_img_thunder(30, 30)
        self.tp_timer = 0

    def _build_img_thunder(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        pygame.draw.ellipse(s, (180, 180, 20), (0, 4, w, h - 4))
        pygame.draw.ellipse(s, ELECTRIC,       (5, 0, w - 10, h // 2))
        pts = [(15, 2), (9, 13), (14, 13), (7, 27), (19, 11), (13, 11)]
        pygame.draw.polygon(s, WHITE, pts)
        pygame.draw.circle(s, WHITE,  (9,  9), 3)
        pygame.draw.circle(s, WHITE,  (21, 9), 3)
        pygame.draw.circle(s, BLACK,  (10, 9), 1)
        pygame.draw.circle(s, BLACK,  (22, 9), 1)
        return s

    def update(self, player, obstacles):
        if self.dead: return

        if self.state == self.ST_CHASE:
            if self.tp_timer > 0:
                self.tp_timer -= 1
            elif self.on_floor:
                offset_x = random.choice([-80, 80])
                nx = max(32, min(1920 - 32, player.rect.centerx + offset_x))
                self.rect.centerx = nx
                self.rect.bottom  = player.rect.bottom
                self.vy           = 0
                self.tp_timer     = self.TELEPORT_CD

        super().update(player, obstacles)

    def _apply_explosion(self, player):
        player.take_damage(self.SHOCK_DAMAGE)
        if hasattr(player, 'direction'):
            player.direction.y = -10

# ── Esprit de Nature ───────────────────────────────────────────

class EspritNature(EspritBase):
    SPEED            = 2
    JUMP_FORCE       = -10
    DETECT_RANGE     = 350
    LOSE_RANGE       = 500
    EXPLOSION_RADIUS = 65
    COULEUR_CORPS    = NATURE_GREEN
    COULEUR_AURA     = GREEN_LIGHT
    POISON_DPS       = 3
    POISON_DUR       = 4
    HEAL_AMOUNT      = 8
    HEAL_RADIUS      = 130
    HEAL_CD          = 180

    def __init__(self, pos, groups, vfx_groups=None):
        super().__init__(pos, groups, hp=20, capacite="poison_cloud",
                         vfx_groups=vfx_groups)
        self.image      = self._build_img_nature(30, 30)
        self.heal_timer = 0

    def _build_img_nature(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        pygame.draw.ellipse(s, NATURE_GREEN, (0, 4, w, h - 4))
        pygame.draw.ellipse(s, GREEN_LIGHT,  (5, 0, w - 10, h // 2))
        for angle, r in [(0, 8), (120, 8), (240, 8)]:
            rad = math.radians(angle)
            lx  = int(15 + r * math.cos(rad))
            ly  = int(15 + r * math.sin(rad))
            pygame.draw.ellipse(s, (0, 160, 30), (lx - 4, ly - 3, 8, 6))
        pygame.draw.circle(s, WHITE,  (9,  9), 3)
        pygame.draw.circle(s, WHITE,  (21, 9), 3)
        pygame.draw.circle(s, BLACK,  (10, 9), 1)
        pygame.draw.circle(s, BLACK,  (22, 9), 1)
        return s

    def update(self, player, obstacles):
        if self.dead: return
        if self.heal_timer > 0: self.heal_timer -= 1
        super().update(player, obstacles)

    def heal_allies(self, monster_group):
        if self.heal_timer > 0 or self.dead: return
        for ally in monster_group:
            if ally is self or ally.dead: continue
            if self.distance_to(ally.rect) < self.HEAL_RADIUS:
                ally.hp_current = min(ally.hp_max,
                                      ally.hp_current + self.HEAL_AMOUNT)
        self.heal_timer = self.HEAL_CD

    def _apply_explosion(self, player):
        player.take_damage(6)
        if hasattr(player, 'is_poisoned'):
            player.is_poisoned  = True
            player.poison_timer = self.POISON_DUR * 60
            player.poison_dps   = self.POISON_DPS

# ================================================================
#  GOLEM DE PIERRE 
# ================================================================

class GolemPierre(BaseEnemy):

    PATROL_SPEED   = 0
    PATROL_RADIUS  = 0
    SPEED          = 1
    DETECT_RANGE   = 600
    LOSE_RANGE     = 900
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
            self.image = self._img_blink0 if (self.reinforce_timer // 8) % 2 == 0 \
                         else self._img_blink1
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