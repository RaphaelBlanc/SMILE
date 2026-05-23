import pygame
import os
from capacite import Capacite
from animator import Animator

#ECRAN#
SCREEN_WIDTH  = 1920
SCREEN_HEIGHT = 1072
FPS = 60

#COULEURS#
WHITE     = (255, 255, 255)
BLACK     = (0,   0,   0)
RED       = (255, 0,   0)
BLUE_NPC  = (0,   0,   255)
BLUE_MENU = (0,   102, 204)
PURPLE    = (127, 0,   255)
ORANGE    = (255, 165, 0)
GREEN     = (0,   255, 0)

#PHYSIQUE#
GRAVITY      = 0.8
JUMP_FORCE   = -16
PLAYER_SPEED = 6
FRICTION     = -0.12
HP_MAX       = 100

# --- ECHELLE ---
LADDER_CLIMB_SPEED   = 4
LADDER_DESCEND_SPEED = 5
LADDER_SLIP_SPEED    = 1.5

TARGET_SIZE = (64, 64)

#CLASS PLAYER########################################################################

class Player(pygame.sprite.Sprite):

    def __init__(self, pos, sound_manager, keybinds=None):
        super().__init__()
        self.image = pygame.Surface((32, 64))
        self.image.fill(RED)

        self.rect      = self.image.get_rect(topleft=pos)
        self.direction = pygame.math.Vector2(0, 0)
        self.velocity  = pygame.math.Vector2(0, 0)

        self.count_jump   = 0
        self.jump_pressed = False
        self.sound_manager = sound_manager

        # --- TOUCHES CONFIGURABLES ---
        self.keybinds = keybinds or {
            "move_left":  pygame.K_q,
            "move_right": pygame.K_d,
            "move_up":    pygame.K_z,
            "move_down":  pygame.K_s,
            "jump":       pygame.K_SPACE,
            "sprint":     pygame.K_LSHIFT,
            "attack":     pygame.K_f,
            "dash":       pygame.K_v,
        }

        # --- VITESSE ET DIRECTION ---
        self.facing_right  = True
        self.normal_speed  = 6
        self.sprint_speed  = 10
        self.current_speed = self.normal_speed

        # --- CAPACITES ---
        self.capacite = Capacite(self)

        # --- VIE ---
        self.hp_max            = HP_MAX
        self.hp_current        = 100
        self.health_bar_length = 200

        # --- INVINCIBILITE apres degats (Hugo) ---
        self.hurt_timer    = 0
        self.hurt_duration = 45

        # --- EFFETS DE STATUT (Hugo — necessaires pour les monstres) ---
        self.slow_timer   = 0
        self.slow_factor  = 1.0
        self.burn_timer   = 0
        self.burn_dps     = 0
        self.is_poisoned  = False
        self.poison_timer = 0
        self.poison_dps   = 0

        # --- ECHELLE (ton code) ---
        self.on_ladder = False

        self.animations = {
            'idle': [], 'run': [], 'sprint': [], 'death': [],
            'attack': [], 'land': [], 'back': [], 'jump': [], 'front': []
        }
        self.load_assets()
        self.animator       = Animator(self.animations, fps=10)
        self.status         = 'idle'
        self.is_sprinting   = False
        self.view_direction = 'side'
        self.is_attacking   = False

        if len(self.animations['idle_right']) > 0:
            self.image = self.animations['idle_right'][0]
        else:
            print("ERREUR CRITIQUE : Aucune image trouvée dans assets/images/player/idle_right/")
            self.image = pygame.Surface((32, 64))
            self.image.fill((255, 0, 0))

        self.rect = self.image.get_rect(topleft=pos)
        self.rect = self.image.get_rect(topleft=pos)

    # -------------------------------------------------------------------------
    # DEGATS avec invincibilite (Hugo)
    # -------------------------------------------------------------------------

    def take_damage(self, amount):
        """Applique des degats avec fenetre d'invincibilite."""
        if self.hurt_timer > 0:
            return
        self.hp_current = max(0, self.hp_current - int(amount))
        self.hurt_timer = self.hurt_duration

    # -------------------------------------------------------------------------
    # INPUT
    # -------------------------------------------------------------------------

    def get_input(self, ladder_sprites):
        keys = pygame.key.get_pressed()
        kb   = self.keybinds   # raccourci lisible

        # ATTAQUE
        if keys[kb["attack"]] and not self.is_attacking:
            self.is_attacking = True
            self.animator.frame_index = 0

        # SPRINT
        if keys[kb["sprint"]]:
            self.is_sprinting = True
            self.speed = 10
        else:
            self.is_sprinting = False
            self.speed = 6

        # DETECTION ECHELLE
        touching_ladder = bool(pygame.sprite.spritecollide(self, ladder_sprites, False))
        if touching_ladder:
            if keys[kb["move_up"]]:
                self.on_ladder = True
            if keys[kb["move_down"]]:
                self.on_ladder = True
        else:
            self.on_ladder = False

        # MOUVEMENT HORIZONTAL
        moving_right      = keys[kb["move_right"]]
        moving_left       = keys[kb["move_left"]]
        moving_horizontal = moving_right or moving_left

        if moving_horizontal:
            if moving_right:
                self.direction.x  = 1
                self.facing_right = True
            elif moving_left:
                self.direction.x  = -1
                self.facing_right = False
            if self.on_ladder:
                self.on_ladder = False
        else:
            self.direction.x = 0

        # VITESSE
        if keys[kb["sprint"]]:
            self.current_speed = self.sprint_speed
        else:
            self.current_speed = self.normal_speed

        # SAUT
        if keys[kb["jump"]] and not self.jump_pressed:
            self.on_ladder = False
            self.jump()
            self.jump_pressed = True
        if not keys[kb["jump"]]:
            self.jump_pressed = False

    def jump(self):
        if self.count_jump < 2:
            self.direction.y = JUMP_FORCE
            self.count_jump += 1
            self.sound_manager.play("jump")

    # -------------------------------------------------------------------------
    # PHYSIQUE
    # -------------------------------------------------------------------------

    def apply_gravity(self):
        self.direction.y += GRAVITY
        if self.direction.y > 16:
            self.direction.y = 16

    def apply_ladder_physics(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_z] or keys[pygame.K_UP]:
            self.direction.y = -LADDER_CLIMB_SPEED
        elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self.direction.y = LADDER_DESCEND_SPEED
        else:
            self.direction.y = LADDER_SLIP_SPEED

    # -------------------------------------------------------------------------
    # UPDATE
    # -------------------------------------------------------------------------

    def update(self, obstacles, ladder_sprites, dt):
        self.get_input(ladder_sprites)
        self.get_status()

        # --- TIMERS (Hugo) ---
        if self.hurt_timer > 0:
            self.hurt_timer -= 1

        if self.slow_timer > 0:
            self.slow_timer -= 1
        else:
            self.slow_factor = 1.0

        if self.burn_timer > 0:
            self.burn_timer -= 1
            if self.burn_timer % 60 == 0:
                self.hp_current = max(0, self.hp_current - int(self.burn_dps))

        if self.is_poisoned and self.poison_timer > 0:
            self.poison_timer -= 1
            if self.poison_timer % 60 == 0:
                self.hp_current = max(0, self.hp_current - int(self.poison_dps))
            if self.poison_timer <= 0:
                self.is_poisoned = False

        # --- ANIMATION ---
        if self.is_attacking:
            self.animator.animation_speed = 0.25
        elif self.status and 'sprint' in self.status:
            self.animator.animation_speed = 1.0 / 12
        elif self.status and 'idle' in self.status:
            self.animator.animation_speed = 1.0 / 6
        else:
            self.animator.animation_speed = 0.15

        raw_image = self.animator.get_current_frame(dt, self.status)

        if self.facing_right:
            self.image = raw_image
        else:
            self.image = pygame.transform.flip(raw_image, True, False)

        # CLIGNOTEMENT si blesse (Hugo)
        if self.hurt_timer > 0 and (self.hurt_timer // 6) % 2 == 0:
            blink = self.image.copy()
            blink.set_alpha(80)
            self.image = blink

        self.capacite.bdf(self.keybinds["attack"])
        self.capacite.projectiles.update(obstacles)
        self.capacite.dash(obstacles, self.keybinds["dash"])

        # PHYSIQUE : gravite normale OU echelle
        if self.on_ladder:
            self.apply_ladder_physics()
        else:
            self.apply_gravity()

        self.move(obstacles)

    # -------------------------------------------------------------------------
    # MOUVEMENT & COLLISION
    # -------------------------------------------------------------------------

    def move(self, obstacles):
        # Vitesse effective avec ralentissement (Hugo)
        effective_speed = self.current_speed * self.slow_factor

        self.rect.x += int(self.direction.x * effective_speed)
        self.check_collision('horizontal', obstacles)

        self.rect.y += self.direction.y
        self.check_collision('vertical', obstacles)

    def check_collision(self, direction, obstacles):
        hits = pygame.sprite.spritecollide(self, obstacles, False)

        if hits:
            if direction == 'horizontal':
                if self.direction.x > 0:
                    self.rect.right = hits[0].rect.left
                if self.direction.x < 0:
                    self.rect.left = hits[0].rect.right

            if direction == 'vertical':
                if self.direction.y > 0:
                    self.rect.bottom = hits[0].rect.top
                    self.direction.y = 0
                    self.count_jump  = 0
                    self.on_ladder   = False
                if self.direction.y < 0:
                    self.rect.top    = hits[0].rect.bottom
                    self.direction.y = 0

    # -------------------------------------------------------------------------
    # STATUT / ANIMATION
    # -------------------------------------------------------------------------

    def get_status(self):
        keys = pygame.key.get_pressed()
        kb   = self.keybinds

        if keys[kb["move_up"]]:
            self.view_direction = 'back'
        elif not self.on_ladder and keys[kb["move_down"]]:
            self.view_direction = 'front'

        # 1. ATTAQUE
        if self.is_attacking:
            self.status = 'attack' + ("_right" if self.facing_right else "_left")
            if self.animator.frame_index >= len(self.animations[self.status]) - 1:
                self.is_attacking = False
            return

        # 2. ECHELLE
        if self.on_ladder:
            self.status = 'back'
            return

        # 3. SAUT / CHUTE
        if self.direction.y < -0.1 or self.direction.y > 1.1:
            action = 'jump' if self.direction.y < 0 else 'land'
            self.status = action + ("_right" if self.facing_right else "_left")
            self.view_direction = 'side'

        # 4. MOUVEMENT HORIZONTAL
        elif self.direction.x != 0:
            action = 'sprint' if self.is_sprinting else 'run'
            self.status = action + ("_right" if self.facing_right else "_left")
            self.view_direction = 'side'

        # 5. REPOS / VUES SPECIALES
        else:
            if self.view_direction == 'back':
                self.status = 'back'
            elif self.view_direction == 'front':
                self.status = 'front'
            else:
                self.status = 'idle' + ("_right" if self.facing_right else "_left")

    # -------------------------------------------------------------------------
    # CHARGEMENT ASSETS
    # -------------------------------------------------------------------------

    def load_assets(self):
        actions = ['idle', 'run', 'sprint', 'death', 'attack', 'jump', 'land', 'back', 'front']
        self.animations = {}
        for action in actions:
            if action in ['jump', 'land', 'idle', 'run', 'sprint', 'death', 'attack']:
                self.animations[f"{action}_right"] = []
                self.animations[f"{action}_left"]  = []
            else:
                self.animations[action] = []

        base_path = 'assets/images/player/'
        for state in self.animations.keys():
            full_path = os.path.join(base_path, state)
            if os.path.exists(full_path):
                files = sorted(os.listdir(full_path))
                for file_name in files:
                    if file_name.lower().endswith('.png'):
                        image_path = os.path.join(full_path, file_name)
                        image_surf = pygame.image.load(image_path).convert_alpha()
                        image_surf = pygame.transform.scale_by(image_surf, 0.5)
                        self.animations[state].append(image_surf)

            if len(self.animations[state]) == 0:
                print(f"--- ATTENTION : Aucune image trouvée dans {full_path} ---")
                placeholder = pygame.Surface((32, 64))
                placeholder.fill((255, 0, 255))
                self.animations[state].append(placeholder)