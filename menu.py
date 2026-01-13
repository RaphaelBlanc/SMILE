import pygame

# Import des constantes nécessaires au dessin
# Si tu préfères, tu peux aussi les passer en paramètres
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE_MENU = (0, 102, 204)
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1072

class Menu:
    def __init__(self, screen):
        self.screen = screen
        
        # Polices
        self.titre_font = pygame.font.SysFont("Comic Sans MS", 100)
        self.button_font = pygame.font.SysFont("Comic Sans MS", 35)

        # Chargement des images avec sécurité
        try:
            self.smile_image = pygame.image.load("logo_jeu.png")
            self.smile_image = pygame.transform.scale(self.smile_image, (200, 200))
            
            self.background_menu = pygame.image.load("background_menu.png")
            self.background_menu = pygame.transform.scale(self.background_menu, (SCREEN_WIDTH, SCREEN_HEIGHT))
        except FileNotFoundError:
            print("INFO : Images du menu manquantes, utilisation de surfaces colorées.")
            self.smile_image = pygame.Surface((200, 200))
            self.smile_image.fill(WHITE)
            self.background_menu = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            self.background_menu.fill((50, 50, 50))

        # Création des Rectangles pour les boutons
        center_x = SCREEN_WIDTH // 2
        self.button_play = pygame.Rect(0, 0, 250, 80)
        self.button_play.center = (center_x, SCREEN_HEIGHT // 2)
        
        self.button_quit = pygame.Rect(0, 0, 250, 80)
        self.button_quit.center = (center_x, SCREEN_HEIGHT // 2 + 120)

    def draw_text(self, text, font, color, x, y):
        text_obj = font.render(text, True, color)
        text_rect = text_obj.get_rect(center=(x, y))
        self.screen.blit(text_obj, text_rect)

    def draw(self):
        # 1. Fond
        self.screen.blit(self.background_menu, (0, 0))
        
        # 2. Logo
        logo_rect = self.smile_image.get_rect(center=(SCREEN_WIDTH // 2, 200))
        self.screen.blit(self.smile_image, logo_rect)

        # 3. Titre
        self.draw_text("PAUSE / MENU", self.titre_font, RED, SCREEN_WIDTH // 2, 350)

        # 4. Dessin des boutons
        pygame.draw.rect(self.screen, BLUE_MENU, self.button_play, border_radius=12)
        pygame.draw.rect(self.screen, BLUE_MENU, self.button_quit, border_radius=12)

        # 5. Texte des boutons
        self.draw_text("REPRENDRE", self.button_font, WHITE, self.button_play.centerx, self.button_play.centery)
        self.draw_text("QUITTER", self.button_font, WHITE, self.button_quit.centerx, self.button_quit.centery)

    def handle_input(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Clic gauche
                if self.button_play.collidepoint(event.pos):
                    return "play"
                if self.button_quit.collidepoint(event.pos):
                    return "quit"
        return None