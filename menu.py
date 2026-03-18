import pygame

# --- CONSTANTES ---
# (Idéalement à mettre dans un fichier settings.py plus tard)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE_MENU = (0, 102, 204)
BLUE_HOVER = (0, 150, 255)
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1072

class Menu:
    def __init__(self, screen):
        self.screen = screen
        
        # État interne du menu : "main" (accueil) ou "mode_selection" (choix histoire/multi)
        self.state = "main"
        
        # Polices de caractères
        self.titre_font = pygame.font.SysFont("Comic Sans MS", 100)
        self.button_font = pygame.font.SysFont("Comic Sans MS", 35)

        # Chargement des images avec sécurité (Gestion d'erreur)
        try:
            self.smile_image = pygame.image.load("logo_jeu.png").convert_alpha()
            self.smile_image = pygame.transform.scale(self.smile_image, (200, 200))
            
            self.background_menu = pygame.image.load("background_menu.png").convert()
            self.background_menu = pygame.transform.scale(self.background_menu, (SCREEN_WIDTH, SCREEN_HEIGHT))
        except (FileNotFoundError, pygame.error):
            # Fallback si les images sont absentes
            self.smile_image = pygame.Surface((200, 200))
            self.smile_image.fill(WHITE)
            self.background_menu = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            self.background_menu.fill((30, 30, 30))

        # --- DÉFINITION DES BOUTONS (Rectangles de collision) ---
        center_x = SCREEN_WIDTH // 2
        
        # Écran Principal
        self.btn_main_play = pygame.Rect(0, 0, 350, 80)
        self.btn_main_play.center = (center_x, SCREEN_HEIGHT // 2)
        
        self.btn_main_quit = pygame.Rect(0, 0, 350, 80)
        self.btn_main_quit.center = (center_x, SCREEN_HEIGHT // 2 + 120)

        # Écran Sélection Mode
        self.btn_mode_story = pygame.Rect(0, 0, 400, 80)
        self.btn_mode_story.center = (center_x, SCREEN_HEIGHT // 2 - 40)

        self.btn_mode_multi = pygame.Rect(0, 0, 400, 80)
        self.btn_mode_multi.center = (center_x, SCREEN_HEIGHT // 2 + 60)

        self.btn_mode_back = pygame.Rect(0, 0, 200, 60)
        self.btn_mode_back.center = (center_x, SCREEN_HEIGHT // 2 + 180)

    def draw_text(self, text, font, color, x, y):
        """Affiche un texte centré sur les coordonnées x, y"""
        text_obj = font.render(text, True, color)
        text_rect = text_obj.get_rect(center=(x, y))
        self.screen.blit(text_obj, text_rect)

    def draw_button(self, rect, text, color_normal, color_hover, mouse_pos):
        """Dessine un bouton avec un effet de survol (hover)"""
        color = color_hover if rect.collidepoint(mouse_pos) else color_normal
        
        # Corps du bouton
        pygame.draw.rect(self.screen, color, rect, border_radius=15)
        # Bordure blanche
        pygame.draw.rect(self.screen, WHITE, rect, 3, border_radius=15)
        # Texte du bouton
        self.draw_text(text, self.button_font, WHITE, rect.centerx, rect.centery)

    def draw(self, game_started=False):
        """Affiche le menu selon son état actuel (main ou mode_selection)"""
        # 1. Dessiner le fond
        self.screen.blit(self.background_menu, (0, 0))
        mouse_pos = pygame.mouse.get_pos()

        if self.state == "main":
            # --- LOGO & TITRE ---
            logo_rect = self.smile_image.get_rect(center=(SCREEN_WIDTH // 2, 200))
            self.screen.blit(self.smile_image, logo_rect)
            
            titre_texte = "PAUSE" if game_started else "SMILE"
            self.draw_text(titre_texte, self.titre_font, RED, SCREEN_WIDTH // 2, 350)

            # --- BOUTONS ---
            btn_play_text = "REPRENDRE" if game_started else "JOUER"
            self.draw_button(self.btn_main_play, btn_play_text, BLUE_MENU, BLUE_HOVER, mouse_pos)
            self.draw_button(self.btn_main_quit, "QUITTER", BLUE_MENU, (200, 0, 0), mouse_pos)

        elif self.state == "mode_selection":
            # --- TITRE SÉLECTION ---
            self.draw_text("CHOISIR UN MODE", self.titre_font, WHITE, SCREEN_WIDTH // 2, 250)

            # --- BOUTONS MODES ---
            self.draw_button(self.btn_mode_story, "MODE HISTOIRE", BLUE_MENU, BLUE_HOVER, mouse_pos)
            self.draw_button(self.btn_mode_multi, "MULTIJOUEUR", BLUE_MENU, BLUE_HOVER, mouse_pos)
            self.draw_button(self.btn_mode_back, "RETOUR", (100, 100, 100), (150, 150, 150), mouse_pos)

    def handle_input(self, event):
        """Gère les clics de souris et renvoie l'action au programme principal"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            
            # Clics sur le Menu Principal
            if self.state == "main":
                if self.btn_main_play.collidepoint(event.pos):
                    return "open_modes" # Action interceptée par main.py
                if self.btn_main_quit.collidepoint(event.pos):
                    return "quit"

            # Clics sur la Sélection de Mode
            elif self.state == "mode_selection":
                if self.btn_mode_story.collidepoint(event.pos):
                    self.state = "main" # On reset l'état pour la prochaine pause
                    return "play_story"
                
                if self.btn_mode_multi.collidepoint(event.pos):
                    self.state = "main"
                    return "play_multi"
                
                if self.btn_mode_back.collidepoint(event.pos):
                    self.state = "main" # Retour au menu précédent
                    
        return None