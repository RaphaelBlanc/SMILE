#SECTION IMPORT #######################################################################

import pygame #moteur graphique
import sys 
from pytmx.util_pygame import load_pygame #pour la map tmx
from player import Player


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
        self.is_paused = False # Par défaut, le jeu n'est pas en pause

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

    def update(self):
        if not self.is_paused:
            self.player.update(self.obstacle_sprites)
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
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
                # GESTION TOUCHE ECHAP (PAUSE)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        # On inverse l'état (Vrai devient Faux, Faux devient Vrai)
                        self.is_paused = not self.is_paused
                
                # GESTION CLICS SI MENU OUVERT
                if self.is_paused:
                    action = self.menu.handle_input(event)
                    if action == "play":
                        self.is_paused = False # On reprend le jeu
                    if action == "quit":
                        pygame.quit()
                        sys.exit()

            self.update()
            self.draw()
            self.clock.tick(FPS)


#CLASS DIALOGUE BOX########################################################################

class DialogueBox:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont("Arial", 30) # Police un peu plus grande
        self.visible = False
        self.text = ""
        
        # Dimensions de la boîte (centrée en bas)
        self.box_width = 800
        self.box_height = 150
        # On centre la boite horizontalement, et on la met en bas
        x_pos = (SCREEN_WIDTH - self.box_width) // 2
        y_pos = SCREEN_HEIGHT - self.box_height - 50 
        
        self.rect = pygame.Rect(x_pos, y_pos, self.box_width, self.box_height)

    def show(self, text):
        self.text = text
        self.visible = True

    def hide(self):
        self.visible = False

    def draw(self):
        if self.visible:
            # Fond noir
            pygame.draw.rect(self.screen, BLACK, self.rect)
            # Bordure blanche
            pygame.draw.rect(self.screen, WHITE, self.rect, 4)
            
            # Texte
            text_surf = self.font.render(self.text, True, WHITE)
            text_rect = text_surf.get_rect(center=self.rect.center)
            self.screen.blit(text_surf, text_rect)

#CLASS NPC ###############################################################################

class NPC(pygame.sprite.Sprite):
    def __init__(self, pos, message, groups):
        super().__init__(groups)
        # Visuel du PNJ (Carré Bleu pour différencier du joueur rouge)
        self.image = pygame.Surface((32, 64))
        self.image.fill((0, 0, 255)) 
        self.rect = self.image.get_rect(topleft=pos)
        
        self.message = message
        self.detection_radius = 150 # Distance de détection

    def check_proximity(self, player_rect):
        # On calcule la distance entre le centre du PNJ et le centre du Joueur
        npc_center = pygame.math.Vector2(self.rect.center)
        player_center = pygame.math.Vector2(player_rect.center)
        
        distance = npc_center.distance_to(player_center)
        return distance <= self.detection_radius
    
    def update(self, player_rect, dialogue_box):
        npc_center = pygame.math.Vector2(self.rect.center)
        player_center = pygame.math.Vector2(player_rect.center)
        
        distance = npc_center.distance_to(player_center)
        
        if distance <= self.detection_radius:
            dialogue_box.show(self.message)
        else:
            # Si on est loin et que la boite affiche NOTRE message, on l'enlève
            if dialogue_box.text == self.message:
                dialogue_box.hide()

#CLASS SOUND MANAGER######################################################################
class SoundManager:
    def __init__(self):
        # Initialisation du module de son
        pygame.mixer.init()
        
        # Chargement du son (avec une sécurité si le fichier manque)
        try:
            self.jump_sound = pygame.mixer.Sound("assets/boing.wav")
            self.jump_sound.set_volume(0.2) # Règle le volume (0.0 à 1.0)
        except FileNotFoundError:
            print("Attention : Fichier son 'assets/boing.wav' introuvable.")
            self.jump_sound = None # On évite que le jeu plante si le son manque

    def play_jump(self):
        if self.jump_sound:
            self.jump_sound.play()

#CLASS MENU ###############################################################################

class Menu:
    def __init__(self, screen):
        self.screen = screen
        
        # Polices
        self.titre_font = pygame.font.SysFont("Comic Sans MS", 100)
        self.button_font = pygame.font.SysFont("Comic Sans MS", 35)
        self.sous_titre_font = pygame.font.SysFont("Comic Sans MS", 30)

        # Chargement des images (avec sécurité)
        try:
            self.smile_image = pygame.image.load("logo_jeu.png")
            # On redimensionne un peu le logo s'il est trop gros
            self.smile_image = pygame.transform.scale(self.smile_image, (200, 200))
            
            self.background_menu = pygame.image.load("background_menu.png")
            self.background_menu = pygame.transform.scale(self.background_menu, (SCREEN_WIDTH, SCREEN_HEIGHT))
        except FileNotFoundError:
            print("ERREUR : Images du menu introuvables. Vérifie les fichiers png.")
            self.smile_image = pygame.Surface((200, 200))
            self.smile_image.fill(WHITE)
            self.background_menu = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            self.background_menu.fill((50, 50, 50))

        # Création des Rectangles pour les boutons (Centrés sur l'écran)
        center_x = SCREEN_WIDTH // 2
        
        # Bouton JOUER
        self.button_play = pygame.Rect(0, 0, 250, 80)
        self.button_play.center = (center_x, SCREEN_HEIGHT // 2)
        
        # Bouton QUITTER
        self.button_quit = pygame.Rect(0, 0, 250, 80)
        self.button_quit.center = (center_x, SCREEN_HEIGHT // 2 + 120)

    def draw(self):
        # 1. Fond
        self.screen.blit(self.background_menu, (0, 0))
        
        # 2. Logo (Centré en haut)
        logo_rect = self.smile_image.get_rect(center=(SCREEN_WIDTH // 2, 200))
        self.screen.blit(self.smile_image, logo_rect)

        # 3. Titre Texte
        self.draw_text("PAUSE / MENU", self.titre_font, RED, SCREEN_WIDTH // 2, 350)

        # 4. Dessin des boutons
        pygame.draw.rect(self.screen, BLUE_MENU, self.button_play)
        pygame.draw.rect(self.screen, BLUE_MENU, self.button_quit)

        # 5. Texte des boutons
        self.draw_text("REPRENDRE", self.button_font, WHITE, self.button_play.centerx, self.button_play.centery)
        self.draw_text("QUITTER", self.button_font, WHITE, self.button_quit.centerx, self.button_quit.centery)

    def draw_text(self, text, font, color, x, y):
        text_obj = font.render(text, True, color)
        text_rect = text_obj.get_rect(center=(x, y))
        self.screen.blit(text_obj, text_rect)

    def handle_input(self, event):
        """Retourne une action ('play', 'quit' ou None) selon le clic"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Clic gauche
                mouse_pos = event.pos
                
                if self.button_play.collidepoint(mouse_pos):
                    return "play"
                if self.button_quit.collidepoint(mouse_pos):
                    return "quit"
        return None
        
#LANCEMENT DU JEU##########################################################################

if __name__ == '__main__':
    game = Game()
    game.run()



