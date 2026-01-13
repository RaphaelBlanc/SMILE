import pygame
from capacite import Capacite

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


#CLASS PLAYER########################################################################

class Player(pygame.sprite.Sprite): #la classe est une enfant de la classe Sprite de pygame

    def __init__(self, pos, sound_manager):
        super().__init__() #permet de ne pas ecraser l'init de la clase Sprite de Pygame
        self.image = pygame.Surface((32, 64))
        self.image.fill(RED)  #je colore le toile de pixel image en rouge

        self.rect = self.image.get_rect(topleft=pos) 
        self.direction = pygame.math.Vector2(0, 0)

        """Ce vecteur est assez facilitant, on l'utilisera dans les fonctions
        suivantes pour recuperer vers ou veux aller le joueur ainsi que l'application
        de la gravite"""

        self.velocity = pygame.math.Vector2(0, 0)

        """Ce vecteur va etre celui que l'on va ajouter a la position
        on va pouvoir gerer l'inertie et d'autre chose avec"""

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

    def get_input(self):
        keys = pygame.key.get_pressed()

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
        "Methode dedie au saut, on note qu'on fera par la suite un verification pour"
        "savoir si notre personnage est sur le sol"

        if self.count_jump < 2 :
            self.direction.y = JUMP_FORCE
            self.count_jump += 1
            self.sound_manager.play("jump")

    def apply_gravity(self):
        self.direction.y += GRAVITY 
        if self.direction.y > 16: # Limite de vitesse de chute
            self.direction.y = 16


    def update(self, obstacles):
        self.get_input() 
        
        # --- GESTION DES CAPACITES ---
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
      