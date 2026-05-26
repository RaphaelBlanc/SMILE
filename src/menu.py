import pygame
import cv2
import sys
import os
import math
import glob
import json
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
        font_names = "fantasquesansmnerdfont,z003,comicsansms,impact"
        self.titre_font  = pygame.font.SysFont(font_names, 100)
        self.smile_font  = pygame.font.SysFont(font_names, 150)
        self.button_font = pygame.font.SysFont(font_names, 35)
        self.code_font   = pygame.font.SysFont(font_names, 60, bold=True)
        self.small_font  = pygame.font.SysFont(font_names, 28)

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

        # ── Boutons sauvegardes (dynamique) ─────────────────────────
        self.saves = []
        self.btn_back_save  = self._btn(center_x, SCREEN_HEIGHT // 2 + 350, 250, 60)
        self.btn_new_game   = self._btn(SCREEN_WIDTH - 250, SCREEN_HEIGHT // 2, 350, 80)

        
        # Confirmation suppression
        self.btn_confirm_del_yes = self._btn(center_x - 170, SCREEN_HEIGHT // 2 + 50, 320, 60)
        self.btn_confirm_del_no  = self._btn(center_x + 170, SCREEN_HEIGHT // 2 + 50, 320, 60)
        self.save_to_delete = None

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
        self.btn_create_save = self._btn(center_x, 480, 300, 60)
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
        self.load_keybinds()
        
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
        self.keybind_row_h       = 60      # Hauteur de chaque ligne
        
        # Presets
        self.btn_preset_wasd = self._btn(center_x + 650, 450, 150, 60)
        self.btn_preset_zqsd = self._btn(center_x + 650, 550, 150, 60)
        # Rect de chaque bouton "rebind" (reconstruit à chaque draw)
        self.keybind_btn_rects   = {}

    # ── Helpers ────────────────────────────────────────────────────

    @staticmethod
    def _btn(cx, cy, w, h):
        r = pygame.Rect(0, 0, w, h)
        r.center = (cx, cy)
        return r

    def refresh_saves(self):
        self.saves = []
        center_x = SCREEN_WIDTH // 2
        save_files = glob.glob("save_*.json")
        slots = []
        for f in save_files:
            try:
                slots.append(int(f.split('_')[1].split('.')[0]))
            except:
                pass
        slots.sort()
        
        y_offset = SCREEN_HEIGHT // 2 - max(0, len(slots)-1) * 50
        
        for i, slot in enumerate(slots):
            y = y_offset + i * 100
            btn = self._btn(center_x, y, 400, 80)
            del_btn = self._btn(center_x + 240, y, 40, 40)
            
            label = f"SAUVEGARDE {slot}"
            filename = f"save_{slot}.json"
            if os.path.exists(filename):
                try:
                    with open(filename, 'r') as f:
                        data = json.load(f)
                        if 'save_name' in data and data['save_name']:
                            label = data['save_name']
                except:
                    pass

            self.saves.append({
                'slot': slot,
                'btn': btn,
                'del': del_btn,
                'label': label
            })

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

    def draw_rainbow_bouncy_text(self, text, font, cx, cy, bounce_amp=10, rot_amp=15):
        colors = [
            (255, 0, 0),    # Rouge
            (255, 127, 0),  # Orange
            (255, 255, 0),  # Jaune
            (0, 255, 0),    # Vert
            (0, 0, 255),    # Bleu
            (75, 0, 130),   # Indigo
            (148, 0, 211)   # Violet
        ]
        
        surfaces = []
        total_width = 0
        t = pygame.time.get_ticks() / 200.0
        
        for i, char in enumerate(text):
            color = colors[i % len(colors)]
            surf = font.render(char, True, color)
            
            # Rotation pour rendre la lettre "moins droite"
            angle = math.sin(t + i) * rot_amp
            rotated_surf = pygame.transform.rotate(surf, angle)
            
            surfaces.append((rotated_surf, i))
            total_width += rotated_surf.get_width()
            
        start_x = cx - total_width // 2
        current_x = start_x
        
        for surf, i in surfaces:
            # Effet de rebond vertical
            y_offset = math.cos(t + i) * bounce_amp
            rect = surf.get_rect(center=(current_x + surf.get_width() // 2, cy + y_offset))
            self.screen.blit(surf, rect)
            current_x += surf.get_width()

    def draw_button(self, rect, text, color_normal, color_hover, mouse_pos):
        color = color_hover if rect.collidepoint(mouse_pos) else color_normal
        pygame.draw.rect(self.screen, color, rect, border_radius=15)
        pygame.draw.rect(self.screen, WHITE,  rect, 3, border_radius=15)
        
        # Choix de la couleur du texte en fonction du texte
        text_upper = text.upper()
        if "RETOUR" in text_upper or "ANNULER" in text_upper or "QUITTER" in text_upper or "NON" in text_upper or "X" == text_upper:
            # Rouge clair (contraste sur gris/bleu)
            text_color = (255, 100, 100)
            # Si le fond est deja rouge, on met le texte en blanc
            if color in [(200, 0, 0), (255, 50, 50), RED]:
                text_color = WHITE
        elif "JOUER" in text_upper or "REPRENDRE" in text_upper or "NOUVELLE" in text_upper or "CONFIRMER" in text_upper or "OUI" in text_upper or "CREER" in text_upper or "REJOINDRE" in text_upper or "HISTOIRE" in text_upper or "MULTIJOUEUR" in text_upper:
            # Vert clair
            text_color = (100, 255, 100)
            if color in [GREEN, (50, 255, 50)]:
                text_color = BLACK
        elif "PARAMETRES" in text_upper:
            text_color = YELLOW
        else:
            text_color = WHITE
            
        self.draw_text(text, self.button_font, text_color, rect.centerx, rect.centery)

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
                self.draw_text("PAUSE", self.titre_font, RED, cx, 320)
                btn_text = "REPRENDRE"
                btn_quit_text = "MENU PRINCIPAL"
            else:
                self.draw_rainbow_bouncy_text("SMILE", self.smile_font, cx, 300)
                btn_text = "JOUER"
                btn_quit_text = "QUITTER"
            self.draw_button(self.btn_play,     btn_text,     BLUE_MENU, BLUE_HOVER, mouse_pos)
            self.draw_button(self.btn_settings, "PARAMETRES", BLUE_MENU, BLUE_HOVER, mouse_pos)
            self.draw_button(self.btn_quit,     btn_quit_text,    BLUE_MENU, (200, 0, 0), mouse_pos)

        # ── Sélection de mode ───────────────────────────────────────
        elif self.state == "mode_selection":
            self.draw_text("CHOISIR UN MODE", self.titre_font, (100, 255, 100), cx, 250)
            self.draw_button(self.btn_mode_story, "MODE HISTOIRE", BLUE_MENU, BLUE_HOVER, mouse_pos)
            self.draw_button(self.btn_mode_multi, "MULTIJOUEUR",   BLUE_MENU, BLUE_HOVER, mouse_pos)
            self.draw_button(self.btn_back,       "RETOUR",        GREY,      WHITE,      mouse_pos)

        # ── Sélection de sauvegarde ─────────────────────────────────
        elif self.state == "save_selection":
            self.draw_text("CHOISIR UNE SAUVEGARDE", self.titre_font, YELLOW, cx, 150)
            
            if not self.saves:
                self.draw_text("aucune sauvegarde", self.button_font, GREY, cx, SCREEN_HEIGHT // 2)
            else:
                for s in self.saves:
                    self.draw_button(s['btn'], s['label'], BLUE_MENU, BLUE_HOVER, mouse_pos)
                    self.draw_button(s['del'], "X", (200, 0, 0), (255, 50, 50), mouse_pos)
            
            self.draw_button(self.btn_new_game, "NOUVELLE PARTIE", GREEN, (50, 255, 50), mouse_pos)
            self.draw_button(self.btn_back_save, "RETOUR", GREY, WHITE, mouse_pos)

        # ── Saisie nom nouvelle sauvegarde ──────────────────────────
        elif self.state == "new_save_input":
            self.draw_text("NOM DE LA SAUVEGARDE", self.titre_font, YELLOW, cx, 220)
            
            # Zone de saisie
            input_rect = pygame.Rect(0, 0, 400, 60)
            input_rect.center = (cx, 380)
            color = BLUE_HOVER if self.input_active else BLUE_MENU
            pygame.draw.rect(self.screen, (20, 20, 60), input_rect, border_radius=10)
            pygame.draw.rect(self.screen, color, input_rect, 3, border_radius=10)
            self.draw_text(self.input_code, self.button_font, WHITE, cx, 380)

            self.draw_button(self.btn_create_save, "CRÉER", GREEN, (50, 255, 50), mouse_pos)
            self.draw_button(self.btn_back_lobby, "ANNULER", GREY, WHITE, mouse_pos)

        # ── Confirmation de suppression ─────────────────────────────
        elif self.state == "delete_save_confirm":
            self.draw_text("voulez vous supprimer la sauvegarde?", self.button_font, WHITE, cx, 300)
            self.draw_button(self.btn_confirm_del_yes, "oui, malheureusement", (200, 0, 0), (255, 50, 50), mouse_pos)
            self.draw_button(self.btn_confirm_del_no, "non, je la garde!", GREEN, (50, 255, 50), mouse_pos)

        # ── Paramètres ──────────────────────────────────────────────
        elif self.state == "settings":
            self.draw_text("PARAMETRES", self.titre_font, YELLOW, cx, 250)

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

                self.draw_button(self.btn_preset_wasd, "WASD", (204, 153, 0), YELLOW, mouse_pos)
                self.draw_button(self.btn_preset_zqsd, "ZQSD", (204, 153, 0), YELLOW, mouse_pos)

            btn_back = self.btn_back_settings_keybinds if self.settings_tab == "keybinds" else self.btn_back_settings
            self.draw_button(btn_back, "RETOUR", GREY, WHITE, mouse_pos)

        # ── Lobby multi : choisir host ou client ────────────────────
        elif self.state == "multi_lobby":
            self.draw_text("MULTIJOUEUR", self.titre_font, YELLOW, cx, 250)
            self.draw_button(self.btn_host,       "CREER UN SALON", BLUE_MENU, BLUE_HOVER, mouse_pos)
            self.draw_button(self.btn_join,       "REJOINDRE",      BLUE_MENU, BLUE_HOVER, mouse_pos)
            self.draw_button(self.btn_back_lobby, "RETOUR",         GREY,      WHITE,      mouse_pos)

        # ── Host attend l'ami ────────────────────────────────────────
        elif self.state == "multi_host_wait":
            self.draw_text("EN ATTENTE D'UN JOUEUR", self.titre_font, YELLOW, cx, 220)

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
            self.draw_text("REJOINDRE UN SALON", self.titre_font, YELLOW, cx, 220)
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
            self.draw_text("CONNEXION EN COURS...", self.titre_font, YELLOW, cx, 300)
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

        # Saisie clavier pour le code/nom (état multi_join_input ou new_save_input)
        if (self.state == "multi_join_input" or self.state == "new_save_input") and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                if self.state == "multi_join_input": return self._try_join(network)
                elif self.state == "new_save_input" and self.input_code.strip() != "":
                    return ("new_game", self.next_save_slot, self.input_code.strip())
            elif event.key == pygame.K_BACKSPACE:
                self.input_code = self.input_code[:-1]
            elif len(self.input_code) < 16 and (event.unicode.isalnum() or event.unicode == ' '):
                self.input_code += event.unicode
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
                    self.save_keybinds()
                    self.rebinding_action = None
                return ("keybinds_changed", self.keybinds)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:

            # Activer/désactiver la zone de saisie
            if self.state == "multi_join_input":
                self.input_active = self.input_rect.collidepoint(event.pos)
            elif self.state == "new_save_input":
                input_rect = pygame.Rect(0, 0, 400, 60)
                input_rect.center = (SCREEN_WIDTH // 2, 380)
                self.input_active = input_rect.collidepoint(event.pos)

            # ── main ────────────────────────────────────────────────
            if self.state == "main":
                if self.btn_play.collidepoint(event.pos):     return "open_modes"
                if self.btn_settings.collidepoint(event.pos): self.state = "settings"
                if self.btn_quit.collidepoint(event.pos):     return "quit"

            # ── mode_selection ──────────────────────────────────────
            elif self.state == "mode_selection":
                if self.btn_mode_story.collidepoint(event.pos):
                    self.refresh_saves()
                    self.state = "save_selection"
                if self.btn_mode_multi.collidepoint(event.pos): self.state = "multi_lobby"
                if self.btn_back.collidepoint(event.pos):       self.state = "main"

            # ── save_selection ──────────────────────────────────────
            elif self.state == "save_selection":
                if self.btn_new_game.collidepoint(event.pos):
                    next_slot = 1
                    if self.saves:
                        next_slot = max(s["slot"] for s in self.saves) + 1
                    self.next_save_slot = next_slot
                    self.input_code = "Ma Sauvegarde"
                    self.input_active = True
                    self.state = "new_save_input"
                    return None

                for s in self.saves:
                    if s["btn"].collidepoint(event.pos):
                        return ("play_story", s["slot"])
                    if s["del"].collidepoint(event.pos):
                        self.save_to_delete = s["slot"]
                        self.state = "delete_save_confirm"
                        return None

                if hasattr(self, "btn_back_save") and self.btn_back_save.collidepoint(event.pos): self.state = "mode_selection"

            # ── new_save_input ──────────────────────────────────────
            elif self.state == "new_save_input":
                input_rect = pygame.Rect(0, 0, 400, 60)
                input_rect.center = (SCREEN_WIDTH // 2, 380)
                if hasattr(self, "btn_create_save") and self.btn_create_save.collidepoint(event.pos) and self.input_code.strip() != "":
                    return ("new_game", self.next_save_slot, self.input_code.strip())
                if hasattr(self, "btn_back_lobby") and self.btn_back_lobby.collidepoint(event.pos):
                    self.state = "save_selection"
            elif self.state == "delete_save_confirm":
                if self.btn_confirm_del_yes.collidepoint(event.pos):
                    action = ("delete_save", self.save_to_delete)
                    self.save_to_delete = None
                    return action
                if self.btn_confirm_del_no.collidepoint(event.pos):
                    self.save_to_delete = None
                    self.refresh_saves()
                    self.state = "save_selection"

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
                    if self.btn_preset_wasd.collidepoint(event.pos):
                        self.keybinds["move_up"]    = pygame.K_w
                        self.keybinds["move_down"]  = pygame.K_s
                        self.keybinds["move_left"]  = pygame.K_a
                        self.keybinds["move_right"] = pygame.K_d
                        self.save_keybinds()
                        self.rebinding_action = None
                        return ("keybinds_changed", self.keybinds)
                    elif self.btn_preset_zqsd.collidepoint(event.pos):
                        self.keybinds["move_up"]    = pygame.K_z
                        self.keybinds["move_down"]  = pygame.K_s
                        self.keybinds["move_left"]  = pygame.K_q
                        self.keybinds["move_right"] = pygame.K_d
                        self.save_keybinds()
                        self.rebinding_action = None
                        return ("keybinds_changed", self.keybinds)
                        
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

    def load_keybinds(self):
        filepath = os.path.join(ROOT_DIR, "keybinds.json")
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                    for action, key in data.items():
                        if action in self.keybinds:
                            self.keybinds[action] = key
            except Exception as e:
                print(f"Erreur lors du chargement des touches : {e}")

    def save_keybinds(self):
        filepath = os.path.join(ROOT_DIR, "keybinds.json")
        try:
            with open(filepath, "w") as f:
                json.dump(self.keybinds, f, indent=4)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde des touches : {e}")