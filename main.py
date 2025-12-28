#SECTION IMPORT #######################################################################

import pygame #moteur graphique
import sys 
from pytmx.util_pygame import load_pygame #pour la map tmx


"""Sys permet de communiquer avec le systeme, ce qui permettra d'arreter le programme
quand on appellera pygame.quit(), notamment avec sys.exit() qui permet de kill le processus
python de maniere propre"""

#DEFINITON CONSTANTE##################################################################

"""Par convention, on ecrit le nom des constantes en majuscules"""

#ECRAN#
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1072
FPS = 60              #Pour un jeu en 60 images par seconde, fluide

#COULEURS#
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)

#PHYSIQUE#
GRAVITY = 0.8     #Force qui tire vers le bas a chaque frame
JUMP_FORCE = -16  #Force negative, vers le haut, pour le saut
PLAYER_SPEED = 6  #Vitesse de deplacement horizontale
FRICTION = -0.12  #Resistance au sol pour un arret progressif

#CLASS ASSET MANAGER#################################################################

class AssetManager:

    def __init__(self):
        pass

#CLASS TILE#########################################################################

class Tile(pygame.sprite.Sprite):
    def __init__(self, pos, surf, groups):
        super().__init__(groups) 
        self.image = surf
        self.rect = self.image.get_rect(topleft=pos)



#CLASS PLAYER########################################################################

class Player(pygame.sprite.Sprite): #la classe est une enfant de la classe Sprite de pygame

    def __init__(self, pos):
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


    def get_input(self):
        """Gestion des entrees du clavier"""

        keys = pygame.key.get_pressed()

        #Pour le mouvement horizontal
        if keys[pygame.K_RIGHT]:
            self.direction.x = 1
        elif keys[pygame.K_LEFT]:
            self.direction.x = -1
        else:
            self.direction.x = 0
        
        #Gestion du saut simple, pour l'instant, apres on fera qqc de mieux
        if keys[pygame.K_SPACE]:
            self.jump()
    
    def jump(self):
        "Methode dedie au saut, on note qu'on fera par la suite un verification pour"
        "savoir si notre personnage est sur le sol"

        if self.count_jump != 1 :
            self.direction.y = JUMP_FORCE
            self.count_jump = 1

    def apply_gravity(self):
        """On applique la gravite a la vitesse verticale"""

        self.direction.y += GRAVITY # on appliquera direction au rect plus bas

    def update(self, obstacles):
        """On fait le calcul de la physique a chaque frame"""

        self.get_input() #on demande recup ce que le joueur veut faire
        self.apply_gravity() #on applique la gravite

        self.move(obstacles)

    def move(self, obstacles):
        """Ici le but va etre de faire une gestion precise des mouvements
        CAD : Mouvement --> Collision --> Correction position"""

        # --- AXE X (Horizontal) ---
        self.rect.x += self.direction.x * PLAYER_SPEED
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
        

#CLASS GAME#########################################################################

class Game:

    def __init__(self):
        pygame.init() #je lance la fenetre pygame
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT)) #taille de l'ecran
        pygame.display.set_caption("SMILE") #pour le nom de la fenetre
        self.clock = pygame.time.Clock()

        #CREATION GROUPES DE SPRITES
        #Visibles
        self.visibles_sprites = pygame.sprite.Group()
        #Obstable
        self.obstacle_sprites = pygame.sprite.Group()

        # --- CHARGEMENT DE LA MAP TILED ---
        tmx_data = load_pygame('map.tmx') # Charge le fichier

        try:
            layer_fond = tmx_data.get_layer_by_name('Background')
            self.background_image = layer_fond.image
        except ValueError:
            print("ERREUR : Je ne trouve pas le calque 'Background'. Vérifie le nom dans Tiled !")
            # On met un fond gris par défaut pour pas que ça plante
            self.background_image = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            self.background_image.fill((50, 50, 50))

        # On parcourt le calque 'Collisions' (c'est le nom que tu as donné dans Tiled)
        # layer.tiles() renvoie : x, y, et l'image (surf) de la tuile

        for x, y, surf in tmx_data.get_layer_by_name('Collisions').tiles():
            # Tiled donne des coordonnées en "grille" (ex: case 0, case 1)
            # On multiplie par la taille d'une tuile (32x32 dans ton cas ?) pour avoir les pixels
            pos = (x * 32, y * 32) # <--- VERIFIE SI TES TUILES FONT BIEN 32px
            
            # On crée un mur à cet endroit et on l'ajoute aux groupes
            Tile(pos, surf, [self.obstacle_sprites])

        # --- CREATION DU JOUEUR ---
        self.player = Player((200, 200)) # Position de départ arbitraire
        self.visibles_sprites.add(self.player) # On l'ajoute au groupe visible

    def update(self):
        #On appelle la fonction update de tout les sprites du groupe obstacles
        self.player.update(self.obstacle_sprites)

    def draw(self):
        # 1. D'ABORD ON DESSINE LE FOND (NOUVEAU)
        # On colle l'image de fond en haut à gauche (0,0)
        self.screen.blit(self.background_image, (0, 0))

        # 2. ENSUITE ON DESSINE LES SPRITES PAR DESSUS
        self.visibles_sprites.draw(self.screen)
        
        pygame.display.flip()

    def run(self):
        """C'est la boucle principale du jeu"""

        while True:
            #On commence par la gestion de la fermeture de la fenetre
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
            
            #On appelle les deux fonction qui font tourner globalement le jeu
            self.update()
            self.draw()

            #Et on limite le jeu a 60fps
            self.clock.tick(FPS)

#LANCEMENT DU JEU##########################################################################

if __name__ == '__main__':
    game = Game()
    game.run()