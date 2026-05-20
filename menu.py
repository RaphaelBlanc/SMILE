import pygame
import cv2
import sys

# --- CONFIGURATION ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE_MENU = (0, 102, 204)
BLUE_HOVER = (0, 150, 255)
GREY = (100, 100, 100)

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1072

class Menu:
    def __init__(self, screen):
        self.screen = screen
        self.state = "main"
        
        # Polices
        self.titre_font = pygame.font.SysFont("Comic Sans MS", 100)
        self.button_font = pygame.font.SysFont("Comic Sans MS", 35)

        # --- CHARGEMENT DU LOGO ---
        try:
            self.smile_image = pygame.image.load("assets/swappy-20260318-204350.png").convert_alpha()
            nouvelle_largeur = 500
            ratio = self.smile_image.get_width() / self.smile_image.get_height()
            nouvelle_hauteur = int(nouvelle_largeur / ratio)
            self.smile_image = pygame.transform.scale(self.smile_image, (nouvelle_largeur, nouvelle_hauteur))
        except (FileNotFoundError, pygame.error):
            self.smile_image = pygame.Surface((500, 500))
            self.smile_image.fill(WHITE)

        # --- VIDÉO DE FOND ---
        self.video_path = "assets/videofondmenu.mp4"
        self.video_capture = cv2.VideoCapture(self.video_path)
        self.video_loaded = self.video_capture.isOpened()
        self.background_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

        # --- BOUTONS ---
        center_x = SCREEN_WIDTH // 2
        self.btn_play = pygame.Rect(0, 0, 400, 80)
        self.btn_play.center = (center_x, SCREEN_HEIGHT // 2 - 80)
        
        self.btn_settings = pygame.Rect(0, 0, 400, 80)
        self.btn_settings.center = (center_x, SCREEN_HEIGHT // 2 + 40)
        
        self.btn_quit = pygame.Rect(0, 0, 400, 80)
        self.btn_quit.center = (center_x, SCREEN_HEIGHT // 2 + 160)

        self.btn_mode_story = pygame.Rect(0, 0, 450, 80)
        self.btn_mode_story.center = (center_x, SCREEN_HEIGHT // 2 - 40)
        self.btn_mode_multi = pygame.Rect(0, 0, 450, 80)
        self.btn_mode_multi.center = (center_x, SCREEN_HEIGHT // 2 + 60)

        self.btn_back = pygame.Rect(0, 0, 250, 60)
        self.btn_back.center = (center_x, SCREEN_HEIGHT // 2 + 250)

    def update_video(self):
        if self.video_loaded:
            success, frame = self.video_capture.read()
            if not success:
                self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                success, frame = self.video_capture.read()
            if success:
                frame = cv2.resize(frame, (SCREEN_WIDTH, SCREEN_HEIGHT))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = frame.transpose(1, 0, 2)
                self.background_surface = pygame.surfarray.make_surface(frame)

    def draw_text(self, text, font, color, x, y):
        text_obj = font.render(text, True, color)
        text_rect = text_obj.get_rect(center=(x, y))
        self.screen.blit(text_obj, text_rect)

    def draw_button(self, rect, text, color_normal, color_hover, mouse_pos):
        color = color_hover if rect.collidepoint(mouse_pos) else color_normal
        pygame.draw.rect(self.screen, color, rect, border_radius=15)
        pygame.draw.rect(self.screen, WHITE, rect, 3, border_radius=15)
        self.draw_text(text, self.button_font, WHITE, rect.centerx, rect.centery)

    def draw(self, game_started=False):
        # 1. Fond Vidéo
        self.update_video()
        self.screen.blit(self.background_surface, (0, 0))
        
        mouse_pos = pygame.mouse.get_pos()

        # 2. Logo (Haut Droite)
        logo_x = SCREEN_WIDTH - self.smile_image.get_width()
        self.screen.blit(self.smile_image, (logo_x, 0))

        # 3. Affichage Main
        if self.state == "main":
            # --- VERIFICATION DU TITRE ---
            if game_started:
                self.draw_text("PAUSE", self.titre_font, RED, SCREEN_WIDTH // 2, 320)
                btn_text = "REPRENDRE"
            else:
                self.draw_text("SMILE", self.titre_font, RED, SCREEN_WIDTH // 2, 320)
                btn_text = "JOUER"

            self.draw_button(self.btn_play, btn_text, BLUE_MENU, BLUE_HOVER, mouse_pos)
            self.draw_button(self.btn_settings, "PARAMETRES", BLUE_MENU, BLUE_HOVER, mouse_pos)
            self.draw_button(self.btn_quit, "QUITTER", BLUE_MENU, (200, 0, 0), mouse_pos)

        elif self.state == "mode_selection":
            self.draw_text("CHOISIR UN MODE", self.titre_font, WHITE, SCREEN_WIDTH // 2, 250)
            self.draw_button(self.btn_mode_story, "MODE HISTOIRE", BLUE_MENU, BLUE_HOVER, mouse_pos)
            self.draw_button(self.btn_mode_multi, "MULTIJOUEUR", BLUE_MENU, BLUE_HOVER, mouse_pos)
            self.draw_button(self.btn_back, "RETOUR", GREY, WHITE, mouse_pos)

        elif self.state == "settings":
            self.draw_text("PARAMETRES", self.titre_font, WHITE, SCREEN_WIDTH // 2, 250)
            self.draw_button(self.btn_back, "RETOUR", GREY, WHITE, mouse_pos)

    def handle_input(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.state == "main":
                if self.btn_play.collidepoint(event.pos): return "open_modes"
                if self.btn_settings.collidepoint(event.pos): self.state = "settings"
                if self.btn_quit.collidepoint(event.pos): return "quit"
            elif self.state == "mode_selection":
                if self.btn_mode_story.collidepoint(event.pos): return "play_story"
                if self.btn_mode_multi.collidepoint(event.pos): return "play_multi"
                if self.btn_back.collidepoint(event.pos): self.state = "main"
            elif self.state == "settings":
                if self.btn_back.collidepoint(event.pos): self.state = "main"
        return None