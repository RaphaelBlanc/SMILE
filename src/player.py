import pygame
import os
from animator import Animator
from capacite import Capacite

# --- CALCUL DU CHEMIN SANS CONFIG.PY ---
# Le code est dans "src", on recule d'un dossier pour aller à la racine
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)

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

    def __init__(self, pos, sound_manager, keybinds=None, player_num=1):
        super().__init__()
        self.player_num = player_num
        
        
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

        self.direction = pygame.math.Vector2(0, 0)
        self.velocity  = pygame.math.Vector2(0, 0)

        self.count_jump   = 0
        self.jump_pressed = False
        self.sound_manager = sound_manager

        # --- VITESSE ET DIRECTION ---
        self.facing_right  = True
        self.normal_speed  = 6
        self.sprint_speed  = 10
        self.current_speed = self.normal_speed

        # --- CAPACITES ---
        self.capacite = Capacite(self)
        self.input_locked = False

        # --- VIE ---
        self.hp_max            = HP_MAX
        self.hp_current        = 100
        self.health_bar_length = 200

        # --- INVINCIBILITE apres degats ---
        self.hurt_timer    = 0
        self.hurt_duration = 45

        # --- EFFETS DE STATUT ---
        self.slow_timer   = 0
        self.slow_factor  = 1.0
        self.burn_timer   = 0
        self.burn_dps     = 0
        self.is_poisoned  = False
        self.poison_timer = 0
        self.poison_dps   = 0

        # --- ECHELLE ---
        self.on_ladder = False

        self.animations = {
            'idle': [], 'run': [], 'sprint': [], 'death': [],
            'land': [], 'back': [], 'jump': [], 'front': []
        }
        
        # Charge l'image (Taille définie dans load_assets)
        self.load_assets()
        
        self.animator       = Animator(self.animations, fps=10)
        self.status         = 'idle_right'
        self.is_sprinting   = False
        self.view_direction = 'side'

        if len(self.animations['idle_right']) > 0:
            self.image = self.animations['idle_right'][0]
        else:
            self.image = pygame.Surface((128, 128))
            self.image.fill((255, 0, 0))

        # -------------------------------------------------------------
        # REGLAGE DE LA HITBOX 
        # -------------------------------------------------------------
        self.hitbox_w = 128  # Largeur de la hitbox de collision
        self.hitbox_h = 128  # Hauteur de la hitbox

        self.rect = self.image.get_rect(topleft=pos)
        
        # On centre la petite hitbox en bas de la grande image
        self.hitbox = pygame.Rect(
            self.rect.centerx - (self.hitbox_w // 2), 
            self.rect.bottom - self.hitbox_h, 
            self.hitbox_w, 
            self.hitbox_h
        )

    def set_position(self, pos):
        self.rect.topleft = pos
        self.hitbox.centerx = self.rect.centerx
        self.hitbox.bottom = self.rect.bottom

    # -------------------------------------------------------------------------
    # DEGATS
    # -------------------------------------------------------------------------

    def take_damage(self, amount):
        if self.hurt_timer > 0: return
        self.hp_current = max(0, self.hp_current - int(amount))
        self.hurt_timer = self.hurt_duration

    # -------------------------------------------------------------------------
    # INPUT
    # -------------------------------------------------------------------------

    def get_input(self, ladder_sprites):
        if getattr(self, 'input_locked', False):
            class EmptyKeys:
                def __getitem__(self, item): return False
            keys = EmptyKeys()
        else:
            keys = pygame.key.get_pressed()
        kb   = self.keybinds

        if keys[kb["sprint"]]:
            self.is_sprinting = True
            self.current_speed = self.sprint_speed
        else:
            self.is_sprinting = False
            self.current_speed = self.normal_speed

        # Pygame utilise rect par défaut, on lui passe la hitbox temporairement
        temp_rect = self.rect
        self.rect = self.hitbox
        touching_ladder = bool(pygame.sprite.spritecollide(self, ladder_sprites, False))
        self.rect = temp_rect

        if touching_ladder:
            if keys[kb["move_up"]] or keys[kb["move_down"]]:
                self.on_ladder = True
        else:
            self.on_ladder = False

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
            if self.sound_manager:
                self.sound_manager.play("jump")

    # -------------------------------------------------------------------------
    # PHYSIQUE
    # -------------------------------------------------------------------------

    def apply_gravity(self):
        self.direction.y += GRAVITY
        if self.direction.y > 16:
            self.direction.y = 16

    def apply_ladder_physics(self):
        if getattr(self, 'input_locked', False):
            class EmptyKeys:
                def __getitem__(self, item): return False
            keys = EmptyKeys()
        else:
            keys = pygame.key.get_pressed()
        if keys[self.keybinds["move_up"]]:
            self.direction.y = -LADDER_CLIMB_SPEED
        elif keys[self.keybinds["move_down"]]:
            self.direction.y = LADDER_DESCEND_SPEED
        else:
            self.direction.y = LADDER_SLIP_SPEED

    # -------------------------------------------------------------------------
    # UPDATE
    # -------------------------------------------------------------------------

    def update(self, obstacles, ladder_sprites, plateforme_sprites, dt):
        
        if self.hp_current <= 0:
            self.status = 'death'
            self.direction.x = 0
            self.apply_gravity()
            self.move(obstacles, ladder_sprites, plateforme_sprites)
            self.capacite.projectiles.update(obstacles)
        else:
            self.get_input(ladder_sprites)
            self.get_status()

            # Timers
            if self.hurt_timer > 0: self.hurt_timer -= 1
            if self.slow_timer > 0: self.slow_timer -= 1
            else: self.slow_factor = 1.0

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

            # Capacités et Projectiles
            self.capacite.bdf(self.keybinds["attack"])
            self.capacite.dash(obstacles, self.keybinds["dash"])
            self.capacite.projectiles.update(obstacles)

            if self.on_ladder:
                self.apply_ladder_physics()
            else:
                self.apply_gravity()

            # Mouvement et Alignement de l'image
            self.move(obstacles, ladder_sprites, plateforme_sprites)

        # Animation Vitesse
        if self.status and 'sprint' in self.status:
            self.animator.animation_speed = 1.0 / 12
        elif self.status and 'idle' in self.status:
            self.animator.animation_speed = 1.0 / 6
        else:
            self.animator.animation_speed = 0.15

        loop = (self.status != 'death')
        self.image = self.animator.get_current_frame(dt, self.status, loop=loop)

        # Clignotement degats
        if self.hurt_timer > 0 and (self.hurt_timer // 6) % 2 == 0:
            blink = self.image.copy()
            blink.set_alpha(80)
            self.image = blink

    # -------------------------------------------------------------------------
    # MOUVEMENT & COLLISION (Utilise la Hitbox)
    # -------------------------------------------------------------------------

    def move(self, obstacles, ladder_sprites=None, plateforme_sprites=None):
        effective_speed = self.current_speed * self.slow_factor

        # 1. Mouvement Horizontal de la HITBOX
        self.hitbox.x += int(self.direction.x * effective_speed)
        self.check_collision('horizontal', obstacles)

        # 2. Mouvement Vertical de la HITBOX
        self.hitbox.y += self.direction.y
        self.check_collision('vertical', obstacles, ladder_sprites, plateforme_sprites)
        
        # 3. Alignement Visuel : On force le rect à prendre la taille exacte de l'image (225x225)
        self.rect = self.image.get_rect()
        
        # On aligne le bas de l'image sur le bas de la hitbox
        self.rect.midbottom = self.hitbox.midbottom

        # --- AJUSTEMENT VISUEL ---
        # Si ton slime vole ou s'enfonce dans le sol, modifie cette valeur
        offset_y = 80
        self.rect.y += offset_y

    def check_collision(self, direction, obstacles, ladder_sprites=None, plateforme_sprites=None):
        # On echange temporairement le rect et la hitbox pour Pygame
        temp_rect = self.rect
        self.rect = self.hitbox
        hits = list(pygame.sprite.spritecollide(self, obstacles, False))
        
        # Plateformes "One-way" pour les échelles (marcher dessus sans tomber)
        if getattr(self, 'input_locked', False):
            class EmptyKeys:
                def __getitem__(self, item): return False
            keys = EmptyKeys()
        else:
            keys = pygame.key.get_pressed()
        pressing_down = keys[self.keybinds["move_down"]]
        
        if ladder_sprites and direction == 'vertical' and self.direction.y > 0 and not pressing_down:
            ladder_hits = pygame.sprite.spritecollide(self, ladder_sprites, False)
            for l in ladder_hits:
                if self.hitbox.bottom - self.direction.y <= l.rect.top + 15:
                    hits.append(l)

        if plateforme_sprites and direction == 'vertical' and self.direction.y > 0 and not pressing_down:
            plateforme_hits = pygame.sprite.spritecollide(self, plateforme_sprites, False)
            for p in plateforme_hits:
                if self.hitbox.bottom - self.direction.y <= p.rect.top + 15:
                    hits.append(p)

        self.rect = temp_rect # On remet en place

        if hits:
            if direction == 'horizontal':
                # ---- AUTO-STEP (Minecraft like) ----
                # Find the highest obstacle we collided with (lowest Y)
                highest_top = min(hit.rect.top for hit in hits)
                step_height = self.hitbox.bottom - highest_top
                
                # If the step is small enough (e.g. 2 tiles of 32px + small margin)
                if 0 < step_height <= 66:
                    self.hitbox.y -= step_height
                    self.rect = temp_rect
                    return
                        
                # Normal horizontal collision
                if self.direction.x > 0:
                    self.hitbox.right = hits[0].rect.left
                if self.direction.x < 0:
                    self.hitbox.left = hits[0].rect.right

            if direction == 'vertical':
                if self.direction.y > 0:
                    self.hitbox.bottom = min(hit.rect.top for hit in hits)
                    self.direction.y = 0
                    self.count_jump  = 0
                    self.on_ladder   = False
                if self.direction.y < 0:
                    self.hitbox.top    = max(hit.rect.bottom for hit in hits)
                    self.direction.y = 0

    # -------------------------------------------------------------------------
    # STATUT / ANIMATION
    # -------------------------------------------------------------------------

    def get_status(self):
        if self.hp_current <= 0:
            self.status = 'death'
            return

        if getattr(self, 'input_locked', False):
            class EmptyKeys:
                def __getitem__(self, item): return False
            keys = EmptyKeys()
        else:
            keys = pygame.key.get_pressed()
        kb   = self.keybinds

        if keys[kb["move_up"]]:
            self.view_direction = 'back'
        elif not self.on_ladder and keys[kb["move_down"]]:
            self.view_direction = 'front'

        if self.on_ladder:
            self.status = 'back'
            return

        if self.direction.y < -0.1 or self.direction.y > 1.1:
            action = 'jump' if self.direction.y < 0 else 'land'
            self.status = action + ("_right" if self.facing_right else "_left")
            self.view_direction = 'side'

        elif self.direction.x != 0:
            action = 'sprint' if self.is_sprinting else 'run'
            self.status = action + ("_right" if self.facing_right else "_left")
            self.view_direction = 'side'

        else:
            if self.view_direction == 'back':
                self.status = 'back'
            elif self.view_direction == 'front':
                self.status = 'front'
            else:
                self.status = 'idle' + ("_right" if self.facing_right else "_left")

    # -------------------------------------------------------------------------
    # CHARGEMENT ASSETS (SLIME SPRITE SHEETS)
    # -------------------------------------------------------------------------

    def load_assets(self):
        # On a retiré attack_right et attack_left de la liste
        actions = [
            'idle_right', 'idle_left', 'run_right', 'run_left', 
            'sprint_right', 'sprint_left', 'jump_right', 'jump_left', 
            'land_right', 'land_left', 'death', 'back', 'front'
        ]
        self.animations.clear()
        self.animations.update({action: [] for action in actions})

        # --- NOUVEAU CHEMIN DES IMAGES ---
        if getattr(self, 'player_num', 1) == 2:
            base_path = os.path.join(ROOT_DIR, 'assets', 'images', 'player2', 'mouvements')
            prefix = "Slime2_"
            death_file = "Slime2_Death.png"
        else:
            base_path = os.path.join(ROOT_DIR, 'assets', 'images', 'player', 'mouvements')
            prefix = "Slime1_"
            death_file = "Slime1_Death_body.png"

        # --- REGLAGE DE LA TAILLE VISUELLE (Image Géante) ---
        SLIME_SIZE = (225, 225) 

        # --- ORIENTATION DES LIGNES ---
        ROW_FRONT = 0
        ROW_BACK  = 1
        ROW_LEFT  = 2
        ROW_RIGHT = 3

        def slice_sheet(filename, cols, rows):
            path = os.path.join(base_path, filename)
            if not os.path.exists(path):
                print(f"ATTENTION : Fichier manquant {filename} dans {base_path}")
                return None
            try:
                sheet = pygame.image.load(path).convert_alpha()
                frame_w = sheet.get_width() // cols
                frame_h = sheet.get_height() // rows
                
                sheet_frames = []
                for r in range(rows):
                    row_frames = []
                    for c in range(cols):
                        rect = pygame.Rect(c * frame_w, r * frame_h, frame_w, frame_h)
                        img = pygame.Surface((frame_w, frame_h), pygame.SRCALPHA)
                        img.blit(sheet, (0, 0), rect)
                        img = pygame.transform.scale(img, SLIME_SIZE)
                        row_frames.append(img)
                    sheet_frames.append(row_frames)
                return sheet_frames
            except Exception as e:
                print(f"Erreur decoupage {filename}: {e}")
                return None

        # 1. IDLE / MOUVEMENT
        idle_frames = slice_sheet(f"{prefix}Idle_body.png", cols=6, rows=4)
        if idle_frames:
            self.animations['front']      = idle_frames[ROW_FRONT]
            self.animations['back']       = idle_frames[ROW_BACK]
            self.animations['idle_left']  = idle_frames[ROW_LEFT]
            self.animations['idle_right'] = idle_frames[ROW_RIGHT]
            
            # On utilise l'animation idle pour courir/sauter
            self.animations['run_left']     = idle_frames[ROW_LEFT]
            self.animations['run_right']    = idle_frames[ROW_RIGHT]
            self.animations['sprint_left']  = idle_frames[ROW_LEFT]
            self.animations['sprint_right'] = idle_frames[ROW_RIGHT]
            self.animations['jump_left']    = idle_frames[ROW_LEFT]
            self.animations['jump_right']   = idle_frames[ROW_RIGHT]
            self.animations['land_left']    = idle_frames[ROW_LEFT]
            self.animations['land_right']   = idle_frames[ROW_RIGHT]

        # 2. MORT
        death_frames = slice_sheet(death_file, cols=10, rows=4)
        if death_frames:
            self.animations['death'] = death_frames[ROW_FRONT]

        # SECURITE : Remplit avec un carré rose si jamais une animation manque
        for state in self.animations:
            if not self.animations[state]:
                placeholder = pygame.Surface(SLIME_SIZE)
                placeholder.fill((255, 0, 255))
                self.animations[state].append(placeholder)