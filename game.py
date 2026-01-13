
import pygame #moteur graphique
import sys 
from pytmx.util_pygame import load_pygame #pour la map tmx
from player import Player
from capacite import Capacite 


"""Sys permet de communiquer avec le systeme, ce qui permettra d'arreter le programme
quand on appellera pygame.quit(), notamment avec sys.exit() qui permet de kill le processus
python de maniere propre"""
#DEFINITON CONSTANTE##################################################################
"""Par convention, on ecrit le nom des constantes en majuscules"""
#ECRAN#
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1072
FPS = 60   #Pour un jeu en 60 images par seconde, fluide

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

        self.player.capacite.projectiles.draw(self.screen)

        self.draw_health_bar()
        
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

    def draw_health_bar(self):
        # Position de la barre sur l'écran
        x, y = 50, 50
        
        # Calcul de la largeur de la barre verte proportionnellement aux HP
        health_ratio = self.player.hp_current / self.player.hp_max
        current_bar_width = self.player.health_bar_length * health_ratio

        # 1. Dessiner le contour ou le fond (Rouge)
        pygame.draw.rect(self.screen, (200, 0, 0), (x, y, self.player.health_bar_length, 20))
        
        # 2. Dessiner la barre de vie actuelle (Verte)
        pygame.draw.rect(self.screen, (0, 255, 0), (x, y, current_bar_width, 20))
        
        # 3. Dessiner un cadre noir autour pour la finition
        pygame.draw.rect(self.screen, (0, 0, 0), (x, y, self.player.health_bar_length, 20), 3)

#LANCEMENT DU JEU##########################################################################
if __name__ == '__main__':
    game = Game()
    game.run()