import pygame
import cv2
import sys
import os
from config import ROOT_DIR

# --- CONFIGURATION ---
WHITE      = (255, 255, 255)
BLACK      = (0,   0,   0)
RED        = (255, 0,   0)
BLUE_MENU  = (0,   102, 204)
BLUE_HOVER = (0,   150, 255)
GREY       = (100, 100, 100)
GREEN      = (0,   200, 80)
YELLOW     = (255, 220, 60)

SCREEN_WIDTH  = 1920
SCREEN_HEIGHT = 1072

class Menu:
    def __init__(self, screen):
        self.screen = screen
        # États possibles :
        #   main | mode_selection | settings
        #   multi_lobby       → choisir host ou client
        #   multi_host_wait   → host attend que l'ami rejoigne
        #   multi_join_input  → client tape le code
        #   multi_join_wait   → client attend confirmation
        self.state = "main"

        # Polices
        self.titre_font  = pygame.font.SysFont("Comic Sans MS", 100)
        self.button_font = pygame.font.SysFont("Comic Sans MS", 35)
        self.code_font   = pygame.font.SysFont("Consolas",      60, bold=True)
        self.small_font  = pygame.font.SysFont("Comic Sans MS", 28)

        # --- LOGO ---
        try:
            self.smile_image = pygame.image.load(os.path.join(ROOT_DIR, "assets/images/swappy-20260318-204350.png")).convert_alpha()
            nouvelle_largeur = 500
            ratio = self.smile_image.get_width() / self.smile_image.get_height()
            self.smile_image = pygame.transform.scale(
                self.smile_image, (nouvelle_largeur, int(nouvelle_largeur / ratio)))
        except (FileNotFoundError, pygame.error):
            self.smile_image = pygame.Surface((500, 500))
            self.smile_image.fill(WHITE)

        # --- VIDÉO DE FOND ---
        self.video_path    = os.path.join(ROOT_DIR, "assets/video/videofondmenu.mp4")
        self.video_capture = cv2.VideoCapture(self.video_path)
        self.video_loaded  = self.video_capture.isOpened()
        self.background_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

        # --- SAISIE CODE (client) ---
        self.input_code   = ""          # texte tapé par le client
        self.input_active = False
        self.input_error  = ""          # message d'erreur éventuel

        center_x = SCREEN_WIDTH // 2

        # ── Boutons menu principal ──────────────────────────────────
        self.btn_play     = self._btn(center_x, SCREEN_HEIGHT // 2 - 80,  400, 80)
        self.btn_settings = self._btn(center_x, SCREEN_HEIGHT // 2 + 40,  400, 80)
        self.btn_quit     = self._btn(center_x, SCREEN_HEIGHT // 2 + 160, 400, 80)

        # ── Boutons sélection de mode ───────────────────────────────
        self.btn_mode_story = self._btn(center_x, SCREEN_HEIGHT // 2 - 40,  450, 80)
        self.btn_mode_multi = self._btn(center_x, SCREEN_HEIGHT // 2 + 60,  450, 80)
        self.btn_back       = self._btn(center_x, SCREEN_HEIGHT // 2 + 250, 250, 60)

        # ── Boutons sauvegardes ─────────────────────────────────────
        self.btn_save_1     = self._btn(center_x, SCREEN_HEIGHT // 2 - 100, 400, 80)
        self.btn_save_2     = self._btn(center_x, SCREEN_HEIGHT // 2 + 0,   400, 80)
        self.btn_save_3     = self._btn(center_x, SCREEN_HEIGHT // 2 + 100, 400, 80)
        self.btn_back_save  = self._btn(center_x, SCREEN_HEIGHT // 2 + 250, 250, 60)

        # ── Boutons lobby multi ─────────────────────────────────────
        self.btn_host       = self._btn(center_x, SCREEN_HEIGHT // 2 - 50,  400, 80)
        self.btn_join       = self._btn(center_x, SCREEN_HEIGHT // 2 + 70,  400, 80)
        self.btn_back_lobby = self._btn(center_x, SCREEN_HEIGHT // 2 + 250, 250, 60)

        # Zone de saisie du code (client)
        self.input_rect = pygame.Rect(0, 0, 400, 80)
        self.input_rect.center = (center_x, SCREEN_HEIGHT // 2 + 20)

        self.btn_confirm_code = self._btn(center_x, SCREEN_HEIGHT // 2 + 130, 300, 70)
        self.btn_back_join    = self._btn(center_x, SCREEN_HEIGHT // 2 + 250, 250, 60)

        # ── Slider volume (paramètres) ──────────────────────────────
        self.volume           = 1.0          # 0.0 → 1.0
        slider_w              = 500
        self.slider_rect      = pygame.Rect(center_x - slider_w // 2,
                                            SCREEN_HEIGHT // 2 + 20,
                                            slider_w, 12)
        self.slider_handle_r  = 18           # rayon de la poignée
        self.slider_dragging  = False
        self.btn_back_settings         = self._btn(center_x, SCREEN_HEIGHT // 2 + 200, 250, 60)
        # Bouton retour spécifique à l'onglet keybinds (en bas de la liste des touches)
        keybinds_back_y = self.keybind_list_y if hasattr(self, 'keybind_list_y') else 400
        self.btn_back_settings_keybinds = self._btn(center_x, 970, 250, 60)

        # ── Onglets paramètres ──────────────────────────────────────
        # "volume" ou "keybinds"
        self.settings_tab = "volume"
        tab_y = 340
        self.btn_tab_volume   = self._btn(center_x - 160, tab_y, 280, 55)
        self.btn_tab_keybinds = self._btn(center_x + 160, tab_y, 280, 55)

        # ── Touches configurables ───────────────────────────────────
        self.keybinds = {
            "move_left":  pygame.K_q,
            "move_right": pygame.K_d,
            "move_up":    pygame.K_z,
            "move_down":  pygame.K_s,
            "jump":       pygame.K_SPACE,
            "sprint":     pygame.K_LSHIFT,
            "attack":     pygame.K_f,
            "dash":       pygame.K_v,
        }
        # Labels lisibles pour chaque action
        self.keybind_labels = {
            "move_left":  "Aller à gauche",
            "move_right": "Aller à droite",
            "move_up":    "Monter / Echelle",
            "move_down":  "Descendre / Front",
            "jump":       "Sauter",
            "sprint":     "Sprint",
            "attack":     "Attaque",
            "dash":       "Dash",
        }
        # Quelle action est en attente d'une nouvelle touche (None = aucune)
        self.rebinding_action    = None
        self.keybind_list_y      = 400     # Y de départ de la liste
        self.keybind_row_h       = 62      # hauteur d'une ligne
        # Rect de chaque bouton "rebind" (reconstruit à chaque draw)
        self.keybind_btn_rects   = {}

    # ── Helpers ────────────────────────────────────────────────────

    @staticmethod
    def _btn(cx, cy, w, h):
        r = pygame.Rect(0, 0, w, h)
        r.center = (cx, cy)
        return r

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
        surf = font.render(text, True, color)
        self.screen.blit(surf, surf.get_rect(center=(x, y)))

    def draw_button(self, rect, text, color_normal, color_hover, mouse_pos):
        color = color_hover if rect.collidepoint(mouse_pos) else color_normal
        pygame.draw.rect(self.screen, color, rect, border_radius=15)
        pygame.draw.rect(self.screen, WHITE,  rect, 3, border_radius=15)
        self.draw_text(text, self.button_font, WHITE, rect.centerx, rect.centery)

    # ── Draw principal ─────────────────────────────────────────────

    def draw(self, game_started=False, network=None):
        self.update_video()
        self.screen.blit(self.background_surface, (0, 0))
        mouse_pos = pygame.mouse.get_pos()

        # Logo haut-droite
        self.screen.blit(self.smile_image,
                         (SCREEN_WIDTH - self.smile_image.get_width(), 0))

        cx = SCREEN_WIDTH // 2

        # ── Menu principal ──────────────────────────────────────────
        if self.state == "main":
            if game_started:
                self.draw_text("PAUSE",    self.titre_font, RED, cx, 320)
                btn_text = "REPRENDRE"
                btn_quit_text = "MENU PRINCIPAL"
            else:
                self.draw_text("SMILE",    self.titre_font, RED, cx, 320)
                btn_text = "JOUER"
                btn_quit_text = "QUITTER"
            self.draw_button(self.btn_play,     btn_text,     BLUE_MENU, BLUE_HOVER, mouse_pos)
            self.draw_button(self.btn_settings, "PARAMETRES", BLUE_MENU, BLUE_HOVER, mouse_pos)
            self.draw_button(self.btn_quit,     btn_quit_text,    BLUE_MENU, (200, 0, 0), mouse_pos)

        # ── Sélection de mode ───────────────────────────────────────
        elif self.state == "mode_selection":
            self.draw_text("CHOISIR UN MODE", self.titre_font, WHITE, cx, 250)
            self.draw_button(self.btn_mode_story, "MODE HISTOIRE", BLUE_MENU, BLUE_HOVER, mouse_pos)
            self.draw_button(self.btn_mode_multi, "MULTIJOUEUR",   BLUE_MENU, BLUE_HOVER, mouse_pos)
            self.draw_button(self.btn_back,       "RETOUR",        GREY,      WHITE,      mouse_pos)

        # ── Sélection de sauvegarde ─────────────────────────────────
        elif self.state == "save_selection":
            self.draw_text("CHOISIR UNE SAUVEGARDE", self.titre_font, WHITE, cx, 250)
            self.draw_button(self.btn_save_1, "SAUVEGARDE 1", BLUE_MENU, BLUE_HOVER, mouse_pos)
            self.draw_button(self.btn_save_2, "SAUVEGARDE 2", BLUE_MENU, BLUE_HOVER, mouse_pos)
            self.draw_button(self.btn_save_3, "SAUVEGARDE 3", BLUE_MENU, BLUE_HOVER, mouse_pos)
            self.draw_button(self.btn_back_save, "RETOUR", GREY, WHITE, mouse_pos)

        # ── Paramètres ──────────────────────────────────────────────
        elif self.state == "settings":
            self.draw_text("PARAMETRES", self.titre_font, WHITE, cx, 250)

            # ── Onglets ─────────────────────────────────────────────
            for btn, label, tab in [
                (self.btn_tab_volume,   "VOLUME",  "volume"),
                (self.btn_tab_keybinds, "TOUCHES", "keybinds"),
            ]:
                active   = (self.settings_tab == tab)
                bg_color = BLUE_HOVER if active else BLUE_MENU
                border   = YELLOW if active else WHITE
                pygame.draw.rect(self.screen, bg_color, btn, border_radius=12)
                pygame.draw.rect(self.screen, border,   btn, 3, border_radius=12)
                self.draw_text(label, self.button_font, WHITE, btn.centerx, btn.centery)

            # ── Contenu : Volume ─────────────────────────────────────
            if self.settings_tab == "volume":
                self.draw_text("VOLUME", self.button_font, WHITE, cx, SCREEN_HEIGHT // 2 - 60)

                pygame.draw.rect(self.screen, GREY, self.slider_rect, border_radius=6)
                filled_w    = int(self.slider_rect.width * self.volume)
                filled_rect = pygame.Rect(self.slider_rect.x, self.slider_rect.y,
                                          filled_w, self.slider_rect.height)
                pygame.draw.rect(self.screen, BLUE_MENU, filled_rect, border_radius=6)

                handle_x = self.slider_rect.x + filled_w
                handle_y = self.slider_rect.centery
                pygame.draw.circle(self.screen, WHITE,     (handle_x, handle_y), self.slider_handle_r)
                pygame.draw.circle(self.screen, BLUE_HOVER,(handle_x, handle_y), self.slider_handle_r, 3)

                pct_text = f"{int(self.volume * 100)} %"
                self.draw_text(pct_text, self.button_font, YELLOW, cx,
                               self.slider_rect.bottom + 45)

            # ── Contenu : Touches ────────────────────────────────────
            elif self.settings_tab == "keybinds":
                actions = list(self.keybinds.keys())
                self.keybind_btn_rects = {}

                for i, action in enumerate(actions):
                    row_y    = self.keybind_list_y + i * self.keybind_row_h
                    label    = self.keybind_labels[action]
                    key_name = pygame.key.name(self.keybinds[action]).upper()

                    # Fond de ligne alterné
                    row_rect = pygame.Rect(cx - 480, row_y - 24, 960, self.keybind_row_h - 6)
                    bg = (30, 30, 60) if i % 2 == 0 else (20, 20, 45)
                    pygame.draw.rect(self.screen, bg, row_rect, border_radius=8)

                    # Label action (à gauche)
                    self.draw_text(label, self.small_font, WHITE, cx - 180, row_y)

                    # Bouton touche (à droite)
                    btn_r = pygame.Rect(0, 0, 220, 44)
                    btn_r.center = (cx + 280, row_y)
                    self.keybind_btn_rects[action] = btn_r

                    if self.rebinding_action == action:
                        pygame.draw.rect(self.screen, YELLOW, btn_r, border_radius=10)
                        pygame.draw.rect(self.screen, WHITE,  btn_r, 2, border_radius=10)
                        self.draw_text("APPUIE...", self.small_font, BLACK, btn_r.centerx, btn_r.centery)
                    else:
                        col = BLUE_HOVER if btn_r.collidepoint(mouse_pos) else BLUE_MENU
                        pygame.draw.rect(self.screen, col,   btn_r, border_radius=10)
                        pygame.draw.rect(self.screen, WHITE, btn_r, 2, border_radius=10)
                        self.draw_text(key_name, self.small_font, WHITE, btn_r.centerx, btn_r.centery)

                # Hint ESC pour annuler
                if self.rebinding_action:
                    self.draw_text("ESC pour annuler", self.small_font, RED, cx,
                                   self.keybind_list_y + len(actions) * self.keybind_row_h + 10)

            btn_back = self.btn_back_settings_keybinds if self.settings_tab == "keybinds" else self.btn_back_settings
            self.draw_button(btn_back, "RETOUR", GREY, WHITE, mouse_pos)

        # ── Lobby multi : choisir host ou client ────────────────────
        elif self.state == "multi_lobby":
            self.draw_text("MULTIJOUEUR", self.titre_font, WHITE, cx, 250)
            self.draw_button(self.btn_host,       "CREER UN SALON", BLUE_MENU, BLUE_HOVER, mouse_pos)
            self.draw_button(self.btn_join,       "REJOINDRE",      BLUE_MENU, BLUE_HOVER, mouse_pos)
            self.draw_button(self.btn_back_lobby, "RETOUR",         GREY,      WHITE,      mouse_pos)

        # ── Host attend l'ami ────────────────────────────────────────
        elif self.state == "multi_host_wait":
            self.draw_text("EN ATTENTE D'UN JOUEUR", self.titre_font, WHITE, cx, 220)

            if network and network.error:
                self.draw_text(f"ERREUR : {network.error}", self.small_font, RED, cx, 360)
            elif network and network.session_code:
                self.draw_text("Donne ce code à ton ami :", self.small_font, WHITE, cx, 360)
                # Encadré code
                code_rect = pygame.Rect(0, 0, 420, 100)
                code_rect.center = (cx, 460)
                pygame.draw.rect(self.screen, (20, 20, 60), code_rect, border_radius=12)
                pygame.draw.rect(self.screen, YELLOW, code_rect, 4, border_radius=12)
                self.draw_text(network.session_code, self.code_font, YELLOW, cx, 460)
                self.draw_text("En attente de connexion...", self.small_font, WHITE, cx, 560)
            else:
                self.draw_text("Connexion au serveur...", self.small_font, WHITE, cx, 400)

            self.draw_button(self.btn_back_lobby, "ANNULER", GREY, WHITE, mouse_pos)

        # ── Client saisit le code ────────────────────────────────────
        elif self.state == "multi_join_input":
            self.draw_text("REJOINDRE UN SALON", self.titre_font, WHITE, cx, 220)
            self.draw_text("Entrez le code du salon :", self.small_font, WHITE, cx, 360)

            # Zone de saisie
            border_color = BLUE_HOVER if self.input_active else GREY
            pygame.draw.rect(self.screen, (20, 20, 60), self.input_rect, border_radius=10)
            pygame.draw.rect(self.screen, border_color, self.input_rect, 3, border_radius=10)
            display = self.input_code if self.input_code else "_ _ _ _"
            self.draw_text(display, self.code_font, WHITE, cx, self.input_rect.centery)

            if self.input_error:
                self.draw_text(self.input_error, self.small_font, RED, cx,
                               self.input_rect.bottom + 25)

            self.draw_button(self.btn_confirm_code, "CONFIRMER", GREEN,  BLUE_HOVER, mouse_pos)
            self.draw_button(self.btn_back_join,    "RETOUR",    GREY,   WHITE,      mouse_pos)

        # ── Client attend confirmation ───────────────────────────────
        elif self.state == "multi_join_wait":
            self.draw_text("CONNEXION EN COURS...", self.titre_font, WHITE, cx, 300)
            if network and network.error:
                self.draw_text(f"ERREUR : {network.error}", self.small_font, RED, cx, 420)
                self.draw_button(self.btn_back_lobby, "RETOUR", GREY, WHITE, mouse_pos)
            else:
                self.draw_text("En attente de l'hôte...", self.small_font, WHITE, cx, 420)

    # ── Gestion des événements ─────────────────────────────────────

    def handle_input(self, event, network=None):
        """
        Retourne une action string ou None.
        Actions possibles :
            open_modes | play_story | play_multi | quit
            multi_create_session | multi_join_session
        """
        mouse_pos = pygame.mouse.get_pos()

        # Saisie clavier pour le code (état multi_join_input)
        if self.state == "multi_join_input" and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                return self._try_join(network)
            elif event.key == pygame.K_BACKSPACE:
                self.input_code = self.input_code[:-1]
            elif event.unicode.isalnum() and len(self.input_code) < 8:
                self.input_code += event.unicode.upper()
            return None

        # ── Slider volume : clic + drag ─────────────────────────────
        if self.state == "settings" and self.settings_tab == "volume":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                hx = self.slider_rect.x + int(self.slider_rect.width * self.volume)
                hy = self.slider_rect.centery
                dist = ((event.pos[0] - hx) ** 2 + (event.pos[1] - hy) ** 2) ** 0.5
                if dist <= self.slider_handle_r + 4 or self.slider_rect.collidepoint(event.pos):
                    self.slider_dragging = True
                    self._update_slider(event.pos[0])
                    return ("volume_changed", self.volume)

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.slider_dragging = False

            elif event.type == pygame.MOUSEMOTION and self.slider_dragging:
                self._update_slider(event.pos[0])
                return ("volume_changed", self.volume)

        # ── Keybinds : capture de touche ────────────────────────────
        if self.state == "settings" and self.settings_tab == "keybinds":
            if self.rebinding_action and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.rebinding_action = None
                else:
                    self.keybinds[self.rebinding_action] = event.key
                    self.rebinding_action = None
                return ("keybinds_changed", self.keybinds)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:

            # Activer/désactiver la zone de saisie
            if self.state == "multi_join_input":
                self.input_active = self.input_rect.collidepoint(event.pos)

            # ── main ────────────────────────────────────────────────
            if self.state == "main":
                if self.btn_play.collidepoint(event.pos):     return "open_modes"
                if self.btn_settings.collidepoint(event.pos): self.state = "settings"
                if self.btn_quit.collidepoint(event.pos):     return "quit"

            # ── mode_selection ──────────────────────────────────────
            elif self.state == "mode_selection":
                if self.btn_mode_story.collidepoint(event.pos): self.state = "save_selection"
                if self.btn_mode_multi.collidepoint(event.pos): self.state = "multi_lobby"
                if self.btn_back.collidepoint(event.pos):       self.state = "main"

            # ── save_selection ──────────────────────────────────────
            elif self.state == "save_selection":
                if self.btn_save_1.collidepoint(event.pos): return "play_story"
                if self.btn_save_2.collidepoint(event.pos): return "play_story"
                if self.btn_save_3.collidepoint(event.pos): return "play_story"
                if self.btn_back_save.collidepoint(event.pos): self.state = "mode_selection"

            # ── settings ────────────────────────────────────────────
            elif self.state == "settings":
                # Changer d'onglet
                if self.btn_tab_volume.collidepoint(event.pos):
                    self.settings_tab     = "volume"
                    self.rebinding_action = None
                elif self.btn_tab_keybinds.collidepoint(event.pos):
                    self.settings_tab     = "keybinds"
                # Bouton rebind dans la liste des touches
                elif self.settings_tab == "keybinds":
                    for action, btn_r in self.keybind_btn_rects.items():
                        if btn_r.collidepoint(event.pos):
                            self.rebinding_action = action
                            break
                if self.btn_back_settings.collidepoint(event.pos) or self.btn_back_settings_keybinds.collidepoint(event.pos):
                    self.rebinding_action = None
                    self.state = "main"

            # ── multi_lobby ─────────────────────────────────────────
            elif self.state == "multi_lobby":
                if self.btn_host.collidepoint(event.pos):
                    self.state = "multi_host_wait"
                    return "multi_create_session"
                if self.btn_join.collidepoint(event.pos):
                    self.input_code  = ""
                    self.input_error = ""
                    self.input_active = True
                    self.state = "multi_join_input"
                if self.btn_back_lobby.collidepoint(event.pos):
                    self.state = "mode_selection"

            # ── multi_host_wait ─────────────────────────────────────
            elif self.state == "multi_host_wait":
                if self.btn_back_lobby.collidepoint(event.pos):
                    self.state = "multi_lobby"

            # ── multi_join_input ────────────────────────────────────
            elif self.state == "multi_join_input":
                if self.btn_confirm_code.collidepoint(event.pos):
                    return self._try_join(network)
                if self.btn_back_join.collidepoint(event.pos):
                    self.state = "multi_lobby"

            # ── multi_join_wait ─────────────────────────────────────
            elif self.state == "multi_join_wait":
                if network and network.error:
                    if self.btn_back_lobby.collidepoint(event.pos):
                        self.state = "multi_lobby"

        return None

    def _update_slider(self, mouse_x):
        """Recalcule self.volume selon la position X de la souris sur la piste."""
        relative = mouse_x - self.slider_rect.x
        self.volume = max(0.0, min(1.0, relative / self.slider_rect.width))

    def _try_join(self, network):
        """Valide le code et lance la tentative de connexion."""
        if len(self.input_code) < 4:
            self.input_error = "Code trop court !"
            return None
        self.input_error = ""
        self.state = "multi_join_wait"
        return "multi_join_session"   # main.py s'occupera d'appeler network.join_session