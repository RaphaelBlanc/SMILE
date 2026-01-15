import pygame
import os
from capacite import Capacite
from animator import Animator

#ECRAN#
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1072
FPS = 60              #Pour un jeu en 60 images par seconde, fluide

#COULEURS#
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE_NPC = (0, 0, 255) 
BLUE_MENU = (0, 102, 204) # Couleur des boutons du menu
PURPLE = (127, 0, 255)
ORANGE = (255, 165, 0) # Pour les projectiles
GREEN = (0, 255, 0)    # Pour la barre de vie

#PHYSIQUE#
GRAVITY = 0.8     #Force qui tire vers le bas a chaque frame
JUMP_FORCE = -16  #Force negative, vers le haut, pour le saut
PLAYER_SPEED = 6  #Vitesse de deplacement horizontale
FRICTION = -0.12  #Resistance au sol pour un arret progressif
HP_MAX = 100 # Points de vie max

TARGET_SIZE = (64, 64) 

#CLASS PLAYER########################################################################

class Player(pygame.sprite.Sprite): #la classe est une enfant de la classe Sprite de pygame

    def __init__(self, pos, sound_manager):
        super().__init__() #permet de ne pas ecraser l'init de la clase Sprite de Pygame
        self.image = pygame.Surface((32, 64))
        self.image.fill(RED)  #je colore le toile de pixel image en rouge

        self.rect = self.image.get_rect(topleft=pos) 
        self.direction = pygame.math.Vector2(0, 0)

        self.velocity = pygame.math.Vector2(0, 0)

        self.count_jump = 0 #J'initialise un compteur pour faire un seul saut
        self.sound_manager = sound_manager #on stocke le gestionnaire de son pour l'utiliser plus tard

        # --- GESTION VITESSE ET DIRECTION ---
        self.facing_right = True # Pour savoir où tirer
        self.normal_speed = 6
        self.sprint_speed = 10
        self.current_speed = self.normal_speed

        # --- CAPACITES ---
        self.capacite = Capacite(self) # On lie le joueur à ses capacités

        # --- VIE ---
        self.hp_max = HP_MAX
        self.hp_current = 100
        self.health_bar_length = 200

        self.animations = {'idle': [], 'run': [], 'sprint': [], 'death': [], 'attack': []}
        self.load_assets()
        self.animator = Animator(self.animations, fps=10)
        self.status = 'idle'

        self.is_sprinting = False

        if len(self.animations['idle_right']) > 0:
            self.image = self.animations['idle_right'][0]
        else:
            print("ERREUR CRITIQUE : Aucune image trouvée dans assets/idle_right/")
            self.image = pygame.Surface((32, 64))
            self.image.fill((255, 0, 0)) # Un carré rouge pour indiquer l'erreur

        self.rect = self.image.get_rect(topleft=pos)
        self.rect = self.image.get_rect(topleft=pos)

    def get_input(self):
        keys = pygame.key.get_pressed()

        # Si Shift Gauche est pressé, is_sprinting devient True
        if keys[pygame.K_LSHIFT]:
            self.is_sprinting = True
            self.speed = 10 # Tu peux aussi augmenter la vitesse ici
        else:
            self.is_sprinting = False
            self.speed = 6

        # Mouvement + Direction du regard
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.direction.x = 1
            self.facing_right = True
        elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.direction.x = -1
            self.facing_right = False
        else:
            self.direction.x = 0
        
        # Sprint (Shift)
        if keys[pygame.K_LSHIFT]:
            self.current_speed = self.sprint_speed
        else:
            self.current_speed = self.normal_speed
        
        # Saut (Space)
        if keys[pygame.K_SPACE] and not self.jump_pressed:
            self.jump()
            self.jump_pressed = True
        if not keys[pygame.K_SPACE]:
            self.jump_pressed = False
    
    def jump(self):
        if self.count_jump < 2 :
            self.direction.y = JUMP_FORCE
            self.count_jump += 1
            self.sound_manager.play("jump")

    def apply_gravity(self):
        self.direction.y += GRAVITY 
        if self.direction.y > 16: # Limite de vitesse de chute
            self.direction.y = 16


    def update(self, obstacles, dt):
        self.get_input() 
        self.get_status()

        raw_image = self.animator.get_current_frame(dt, self.status)

        if self.facing_right:
            self.image = raw_image
        else:
            self.image = pygame.transform.flip(raw_image, True, False)

        if self.status == 'sprint':
            self.animator.animation_speed = 1.0 / 12  # Plus rapide (12 FPS)
        elif self.status == 'idle':
            self.animator.animation_speed = 1.0 / 6   # Plus lent (6 FPS)

        self.image = self.animator.get_current_frame(dt, self.status)
        self.capacite.bdf() # Vérifie si on tire
        self.capacite.projectiles.update(obstacles) # Met à jour les boules de feu existantes
        self.capacite.dash(obstacles) # Vérifie si on dash

        self.apply_gravity() 
        self.move(obstacles)

    def move(self, obstacles):
        """Ici le but va etre de faire une gestion precise des mouvements
        CAD : Mouvement --> Collision --> Correction position"""

        # --- AXE X (Horizontal) ---
        self.rect.x += self.direction.x * self.current_speed
        self.check_collision('horizontal', obstacles)

        # --- AXE Y (Vertical) ---
        self.rect.y += self.direction.y
        self.check_collision('vertical', obstacles)

    def check_collision(self, direction, obstacles):
        """On detecte et on resout les collisions"""
        # On vérifie si le rect du joueur touche un des rects du groupe obstacles
        hits = pygame.sprite.spritecollide(self, obstacles, False)

        if hits: # S'il y a collision
            if direction == 'horizontal':
                # Si on allait à droite, on se colle à gauche du mur
                if self.direction.x > 0: 
                    self.rect.right = hits[0].rect.left
                # Si on allait à gauche, on se colle à droite du mur
                if self.direction.x < 0: 
                    self.rect.left = hits[0].rect.right
            
            if direction == 'vertical':
                # Si on tombait (gravité), on atterrit sur le mur
                if self.direction.y > 0: 
                    self.rect.bottom = hits[0].rect.top
                    self.direction.y = 0     # On arrête la chute
                    self.count_jump = 0      # On récupère le saut
                
                # Si on sautait et qu'on tape un plafond
                if self.direction.y < 0: 
                    self.rect.top = hits[0].rect.bottom
                    self.direction.y = 0     # On se cogne la tête
      
    def get_status(self):
        # 1. On détermine l'action de base
        if self.hp_current <= 0:
            action = 'death'
        elif pygame.key.get_pressed()[pygame.K_f]:
            action = 'attack'
        elif self.direction.x != 0:
            action = 'sprint' if self.is_sprinting else 'run'
        else:
            action = 'idle'

        direction_suffix = "_right" if self.facing_right else "_left"
    
        self.status = action + direction_suffix

    def load_assets(self):
        # 1. On prépare les clés
        actions = ['idle', 'run', 'sprint', 'death', 'attack']
        self.animations = {}
        for action in actions:
            self.animations[f"{action}_right"] = []
            self.animations[f"{action}_left"] = []

        # 2. Chemin vers ton dossier assets
        # Si tes dossiers sont directement dans Bureau/SMILET/SMILE/assets/
        base_path = 'assets/' 

        # 3. On parcourt les dossiers d'animations
        for state in self.animations.keys():
            full_path = os.path.join(base_path, state)
            
            if os.path.exists(full_path):
                # On récupère la liste des fichiers
                files = sorted(os.listdir(full_path))
                
                for file_name in files: # On boucle sur CHAQUE fichier
                    if file_name.lower().endswith('.png'): # .lower() gère .png et .PNG
                        image_path = os.path.join(full_path, file_name)
                        
                        # Chargement et redimensionnement
                        image_surf = pygame.image.load(image_path).convert_alpha()
                        image_surf = pygame.transform.scale_by(image_surf, 0.5)
                        
                        # On ajoute l'image à la liste de cette animation
                        self.animations[state].append(image_surf)
            
            # 4. Sécurité : Si après la boucle le dossier était vide ou absent
            if len(self.animations[state]) == 0:
                print(f"--- ATTENTION : Aucune image trouvée dans {full_path} ---")
                placeholder = pygame.Surface((32, 64))
                placeholder.fill((255, 0, 255)) # Rose pour indiquer une erreur
                self.animations[state].append(placeholder)

    