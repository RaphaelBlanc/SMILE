#SECTION IMPORT #######################################################################

import pygame #moteur graphique
import sys 
from pytmx.util_pygame import load_pygame #pour la map tmx
from player import Player
from son import SoundManager
from menu import Menu
from npc import NPC
from npc import DialogueBox


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

        # --- ETAT DU JEU (NOUVEAU) ---
        self.is_paused = True   # commencer jeu en pause pour avoir un menu 
        self.game_started = False # pour differencier 

        # --- GESTIONNAIRE DE SON ---
        self.sound_manager = SoundManager()
        self.menu = Menu(self.screen) # On initialise le menu
        
        #CREATION GROUPES DE SPRITES
        #Visibles
        self.visibles_sprites = pygame.sprite.Group()
        #Obstable
        self.obstacle_sprites = pygame.sprite.Group()

        self.npc_sprites = pygame.sprite.Group()

        # --- UI DIALOGUE ---
        self.dialogue_box = DialogueBox(self.screen) # Création de l'interface


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
            pos = (x * 32, y * 32) 
            
            # On crée un mur à cet endroit et on l'ajoute aux groupes
            Tile(pos, surf, [self.obstacle_sprites])

        # --- CREATION D'UN PNJ TEST ---
        # Je le place un peu plus loin, à 600px en X
        self.pnj1 = NPC((600, 500), "Salut Voyageur ! Attention aux trous !", [self.visibles_sprites, self.npc_sprites])


        # --- CREATION DU JOUEUR ---
        self.player = Player((200, 200), self.sound_manager) # Position de départ arbitraire
        self.visibles_sprites.add(self.player) # On l'ajoute au groupe visible

    def update(self,dt):
        if not self.is_paused:
            self.player.update(self.obstacle_sprites, dt)
            for npc in self.npc_sprites:
                npc.update(self.player.rect, self.dialogue_box)

    def draw_health_bar(self):
        """Dessine la barre de vie en haut à gauche"""
        x, y = 50, 50
        health_ratio = self.player.hp_current / self.player.hp_max
        current_bar_width = self.player.health_bar_length * health_ratio

        # Fond (rouge)
        pygame.draw.rect(self.screen, RED, (x, y, self.player.health_bar_length, 20))
        # Vie actuelle (verte)
        pygame.draw.rect(self.screen, GREEN, (x, y, current_bar_width, 20))
        # Cadre (noir)
        pygame.draw.rect(self.screen, BLACK, (x, y, self.player.health_bar_length, 20), 3)

    def draw(self):
        if self.is_paused:
            self.menu.draw()
        else:
            self.screen.blit(self.background_image, (0, 0))
            self.visibles_sprites.draw(self.screen)
            
            # --- DESSIN DES PROJECTILES ---
            # Les projectiles sont stockés dans la "Capacite" du joueur
            self.player.capacite.projectiles.draw(self.screen)
            
            # --- DESSIN DE L'UI ---
            self.dialogue_box.draw()
            self.draw_health_bar()
        
        pygame.display.flip()

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
                # 1. Gestion de la touche ECHAP
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    if self.game_started: # On ne peut toggle la pause que si le jeu a commencé
                        self.is_paused = not self.is_paused
                
                # 2. Gestion du MENU (Seulement si en pause)
                if self.is_paused:
                    # CRITIQUE : Il faut stocker le retour de handle_input
                    action = self.menu.handle_input(event)

                    if action == "open_modes":
                        if self.game_started:
                            self.is_paused = False # Reprise simple si déjà en jeu
                        else:
                            self.menu.state = "mode_selection" # Change l'affichage interne du menu
            
                    elif action == "play_story":
                        print("Mode Histoire lancé !") # Pour vérifier dans la console
                        self.game_started = True
                        self.is_paused = False
        
                    elif action == "play_multi":
                        print("Mode Multi lancé !")
                        self.game_started = True
                        self.is_paused = False

                    elif action == "quit":
                        pygame.quit()
                        sys.exit()

            # Mise à jour et dessin
            if not self.is_paused and self.game_started:
                self.update(dt)
            
            self.draw()

#LANCEMENT DU JEU##########################################################################

if __name__ == '__main__':
    game = Game()
    game.run()



