#SECTION IMPORT #######################################################################

import pygame
import sys
import random
import math
import json
import os
import cv2
from pytmx.util_pygame import load_pygame
from player import Player
from son import SoundManager
from menu import Menu
from npc import NPC
from npc import DialogueBox
from network import Network
from boss import Glacius, Pyros
from monstre import (
    ChienEnrage, GoblinMelee, GoblinArcher,
    EspritFeu, EspritGlace, EspritFoudre, EspritNature,
    GolemPierre, Fox, Deer, GoblinLancier, Gorgon, MechaGolem,
)
from config import ROOT_DIR, format_time
import os

#DEFINITON CONSTANTE##################################################################

#ECRAN#
SCREEN_WIDTH  = 1920
SCREEN_HEIGHT = 1072
FPS = 60

#COULEURS#
WHITE     = (255, 255, 255)
BLACK     = (0,   0,   0)
RED       = (255, 0,   0)
BLUE_NPC  = (0,   0,   255)
BLUE_MENU = (0,   102, 204)
PURPLE    = (127, 0,   255)
ORANGE    = (255, 165, 0)
GREEN     = (0,   255, 0)
GRAY      = (120, 120, 135)
YELLOW    = (255, 220, 60)

#PHYSIQUE#
GRAVITY      = 0.8
JUMP_FORCE   = -16
PLAYER_SPEED = 6
FRICTION     = -0.12
HP_MAX       = 100

# Correspondance type Tiled → classe Python (Hugo)
MOB_CLASSES = {
    "ChienEnrage":  ChienEnrage,  "GoblinMelee":  GoblinMelee,
    "GoblinArcher": GoblinArcher, "EspritFeu":    EspritFeu,
    "EspritGlace":  EspritGlace,  "EspritFoudre": EspritFoudre,
    "EspritNature": EspritNature, "GolemPierre":  GolemPierre,
    "Fox":          Fox,          "Deer":         Deer,
    "GoblinLancier":GoblinLancier,
    "Gorgon":       Gorgon,
    "MechaGolem":   MechaGolem,
}
MOB_COLORS = {
    "ChienEnrage": (180,90,30),   "GoblinMelee":  (60,160,60),
    "GoblinArcher":(60,200,100),  "EspritFeu":    (255,100,0),
    "EspritGlace": (80,180,255),  "EspritFoudre": (220,255,0),
    "EspritNature":(30,200,80),   "GolemPierre":  (140,130,120),
    "Fox":          (240, 120, 30),"Deer":         (150, 110, 80),
    "GoblinLancier":(40, 160, 200),
    "Gorgon":       (100, 200, 100),
    "MechaGolem":   (120, 120, 120),
}
MOB_XP = {
    "ChienEnrage":20, "GoblinMelee":30, "GoblinArcher":40,
    "EspritFeu":35,   "EspritGlace":35, "EspritFoudre":45,
    "EspritNature":30,"GolemPierre":100,
    "Fox":10,         "Deer":15,
    "GoblinLancier":50,
    "Gorgon":120,
    "MechaGolem":150,
}

#CLASS PARTICLE (Hugo)###############################################################

class Particle:
    def __init__(self, x, y, color):
        self.x     = float(x)
        self.y     = float(y)
        self.vx    = random.uniform(-4, 4)
        self.vy    = random.uniform(-6, -1)
        self.life  = random.randint(18, 35)
        self.r     = random.randint(3, 7)
        self.color = color

    def update(self):
        self.x  += self.vx
        self.vy += 0.4
        self.y  += self.vy
        self.life -= 1

    def draw(self, surface):
        if self.life > 0:
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.r)

#CLASS ASSET MANAGER#################################################################

class AssetManager:
    def __init__(self):
        pass

#CLASS TILE#########################################################################

class Tile(pygame.sprite.Sprite):
    def __init__(self, pos, surf, groups):
        super().__init__(groups)
        self.image = surf
        self.rect  = self.image.get_rect(topleft=pos)

#CLASS CAMERA (ton code)#############################################################

class Camera:
    def __init__(self, map_width, map_height):
        self.map_width  = map_width
        self.map_height = map_height
        self.offset     = pygame.math.Vector2(0, 0)
        self.lerp_speed = 0.10

    def update(self, target_rect):
        target_x = target_rect.centerx - SCREEN_WIDTH  // 2
        target_y = target_rect.centery - SCREEN_HEIGHT // 2
        self.offset.x += (target_x - self.offset.x) * self.lerp_speed
        self.offset.y += (target_y - self.offset.y) * self.lerp_speed
        self.offset.x = max(0, min(self.offset.x, self.map_width  - SCREEN_WIDTH))
        self.offset.y = max(0, min(self.offset.y, self.map_height - SCREEN_HEIGHT))

    def apply(self, rect):
        return rect.move(-int(self.offset.x), -int(self.offset.y))

#CLASS REMOTE PLAYER (fantôme de l'autre joueur) #####################################

class RemotePlayer(pygame.sprite.Sprite):
    """Représentation locale animée du joueur distant — mis à jour par les messages réseau."""
    def __init__(self, pos, player_num=2):
        super().__init__()
        self.player_num = player_num
        self.hp_current = 100
        self.hp_max     = 100
        self.facing_right = True
        self.is_sprinting = False
        self.on_ladder = False
        self.status = "idle_right"
        
        self.dx = 0
        self.dy = 0
        
        from animator import Animator
        self.animations = {}
        self._load_assets()
        
        self.animator = Animator(self.animations, fps=8)
        self.image = self.animations["idle_right"][0]
        self.rect  = self.image.get_rect(topleft=pos)

    def _load_assets(self):
        import os
        from config import ROOT_DIR
        actions = [
            'idle_right', 'idle_left', 'run_right', 'run_left', 
            'sprint_right', 'sprint_left', 'jump_right', 'jump_left', 
            'land_right', 'land_left', 'death', 'back', 'front'
        ]
        self.animations = {action: [] for action in actions}
        
        if self.player_num == 2:
            base_path = os.path.join(ROOT_DIR, 'assets', 'images', 'player2', 'mouvements')
            prefix = "Slime2_"
            death_file = "Slime2_Death.png"
            fill_color = (0, 200, 255)
        else:
            base_path = os.path.join(ROOT_DIR, 'assets', 'images', 'player', 'mouvements')
            prefix = "Slime1_"
            death_file = "Slime1_Death_body.png"
            fill_color = (0, 200, 0)
            
        SLIME_SIZE = (225, 225) 
        ROW_FRONT = 0
        ROW_BACK  = 1
        ROW_LEFT  = 2
        ROW_RIGHT = 3

        def slice_sheet(filename, cols, rows):
            path = os.path.join(base_path, filename)
            if not os.path.exists(path):
                return None
            try:
                sheet = pygame.image.load(path).convert_alpha()
                frame_w = sheet.get_width() // cols
                frame_h = sheet.get_height() // rows
                
                sheet_frames = []
                for r in range(rows):
                    row_frames = []
                    for c in range(cols):
                        rect = pygame.Rect(c * frame_w, r * frame_h, frame_w, frame_h)
                        img = pygame.Surface((frame_w, frame_h), pygame.SRCALPHA)
                        img.blit(sheet, (0, 0), rect)
                        img = pygame.transform.scale(img, SLIME_SIZE)
                        row_frames.append(img)
                    sheet_frames.append(row_frames)
                return sheet_frames
            except Exception as e:
                print(f"Erreur decoupage {filename}: {e}")
                return None

        # 1. IDLE / MOUVEMENT
        idle_frames = slice_sheet(f"{prefix}Idle_body.png", cols=6, rows=4)
        if idle_frames:
            self.animations['front']      = idle_frames[ROW_FRONT]
            self.animations['back']       = idle_frames[ROW_BACK]
            self.animations['idle_left']  = idle_frames[ROW_LEFT]
            self.animations['idle_right'] = idle_frames[ROW_RIGHT]
            
            # Use same sheet for actions for simplicity and size matching
            self.animations['run_left']     = idle_frames[ROW_LEFT]
            self.animations['run_right']    = idle_frames[ROW_RIGHT]
            self.animations['sprint_left']  = idle_frames[ROW_LEFT]
            self.animations['sprint_right'] = idle_frames[ROW_RIGHT]
            self.animations['jump_left']    = idle_frames[ROW_LEFT]
            self.animations['jump_right']   = idle_frames[ROW_RIGHT]
            self.animations['land_left']    = idle_frames[ROW_LEFT]
            self.animations['land_right']   = idle_frames[ROW_RIGHT]

        # 2. DECEASED
        death_frames = slice_sheet(death_file, cols=10, rows=4)
        if death_frames:
            self.animations['death'] = death_frames[ROW_FRONT]

        # PLACEHOLDERS
        for state in self.animations:
            if not self.animations[state]:
                placeholder = pygame.Surface(SLIME_SIZE, pygame.SRCALPHA)
                placeholder.fill(fill_color)
                self.animations[state].append(placeholder)

    def apply_state(self, state: dict):
        new_x = state.get("x", self.rect.x)
        new_y = state.get("y", self.rect.y)
        
        self.dx = new_x - self.rect.x
        self.dy = new_y - self.rect.y
        
        self.rect.x = new_x
        self.rect.y = new_y
        self.hp_current = state.get("hp", self.hp_current)

    def take_damage(self, amount):
        pass  # Les dégâts du joueur distant sont gérés de son côté et synchronisés via le réseau

    def update(self, dt):
        loop = (self.status != 'death')
        self.image = self.animator.get_current_frame(dt, self.status, loop=loop)

#CLASS INTRO VIDEO##################################################################

class IntroVideo:
    """Joue la vidéo d'intro avec son au lancement, AVANT que le SoundManager démarre la musique."""

    def __init__(self, screen, clock, video_path):
        self.screen     = screen
        self.clock      = clock
        self.video_path = video_path

    def play(self):
        """Bloque jusqu'à la fin de la vidéo (ou si le joueur appuie sur ESPACE/ENTRÉE/ECHAP)."""
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            print(f"INTRO : impossible d'ouvrir {self.video_path}, on passe.")
            return

        fps_video = cap.get(cv2.CAP_PROP_FPS) or 30.0

        audio_path = None
        try:
            try:
                from moviepy.editor import VideoFileClip   # moviepy 1.x
            except ImportError:
                from moviepy import VideoFileClip           # moviepy 2.x
            import tempfile
            clip = VideoFileClip(self.video_path)
            if clip.audio is not None:
                tmp = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)
                audio_path = tmp.name
                tmp.close()
                clip.audio.write_audiofile(audio_path, logger=None)
                pygame.mixer.music.stop()
                pygame.mixer.music.load(audio_path)
                pygame.mixer.music.play()
            clip.close()
        except Exception as e:
            print(f"INTRO : audio non disponible ({e})")

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    cap.release()
                    pygame.mixer.music.stop()
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN and event.key in (
                        pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                    running = False

            success, frame = cap.read()
            if not success:
                break

            # Enlever les bordures noires intégrées à la vidéo d'intro (5% de chaque côté sur 3840x2160)
            # La zone utile est [108:2052, 192:3648]
            h_vid, w_vid, _ = frame.shape
            if w_vid > 192 and h_vid > 108:
                margin_x = int(w_vid * 0.05)
                margin_y = int(h_vid * 0.05)
                frame = frame[margin_y:h_vid-margin_y, margin_x:w_vid-margin_x]

            frame = cv2.resize(frame, (SCREEN_WIDTH, SCREEN_HEIGHT))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = frame.transpose(1, 0, 2)
            surf  = pygame.surfarray.make_surface(frame)
            self.screen.blit(surf, (0, 0))

            hint_font = pygame.font.SysFont("consolas", 22)
            hint      = hint_font.render("ESPACE  pour passer", True, (200, 200, 200))
            self.screen.blit(hint, (SCREEN_WIDTH - hint.get_width() - 24,
                                    SCREEN_HEIGHT - hint.get_height() - 16))
            pygame.display.flip()
            self.clock.tick(fps_video)

        cap.release()
        pygame.mixer.music.stop()

        # ── Fondu au noir depuis la dernière frame ───────────────────
        fade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        fade.fill((0, 0, 0))
        last_surf = surf if 'surf' in locals() else fade
        for alpha in range(0, 256, 5):
            self.screen.blit(last_surf, (0, 0))
            fade.set_alpha(alpha)
            self.screen.blit(fade, (0, 0))
            pygame.display.flip()
            pygame.time.delay(16)

        # Noir complet une fraction de seconde
        self.screen.fill((0, 0, 0))
        pygame.display.flip()
        pygame.time.delay(200)

        # Supprimer le fichier audio temporaire
        if audio_path:
            try:
                import os as _os
                _os.remove(audio_path)
            except Exception:
                pass

CREDITS_TEXT = [
    "DIRECTION & PRODUCTION",
    "",
    "Réalisateur & Concepteur Principal : Horagle",
    "Producteur Exécutif : Raphael Blanc--Alcaix",
    "Directeur Artistique : Oceane Jordan",
    "Scénariste Principal : Hugo Birard",
    "",
    "DESIGN DE JEU (GAME DESIGN)",
    "",
    "Lead Game Designer : Guilhem Fourrey",
    "System Designer (Équilibrage de la Magie) : Raphael Blanc--Alcaix",
    "Level Designer (Création des Donjons & Châteaux) : Alexandre Fillaquier",
    "Combat Designer (Mécaniques du Mage) : Guilhem Fourrey",
    "",
    "PROGRAMMATION & TECHNIQUE",
    "",
    "Directeur Technique : Raphael Blanc--Alcaix",
    "Développeur Moteur & Gameplay : Hugo Birard",
    "Programmation de l'Interface : Oceane Jordan",
    "Gestion des Effets de Lumière & LED : Alexandre Fillaquier",
    "Optimisation & Stabilité : Guilhem Fourrey",
    "",
    "GRAPHISMES & ANIMATION",
    "",
    "Artiste Conceptuel (Concept Art) : Hugo Birard",
    "Modélisation & Pixel Art du Mage : Guilhem Fourrey",
    "Créateur du Ciel Étoilé & Décors : Guilhem Fourrey",
    "Animateur des Effets Magiques : Hugo Birard",
    "UI/UX Designer : Alexandre Fillaquier",
    "",
    "AUDIO & MUSIQUE",
    "",
    "Compositeur de la Bande Originale : Oceane Jordan",
    "Concepteur Sonore (Sound Designer) : Oceane Jordan",
    "Bruitages des Étoiles & Sorts Violet : Oceane Jordan",
    "Ingénieur du Son : Oceane Jordan",
    "",
    "ASSURANCE QUALITÉ (TESTS)",
    "",
    "Responsable QA (Lead Tester) : Raphael Blanc--Alcaix",
    "Chasseurs de Bugs Principaux : Raphael Blanc--Alcaix / Guilhem Fourrey",
    "Équipe de Bêta-Testeurs : Raphael Blanc--Alcaix / Guilhem Fourrey",
    "",
    "SYNDICAT DES MAGECREUX",
    "",
    "Représentant en Chef : Raphael Blanc--Alcaix",
    "Conseiller aux Affaires Occultes : Alexandre Fillaquier",
    "Gardien des Archives : Hugo Birard",
    "",
    "REMERCIEMENTS SPÉCIAUX",
    "",
    "UN GRAND MERCI D'AVOIR JOUÉ !",
    "Voyageur, vous êtes arrivé au bout du chemin.",
    "Vous avez bravé l'obscurité, maîtrisé votre puissance,",
    "et inscrit votre nom parmi les légendes.",
    "Ce jeu a été conçu avec passion, caféine et une immense volonté",
    "de vous offrir une aventure mémorable. Sans votre curiosité",
    "et votre persévérance, ce monde n'aurait jamais pris vie.",
    "Merci de faire partie de notre histoire.",
    "",
    "Un grand merci à Alix pour ses précieux conseils.",
    "",
    "LE MOT DE LA FIN",
    "",
    "Le récit s'achève... Merci de l'avoir vécu, valeureux mage.",
    "Fin de l'aventure... En quête de nouvelles terres et de nouveaux mystères...",
    "Que la magie continue de vous guider.",
    "",
    "LIBERTE QUOI YGALE",
    "Tous droits réservés – 2026"
]

#CLASS GAME##########################################################################

class Game:

    def __init__(self, screen=None, clock=None):
        if screen is None:
            pygame.init()
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
            pygame.display.set_caption("SMILE")
            self.clock  = pygame.time.Clock()
        else:
            self.screen = screen
            self.clock  = clock

        # Polices HUD
        self.font_hud   = pygame.font.SysFont("consolas", 18, bold=True)
        self.font_small = pygame.font.SysFont("consolas", 14)
        self.font_title = pygame.font.SysFont("consolas", 42, bold=True)
        self.potion_font = pygame.font.SysFont("consolas", 24, bold=True)
        
        try:
            self.potion_img = pygame.image.load(os.path.join(ROOT_DIR, "assets", "images", "potion.png")).convert_alpha()
            self.potion_img = pygame.transform.scale(self.potion_img, (64, 64))
        except:
            self.potion_img = pygame.Surface((64, 64), pygame.SRCALPHA)
            pygame.draw.rect(self.potion_img, (200, 0, 50), (16, 16, 32, 32), border_radius=8)
            
        self.is_end_game = False
        self.end_game_timer = 0.0
        self.show_credits = False
        self.credits_scroll_y = SCREEN_HEIGHT
        self.btn_credits = pygame.Rect(0, 0, 700, 70)
        self.btn_credits.center = (SCREEN_WIDTH // 2, 930)  # Position approx du texte
        self.credits_font_title = pygame.font.SysFont("consolas", 40, bold=True)
        self.credits_font_text = pygame.font.SysFont("consolas", 28)
        self.credits_finished = False
        self.btn_end_menu = pygame.Rect(SCREEN_WIDTH - 300, SCREEN_HEIGHT - 100, 250, 60)

        try:
            self.designfin_img = pygame.image.load(os.path.join(ROOT_DIR, "assets", "images", "designfin.png")).convert_alpha()
            self.designfin_img = pygame.transform.scale(self.designfin_img, (SCREEN_WIDTH, SCREEN_HEIGHT))
        except:
            self.designfin_img = None

        # --- ETATS DU JEU ---
        self.is_paused    = True
        self.game_started = False
        self.score        = 0
        self.kill_count   = 0
        self.respawn_count = 0
        self.particles    = []

        # --- SAUVEGARDE ---
        self.current_save_slot = None
        self.last_save_time = 0
        self.save_indicator_timer = 0
        self.save_font = pygame.font.SysFont("consolas", 20, bold=True)

        # Screen-shake pour GolemPierre
        self.shake_ref = [0]
        self.mob_counter = 0

        # --- GAME OVER ---
        self.death_time = None
        cx = SCREEN_WIDTH // 2
        cy = SCREEN_HEIGHT // 2
        self.btn_respawn = pygame.Rect(0, 0, 320, 75)
        self.btn_respawn.center = (cx - 200, cy + 80)
        self.btn_gameover_menu = pygame.Rect(0, 0, 320, 75)
        self.btn_gameover_menu.center = (cx + 200, cy + 80)
        self.respawn_point = (200, 200)   # mis à jour au spawn / checkpoint
        self.menu_input_blocked = 0       # frames où le menu ignore les clics

        # --- MODE MULTI ---
        self.network       = None          # Network() créé à la demande
        self.is_multi      = False         # True si partie réseau
        self.show_menu_overlay = False     # True pour afficher l'overlay en multi
        self.remote_player = None          # RemotePlayer (l'autre joueur)
        self.net_timer     = 0             # compteur pour envoi état (host)
        self.pending_damage_events = []
        self.last_transition_flag  = ""

        # --- SON / MENU ---
        self.sound_manager = SoundManager()
        self.menu          = Menu(self.screen)

        # --- GROUPES DE SPRITES ---
        self.visibles_sprites   = pygame.sprite.Group()
        self.obstacle_sprites   = pygame.sprite.Group()
        self.plateforme_sprites = pygame.sprite.Group()
        self.npc_sprites        = pygame.sprite.Group()
        self.ladder_sprites     = pygame.sprite.Group()
        self.monster_sprites    = pygame.sprite.Group()
        self.enemy_proj_sprites = pygame.sprite.Group()
        self.vfx_sprites        = pygame.sprite.Group()
        self.transition_sprites = pygame.sprite.Group()

        # --- UI DIALOGUE ---
        self.dialogue_box = DialogueBox(self.screen)

        self.doors = []
        self.spawn_boss = None
        self.killed_by_boss = False
        self.current_map_name = ""
        self.killed_mobs = set()
        self.boss_death_pos = None
        
        # --- ETATS DE QUETE ---
        self.boss_glace_dead = False
        self.boss_lave_dead = False
        self.coming_from_boss = False
        self.coming_from_glace = False
        self.coming_from_lave = False
        self.coming_from_teleport = False
        self.spawn_from_boss_point = None
        self.spawn_porte_glace_point = None
        self.spawn_from_glace_point = None
        self.spawn_from_lave_point = None
        self.pnj_boss_pos = None
        self.play_time = 0.0

        # Joueur local initial (sera repositionné par load_map)
        self.player = Player((200, 200), self.sound_manager, self.menu.keybinds)
        self.visibles_sprites.add(self.player)
        self.respawn_point = (200, 200)

        # --- CHARGEMENT DE LA MAP ---
        self.load_map('assets/maps/Surface.tmx')

    def _get_zone_name(self, map_path):
        if not map_path:
            return ""
        if "zone1" in map_path.lower():
            return "zone1"
        if "glace" in map_path:
            return "glace"
        if "map1" in map_path or "lave" in map_path.lower():
            return "lave"
        if "finale" in map_path:
            return "finale"
        return "unknown"

    def load_map(self, map_file):
        print(f"Chargement de la map : {map_file}")
        
        # Detect zone change
        zone_current = self._get_zone_name(self.current_map_name)
        zone_next = self._get_zone_name(map_file)
        
        if zone_current and zone_current != zone_next:
            self.killed_mobs.clear()
            
        # Reinitialise les potions
        if "BossLave" in map_file or ("lave" in map_file.lower() and "boss" in map_file.lower()):
            self.player.potions_max = 1
        elif "glace" in map_file.lower() and "boss" in map_file.lower():
            self.player.potions_max = 2
        else:
            self.player.potions_max = 3
            
        self.player.potions_current = self.player.potions_max
        self.player.potion_primed = False
            
        self.current_map_name = map_file

        if 'glace' in map_file:
            self.sound_manager.play_world_music('glace')
        elif 'map1' in map_file or 'lave' in map_file:
            self.sound_manager.play_world_music('feu')
            
        # Enregistrement du meilleur temps lorsqu'on atteint la map de fin
        if "Fin" in map_file:
            self.is_end_game = True
            self.end_game_timer = 0.0
            
            filepath = os.path.join(ROOT_DIR, "best_time.json")
            old_best = None
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r") as f:
                        old_best = json.load(f).get("best_time")
                except:
                    pass
            if old_best is None or getattr(self, 'play_time', 0.0) < old_best:
                try:
                    with open(filepath, "w") as f:
                        json.dump({"best_time": getattr(self, 'play_time', 0.0)}, f)
                    self.menu.load_best_time()
                except:
                    pass
        
        for s in self.visibles_sprites:
            if s != self.player and getattr(self, 'remote_player', None) != s:
                s.kill()
        self.obstacle_sprites.empty()
        self.plateforme_sprites.empty()
        self.npc_sprites.empty()
        self.ladder_sprites.empty()
        self.monster_sprites.empty()
        self.mob_counter = 0
        self.enemy_proj_sprites.empty()
        self.vfx_sprites.empty()
        self.transition_sprites.empty()
        self.particles.clear()
        self.doors.clear()
        self.dialogue_box.hide()
        
        self.spawn_from_boss_point = None
        self.spawn_porte_glace_point = None
        self.spawn_from_glace_point = None
        self.spawn_from_lave_point = None
        self.pnj_boss_pos = None

        full_path = os.path.join(ROOT_DIR, map_file)
        if not os.path.exists(full_path):
            print(f"ATTENTION : Le fichier map '{full_path}' n'existe pas encore.")
            return

        tmx_data = load_pygame(full_path)
        map_pixel_width  = tmx_data.width  * tmx_data.tilewidth
        map_pixel_height = tmx_data.height * tmx_data.tileheight

        self.camera = Camera(map_pixel_width, map_pixel_height)

        try:
            layer_fond = tmx_data.get_layer_by_name('Background')
            self.background_image = layer_fond.image
        except (ValueError, AttributeError):
            print("ERREUR : Calque 'Background' introuvable.")
            self.background_image = pygame.Surface((map_pixel_width, map_pixel_height))
            self.background_image.fill((50, 50, 50))

        for x, y, surf in tmx_data.get_layer_by_name('Collisions').tiles():
            if surf:
                Tile((x * 32, y * 32), surf, [self.obstacle_sprites])

        try:
            for x, y, surf in tmx_data.get_layer_by_name('Plateforme').tiles():
                if surf:
                    Tile((x * 32, y * 32), surf, [self.plateforme_sprites])
        except ValueError:
            print("INFO : Calque 'Plateforme' introuvable.")

        try:
            for x, y, surf in tmx_data.get_layer_by_name('Echelles').tiles():
                Tile((x * 32, y * 32), surf, [self.ladder_sprites])
            print(f"INFO : {len(self.ladder_sprites)} tuile(s) d'echelle chargee(s).")
        except ValueError:
            print("INFO : Calque 'Echelles' introuvable — echelles ignorees.")

        try:
            for x, y, surf in tmx_data.get_layer_by_name('Transition').tiles():
                if surf:
                    Tile((x * 32, y * 32), surf, [self.transition_sprites])
        except ValueError:
            pass

        player_spawn = (200, 200)
        self.spawn_host_point = None
        self.spawn_client_point = None
        self.spawn_from_glace_point = None
        self.spawn_depuis_glace_point = None
        self.spawn_from_boss_point = None
        self.spawn_from_lave_point = None
        self.spawn_porte_glace_point = None
        self.spawn_porte_to_glace_point = None
        self.spawn_depuis_mage_point = None
        try:
            for obj_index, obj in enumerate(tmx_data.get_layer_by_name('Objets')):
                obj_type = getattr(obj, 'type', None) or obj.properties.get('type', None)
                if not obj_type:
                    obj_type = getattr(obj, 'name', None)
                
                pos = (int(obj.x), int(obj.y))
                rect = pygame.Rect(pos[0], pos[1], getattr(obj, 'width', 32), getattr(obj, 'height', 32))

                obj_type_lower = obj_type.lower() if obj_type else ''

                if obj_type_lower in ('spawnjoueur', 'spawn_lave', 'spawn_depart', 'spawn_joueur_boss_lave'):
                    player_spawn = pos
                elif obj_type_lower == 'host':
                    self.spawn_host_point = pos
                elif obj_type_lower == 'client':
                    self.spawn_client_point = pos
                elif obj_type_lower == 'spawnjoueurboss':
                    self.zone_boss_respawn_point = pos
                    self.zone_boss_map = self.current_map_name
                elif obj_type_lower in ('spawn_from_boss', 'spawn_form_boss'):
                    self.spawn_from_boss_point = pos
                elif obj_type_lower == 'spawn_from_glace':
                    self.spawn_from_glace_point = pos
                elif obj_type_lower == 'spawn_from_haut':
                    player_spawn = pos
                elif obj_type_lower == 'spawn_from_lave':
                    self.spawn_from_lave_point = pos
                elif obj_type_lower in ('pnj_boss', 'pnjboss'):
                    if "map_boss_glace" in map_file:
                        self.pnj_boss_pos = pos
                        if self.boss_glace_dead:
                            msg = "Bravo, tu as vaincu le boss !|Je te téléporte à la porte suivante."
                            npc = NPC(pos, msg, [self.visibles_sprites, self.npc_sprites], on_end_callback=self.teleport_from_boss, name=getattr(obj, 'name', None), pnj_type=obj_type_lower)
                    else:
                        if not self.boss_glace_dead:
                            msg = "Attention au boss de glace !"
                            NPC(pos, msg, [self.visibles_sprites, self.npc_sprites], name=getattr(obj, 'name', None), pnj_type=obj_type_lower)
                elif obj_type_lower == 'pnjporteglace':
                    self.spawn_porte_glace_point = pos
                    if self.boss_glace_dead:
                        msg = "Le boss est mort !|La porte est maintenant ouverte."
                    else:
                        msg = "La porte est fermée...|Il faut d'abord vaincre le boss de glace."
                    NPC(pos, msg, [self.visibles_sprites, self.npc_sprites], name=getattr(obj, 'name', None), pnj_type=obj_type_lower)
                elif obj_type_lower == 'mage':
                    msg = "Bravo, tu as vaincu le boss !|Je vais te téléporter vers la fin."
                    def tp_fin():
                        if self.is_multi and getattr(self, 'network', None) and self.network.role == "client":
                            self.network._send({"action": "request_map_change", "dest": 'assets/maps/Fin.tmx', "req_flag": "mage"})
                        else:
                            self.coming_from_mage = True
                            self.map_flag = "mage"
                            self.load_map('assets/maps/Fin.tmx')
                    NPC(pos, msg, [self.visibles_sprites, self.npc_sprites], on_end_callback=tp_fin, name=getattr(obj, 'name', None), pnj_type=obj_type_lower)
                elif obj_type_lower == 'spawndepuisglace':
                    self.spawn_depuis_glace_point = pos
                elif obj_type_lower == 'spawndepuismage':
                    self.spawn_depuis_mage_point = pos
                elif obj_type_lower == 'npc':
                    msg = obj.properties.get('message', 'Bonjour !')
                    NPC(pos, msg, [self.visibles_sprites, self.npc_sprites], name=getattr(obj, 'name', None), pnj_type=obj_type_lower)
                elif obj_type_lower in ('portetolave', 'porte_to_lave', 'portebossglace', 'porteglace', 'porte_to_glace', 'porte_to_zone_1', 'porte_to zone_1', 'porte_boss_lave', 'porteversglace', 'porteversmage'):
                    if obj_type_lower in ('portetolave', 'porte_to_lave'):
                        dest = 'assets/maps/ZoneLave.tmx'
                    elif obj_type_lower == 'portebossglace':
                        dest = 'assets/maps/map_boss_glace.tmx'
                    elif obj_type_lower in ('porte_to_glace', 'porteversglace'):
                        dest = 'assets/maps/map_glace.tmx'
                        self.spawn_porte_to_glace_point = pos
                    elif obj_type_lower == 'porteglace':
                        dest = 'assets/maps/ZoneMage.tmx'
                    elif obj_type_lower in ('porte_to_zone_1', 'porte_to zone_1'):
                        dest = 'assets/maps/Zone1.tmx'
                    elif obj_type_lower == 'porte_boss_lave':
                        dest = 'assets/maps/BossLave.tmx'
                    elif obj_type_lower == 'porteversmage':
                        dest = 'assets/maps/ZoneMage.tmx'
                    else:
                        dest = 'assets/maps/map_finale.tmx'
                    
                    if obj_type_lower == 'porte_to_glace' and player_spawn == (200, 200):
                        player_spawn = pos
                    
                    self.doors.append({'rect': rect, 'dest': dest, 'type': obj_type_lower})
                elif obj_type == 'BossGlace':
                    if not self.boss_glace_dead:
                        floor_y = pos[1] + getattr(obj, 'height', 32)
                        boss = Glacius(pos, self.obstacle_sprites, floor_y)
                        boss.id = getattr(obj, 'id', obj_index)
                        boss.sound_manager = self.sound_manager
                        self.monster_sprites.add(boss)
                elif obj_type_lower == 'spawn_boss_lave':
                    if not self.boss_lave_dead:
                        floor_y = pos[1] + getattr(obj, 'height', 32)
                        boss = Pyros(pos, self.obstacle_sprites, floor_y)
                        boss.id = getattr(obj, 'id', obj_index)
                        boss.sound_manager = self.sound_manager
                        self.monster_sprites.add(boss)
                    else:
                        self.pnj_boss_pos = pos
                        msg = "Le gardien de la lave est vaincu.|Je te téléporte hors d'ici."
                        npc = NPC(pos, msg, [self.visibles_sprites, self.npc_sprites], on_end_callback=self.teleport_from_boss_lave)
                elif obj_type in MOB_CLASSES:
                    if (self.current_map_name, pos) not in self.killed_mobs:
                        mob = self._spawn_mob(obj_type, pos)
                        if mob:
                            mob.id = getattr(obj, 'id', obj_index)
                            mob.spawn_pos = pos
        except ValueError:
            print("INFO : Calque 'Objets' introuvable — monstres non charges depuis Tiled.")



        if map_file == 'assets/maps/PVP.tmx' and getattr(self, 'is_multi', False):
            if self.player.player_num == 1 and getattr(self, 'spawn_host_point', None):
                player_spawn = self.spawn_host_point
            elif self.player.player_num == 2 and getattr(self, 'spawn_client_point', None):
                player_spawn = self.spawn_client_point

        self.last_transition_flag = ""
        if self.killed_by_boss and hasattr(self, 'zone_boss_respawn_point'):
            self.last_transition_flag = "boss"
            self.player.set_position(self.zone_boss_respawn_point)
            self.respawn_point = self.zone_boss_respawn_point
        elif self.coming_from_boss and self.spawn_from_boss_point:
            self.last_transition_flag = "boss"
            self.player.set_position(self.spawn_from_boss_point)
            self.respawn_point = self.spawn_from_boss_point
        elif self.coming_from_glace and getattr(self, 'spawn_from_glace_point', None):
            self.last_transition_flag = "glace"
            self.player.set_position(self.spawn_from_glace_point)
            self.respawn_point = self.spawn_from_glace_point
        elif self.coming_from_glace and getattr(self, 'spawn_depuis_glace_point', None):
            self.last_transition_flag = "glace"
            self.player.set_position(self.spawn_depuis_glace_point)
            self.respawn_point = self.spawn_depuis_glace_point
        elif getattr(self, 'coming_from_mage', False) and getattr(self, 'spawn_depuis_mage_point', None):
            self.last_transition_flag = "mage"
            self.player.set_position(self.spawn_depuis_mage_point)
            self.respawn_point = self.spawn_depuis_mage_point
        elif self.coming_from_lave and self.spawn_from_lave_point:
            self.last_transition_flag = "lave"
            self.player.set_position(self.spawn_from_lave_point)
            self.respawn_point = self.spawn_from_lave_point
        elif self.coming_from_teleport and getattr(self, 'spawn_porte_glace_point', None):
            self.last_transition_flag = "tp_glace"
            tp_pos = (self.spawn_porte_glace_point[0] - 50, self.spawn_porte_glace_point[1] - 150)
            self.player.set_position(tp_pos)
            self.respawn_point = tp_pos
        elif getattr(self, 'coming_from_teleport_lave', False) and getattr(self, 'spawn_porte_to_glace_point', None):
            self.last_transition_flag = "tp_lave"
            safe_pos = (self.spawn_porte_to_glace_point[0] - 100, self.spawn_porte_to_glace_point[1] - 150)
            self.player.set_position(safe_pos)
            self.respawn_point = safe_pos
        else:
            self.last_transition_flag = "none"
            self.player.set_position(player_spawn)
            self.respawn_point = player_spawn
            
        self.coming_from_boss = False
        self.coming_from_glace = False
        self.coming_from_lave = False
        self.coming_from_teleport = False
        self.coming_from_teleport_lave = False
        self.coming_from_mage = False
        self.map_flag = None
        self.killed_by_boss = False
        self.coming_from_boss = False
        self.coming_from_glace = False
        self.coming_from_lave = False
        self.coming_from_teleport = False
        self.coming_from_teleport_lave = False
        
        # Snap camera to player immediately to avoid panning from (0,0)
        target_x = self.player.rect.centerx - SCREEN_WIDTH // 2
        target_y = self.player.rect.centery - SCREEN_HEIGHT // 2
        self.camera.offset.x = max(0, min(target_x, self.camera.map_width - SCREEN_WIDTH))
        self.camera.offset.y = max(0, min(target_y, self.camera.map_height - SCREEN_HEIGHT))

        # Auto-save after changing map/zone
        if getattr(self, 'game_started', False):
            self.save_game()

    def teleport_from_boss(self):
        self.coming_from_teleport = True
        self.map_flag = "tp_glace"
        if self.is_multi and self.network and self.network.role == "client":
            self.network._send({"action": "request_map_change", "dest": "assets/maps/map_glace.tmx", "req_flag": "tp_glace"})
            return
        self.load_map('assets/maps/map_glace.tmx')

    def teleport_from_boss_lave(self):
        self.coming_from_teleport_lave = True
        self.map_flag = "tp_lave"
        if self.is_multi and self.network and self.network.role == "client":
            self.network._send({"action": "request_map_change", "dest": "assets/maps/ZoneLave.tmx", "req_flag": "tp_lave"})
            return
        self.load_map('assets/maps/ZoneLave.tmx')

    def load_game(self, slot):
        is_same_slot = (getattr(self, 'current_save_slot', None) == slot)
        self.current_save_slot = slot
        filename = f"save_{slot}.json"
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                
                self.current_save_name = data.get('save_name', None)

                # Restore game state
                self.score = data.get('score', 0)
                self.kill_count = data.get('kill_count', 0)
                self.respawn_count = data.get('respawn_count', 0)
                
                loaded_play_time = data.get('play_time', 0.0)
                if is_same_slot and hasattr(self, 'play_time'):
                    self.play_time = max(self.play_time, loaded_play_time)
                else:
                    self.play_time = loaded_play_time
                    
                self.boss_glace_dead = data.get('boss_glace_dead', False)
                self.boss_lave_dead = data.get('boss_lave_dead', False)
                
                # Killed mobs - convert back to set of tuples
                killed = data.get('killed_mobs', [])
                self.killed_mobs = set()
                for item in killed:
                    self.killed_mobs.add((item[0], tuple(item[1])))
                
                # Restore map
                map_name = data.get('current_map_name', 'assets/maps/Surface.tmx')
                # Set current_map_name before load_map to prevent killed_mobs from being cleared
                self.current_map_name = map_name
                self.load_map(map_name)
                
                # Restore player state
                player_pos = data.get('player_pos', [200, 200])
                self.player.set_position(tuple(player_pos))
                self.respawn_point = tuple(player_pos)
                self.player.hp_current = data.get('player_hp', 100)
                
                print(f"Partie chargee depuis {filename}")
            except Exception as e:
                print(f"Erreur lors du chargement : {e}")
                self.load_map('assets/maps/Surface.tmx')
        else:
            print(f"Aucune sauvegarde trouvee pour le slot {slot}, nouvelle partie.")
            # Start fresh
            self.score = 0
            self.kill_count = 0
            self.respawn_count = 0
            self.play_time = 0.0
            self.boss_glace_dead = False
            self.boss_lave_dead = False
            self.killed_mobs.clear()
            self.load_map('assets/maps/Surface.tmx')
            self.player.hp_current = 100
            
        self.last_save_time = pygame.time.get_ticks()
        self.game_started = True
        self.is_paused = False

    def save_game(self):
        if not self.current_save_slot:
            return
            
        filename = f"save_{self.current_save_slot}.json"
        
        # Serialize killed_mobs
        killed_list = [[m[0], list(m[1])] for m in self.killed_mobs]
        
        data = {
            'save_name': getattr(self, 'current_save_name', None),
            'current_map_name': self.current_map_name,
            'player_pos': list(self.player.rect.topleft),
            'player_hp': self.player.hp_current,
            'score': self.score,
            'kill_count': self.kill_count,
            'respawn_count': self.respawn_count,
            'boss_glace_dead': self.boss_glace_dead,
            'boss_lave_dead': self.boss_lave_dead,
            'killed_mobs': killed_list,
            'play_time': self.play_time
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=4)
            print(f"Partie sauvegardee dans {filename}")
            self.save_indicator_timer = 180  # 3 seconds at 60 FPS
        except Exception as e:
            print(f"Erreur lors de la sauvegarde : {e}")

    def delete_save(self, slot):
        filename = f"save_{slot}.json"
        if os.path.exists(filename):
            try:
                os.remove(filename)
                print(f"Sauvegarde {slot} supprimee.")
            except Exception as e:
                print(f"Erreur lors de la suppression : {e}")
        self.menu.refresh_saves()
        self.menu.state = "save_selection"

    def fade_in(self, duration_ms=600):
        """Fondu depuis le noir vers le contenu actuel."""
        fade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        fade.fill((0, 0, 0))
        steps   = 40
        delay   = duration_ms // steps
        for i in range(steps + 1):
            alpha = max(0, 255 - int(255 * i / steps))
            self.draw(flip=False)
            fade.set_alpha(alpha)
            self.screen.blit(fade, (0, 0))
            pygame.display.flip()
            pygame.time.delay(delay)

    # ── Gestion réseau ────────────────────────────────────────────

    def _ensure_network(self):
        """Crée et connecte le Network si ce n'est pas déjà fait."""
        if self.network is None:
            self.network = Network()
            self.network.connect()

    def _start_multi_as_host(self):
        self._ensure_network()
        self.network.create_session()

    def _start_multi_as_client(self, code: str):
        self._ensure_network()
        self.network.join_session(code)

    def _launch_multi_game(self):
        """Démarre effectivement la partie multi (appelé quand les 2 joueurs sont prêts)."""
        self.is_multi      = True
        self.game_started  = True
        self.is_paused     = False
        
        # Configure les numéros de joueur en fonction du rôle
        if self.network and self.network.role == "client":
            self.player.player_num = 2
            self.player.load_assets()
            self.remote_player = RemotePlayer(self.player.rect.topleft, player_num=1)
            
            # Réinitialisation pour forcer la synchronisation avec le host
            self.current_map_name = ""
            self.killed_mobs.clear()
            self.boss_glace_dead = False
            self.boss_lave_dead = False
            self.score = 0
            self.kill_count = 0
            self.play_time = 0.0
        else:
            self.player.player_num = 1
            self.player.load_assets()
            self.remote_player = RemotePlayer(self.player.rect.topleft, player_num=2)

        self.visibles_sprites.add(self.remote_player)
        
        if getattr(self, 'network', None) and self.network.role == "host":
            self.network._send({"action": "start_multi_game"})

    def _network_update(self, dt):
        """Envoi/réception réseau — appelé chaque frame quand multi actif."""
        if self.network is None:
            return

        if self.network.role == "host":
            self.net_timer += dt
            if self.net_timer >= 1 / 60:          # 60 fois/seconde (très fluide)
                self.net_timer = 0
                state = {
                    "map_name": getattr(self, "current_map_name", ""),
                    "map_flag": getattr(self, "last_transition_flag", ""),
                    "boss_glace_dead": getattr(self, "boss_glace_dead", False),
                    "boss_lave_dead": getattr(self, "boss_lave_dead", False),
                    "p1_x":  self.player.rect.x,
                    "p1_y":  self.player.rect.y,
                    "p1_hp": self.player.hp_current,
                    "p1_status": self.player.status,
                }
                mobs_state = []
                boss_projs = []
                boss_shockwaves = []
                boss_hazards = []
                for m in self.monster_sprites:
                    hp_val = getattr(m, 'hp_current', getattr(m, 'hp', 0))
                    state_dict = {"id": getattr(m, 'id', -1), "x": m.rect.x, "y": m.rect.y, "hp": hp_val}
                    if hasattr(m, 'attack_state'):
                        state_dict["astate"] = m.attack_state
                        state_dict["phase"] = getattr(m, 'phase', 1)
                        if hasattr(m, 'attack_name'):
                            state_dict["aname"] = m.attack_name
                        for p in getattr(m, 'projectiles', []):
                            boss_projs.append({"x": p.rect.x, "y": p.rect.y})
                        for sw in getattr(m, 'shockwaves', []):
                            boss_shockwaves.append({"x": sw.rect.x, "y": sw.rect.y, "w": sw.rect.width, "h": sw.rect.height})
                        for hz in getattr(m, 'hazards', []):
                            boss_hazards.append({"x": hz.rect.x, "y": hz.rect.y, "w": hz.rect.width, "h": hz.rect.height})
                    mobs_state.append(state_dict)
                state["mobs"] = mobs_state
                state["boss_projs"] = boss_projs
                state["boss_shockwaves"] = boss_shockwaves
                state["boss_hazards"] = boss_hazards
                state["projs"] = [{"x": p.rect.x, "y": p.rect.y} for p in self.player.capacite.projectiles]
                state["enemy_projs"] = [{"x": p.rect.x, "y": p.rect.y} for p in self.enemy_proj_sprites]
                state["events_for_client"] = getattr(self, 'events_for_client', [])
                self.network.send_game_state(state)
                self.events_for_client = []

            for msg in self.network.poll():
                self.last_msg_time = pygame.time.get_ticks()
                if msg.get("action") == "input":
                    if self.remote_player:
                        self.remote_player.rect.x     = msg.get("p2_x", self.remote_player.rect.x)
                        self.remote_player.rect.y     = msg.get("p2_y", self.remote_player.rect.y)
                        self.remote_player.hp_current = msg.get("p2_hp", self.remote_player.hp_current)
                        self.remote_player.status     = msg.get("p2_status", self.remote_player.status)
                    self.remote_projs = msg.get("projs", [])
                    for dmg in msg.get("damage_events", []):
                        mob_id = dmg.get("mob_id")
                        mob = next((m for m in self.monster_sprites if getattr(m, 'id', None) == mob_id), None)
                        if mob:
                            mob.take_damage(dmg.get("amount", 20))
                elif msg.get("action") == "damage_mob":
                    self._respawn()
                elif msg.get("action") == "request_map_change":
                    req_flag = msg.get("req_flag", "none")
                    self.map_flag = req_flag if req_flag != "none" else None
                    if req_flag == "boss": self.coming_from_boss = True
                    elif req_flag == "glace": self.coming_from_glace = True
                    elif req_flag == "lave": self.coming_from_lave = True
                    elif req_flag == "tp_glace": self.coming_from_teleport = True
                    elif req_flag == "tp_lave": self.coming_from_teleport_lave = True
                    self.load_map(msg.get("dest"))

        # ── CLIENT : envoie son état (P2), reçoit l'état du host (P1) ──────
        elif self.network.role == "client":
            self.net_timer += dt
            if self.net_timer >= 1 / 60:
                self.net_timer = 0
                state = {
                    "p2_x":  self.player.rect.x,
                    "p2_y":  self.player.rect.y,
                    "p2_hp": self.player.hp_current,
                    "p2_status": self.player.status,
                    "projs": [{"x": p.rect.x, "y": p.rect.y} for p in self.player.capacite.projectiles],
                    "damage_events": self.pending_damage_events
                }
                self.network.send_client_state(state)
                self.pending_damage_events = []

            for msg in self.network.poll():
                self.last_msg_time = pygame.time.get_ticks()
                if msg.get("action") == "game_state":
                    if msg.get("boss_glace_dead"):
                        self.boss_glace_dead = True
                    if msg.get("boss_lave_dead"):
                        self.boss_lave_dead = True
                    remote_map = msg.get("map_name")
                    remote_flag = msg.get("map_flag", "")
                    if remote_map and getattr(self, 'current_map_name', "") != remote_map:
                        if remote_flag == "boss": self.coming_from_boss = True
                        elif remote_flag == "glace": self.coming_from_glace = True
                        elif remote_flag == "lave": self.coming_from_lave = True
                        elif remote_flag == "tp_glace": self.coming_from_teleport = True
                        elif remote_flag == "tp_lave": self.coming_from_teleport_lave = True
                        elif remote_flag == "mage": self.coming_from_mage = True
                        self.load_map(remote_map)

                    for ev in msg.get("events_for_client", []):
                        if ev["type"] in ("boss_proj", "boss_sw", "boss_hazard"):
                            self.player.take_damage(ev["damage"])
                            if ev["effect"] == "glace":
                                self.player.slow_timer = 180
                                self.player.slow_factor = 0.4
                            elif ev["effect"] == "lave":
                                self.player.burn_timer = 180
                                self.player.burn_dps = 3

                    # Le joueur distant pour le client = p1 dans l'état host
                    if self.remote_player:
                        self.remote_player.rect.x     = msg.get("p1_x", self.remote_player.rect.x)
                        self.remote_player.rect.y     = msg.get("p1_y", self.remote_player.rect.y)
                        self.remote_player.hp_current = msg.get("p1_hp", self.remote_player.hp_current)
                        self.remote_player.status     = msg.get("p1_status", self.remote_player.status)

                    self.remote_projs = msg.get("projs", [])
                    self.remote_enemy_projs = msg.get("enemy_projs", [])
                    self.remote_boss_projs = msg.get("boss_projs", [])
                    self.remote_boss_shockwaves = msg.get("boss_shockwaves", [])
                    self.remote_boss_hazards = msg.get("boss_hazards", [])

                    mobs_state = msg.get("mobs", [])
                    received_ids = {m["id"] for m in mobs_state}
                    for m_state in mobs_state:
                        mob = next((m for m in self.monster_sprites if getattr(m, 'id', None) == m_state["id"]), None)
                        if mob:
                            dx = m_state["x"] - mob.rect.x
                            dy = m_state["y"] - mob.rect.y
                            mob.vx = dx
                            mob.vy = dy
                            if dx > 0.2:
                                mob.facing_right = True
                            elif dx < -0.2:
                                mob.facing_right = False
                            
                            mob.rect.x = m_state["x"]
                            mob.rect.y = m_state["y"]
                            if hasattr(mob, 'hp_current'):
                                mob.hp_current = m_state["hp"]
                                if mob.hp_current <= 0 and not getattr(mob, 'dead', False):
                                    mob.dead = True
                                    if hasattr(mob, 'on_death'): mob.on_death()
                            elif hasattr(mob, 'hp'):
                                mob.hp = m_state["hp"]
                                if mob.hp <= 0 and getattr(mob, 'alive', True):
                                    mob.alive = False
                                    if hasattr(mob, 'on_death'): mob.on_death()
                                
                            if "astate" in m_state:
                                mob.attack_state = m_state["astate"]
                            if "phase" in m_state:
                                mob.phase = m_state["phase"]
                            if "aname" in m_state:
                                mob.attack_name = m_state["aname"]
                    for m in list(self.monster_sprites):
                        if getattr(m, 'id', None) not in received_ids:
                            if hasattr(m, 'hp_current'): m.hp_current = 0
                            elif hasattr(m, 'hp'): m.hp = 0
                            
                            if not getattr(m, 'client_death_processed', False):
                                m.client_death_processed = True
                                if hasattr(m, 'dead'): m.dead = True
                                if hasattr(m, 'alive'): m.alive = False
                                if hasattr(m, 'on_death'): m.on_death()
                                
                                if 'Esprit' in type(m).__name__:
                                    from monstre import ExplosionVFX
                                    ExplosionVFX(
                                        m.rect.center,
                                        getattr(m, 'COULEUR_CORPS', (255, 0, 0)),
                                        getattr(m, 'EXPLOSION_RADIUS', 25),
                                        getattr(m, 'vfx_groups', [self.visibles_sprites])
                                    )
                                    dist = pygame.math.Vector2(m.rect.center).distance_to(self.player.rect.center)
                                    if dist < getattr(m, 'EXPLOSION_RADIUS', 25) + 60:
                                        if hasattr(m, '_apply_explosion'):
                                            m._apply_explosion(self.player)
                elif msg.get("action") == "respawn_team":
                    self._respawn()

    # ── Spawn mobs ────────────────────────────────────────────────

    def _spawn_mob(self, obj_type, pos):
        groups    = [self.monster_sprites]
        mob_class = MOB_CLASSES[obj_type]
        if obj_type in ("GoblinArcher", "MechaGolem"):
            mob = mob_class(pos, groups, arrow_groups=[self.enemy_proj_sprites])
        elif obj_type == "GolemPierre":
            mob = mob_class(pos, groups, screen_shake_ref=self.shake_ref)
        elif obj_type in ("EspritFeu", "EspritGlace", "EspritFoudre", "EspritNature"):
            mob = mob_class(pos, groups, vfx_groups=[self.vfx_sprites])
        else:
            mob = mob_class(pos, groups)
        mob.sound_manager = getattr(self, 'sound_manager', None)
        mob.id = self.mob_counter
        self.mob_counter += 1
        return mob

    # ── Respawn / Game Over ───────────────────────────────────────

    def _respawn(self):
        """Réinitialise le joueur au dernier point de respawn."""
        if getattr(self.player, 'hp_current', 0) <= 0:
            self.respawn_count += 1
        self.death_time = None
        self.player.hp_current = self.player.hp_max
        self.player.vel_y = 0
        self.killed_mobs.clear()
        
        if self.killed_by_boss and getattr(self, 'zone_boss_map', None):
            self.load_map(self.zone_boss_map)
            self.player.set_position(self.zone_boss_respawn_point)
            self.respawn_point = self.zone_boss_respawn_point
        elif self.current_map_name:
            self.load_map(self.current_map_name)

    def _go_to_main_menu(self):
        """Retourne au menu principal sans réinitialiser la partie."""
        self._respawn()          # remet le joueur en vie pour éviter un état incohérent
        self.is_paused    = True
        self.game_started = False
        self.menu.state   = "main"
        self.menu_input_blocked = 10   # ignore les clics pendant 10 frames
        
        # Reset local player to player 1 assets
        if self.player:
            self.player.player_num = 1
            self.player.load_assets()

    # ── Update ────────────────────────────────────────────────────

    def update(self, dt):
        if self.menu_input_blocked > 0:
            self.menu_input_blocked -= 1

        if self.save_indicator_timer > 0:
            self.save_indicator_timer -= 1

        if self.is_multi and self.network:
            # Initialise le timer de message si pas encore fait
            if getattr(self, 'last_msg_time', 0) == 0:
                self.last_msg_time = pygame.time.get_ticks()
            
            # Déconnexion par timeout (15 secondes sans message, compense les temps de chargement)
            if pygame.time.get_ticks() - self.last_msg_time > 15000:
                self.network.connected = False

            if not self.network.connected:
                print("Déconnexion détectée, retour au menu...")
                self.is_multi = False
                self.game_started = False
                self.is_paused = True
                self.menu.state = "main"
                self.network = None
                self.last_msg_time = 0
                
                # Reset local player to player 1 assets
                if self.player:
                    self.player.player_num = 1
                    self.player.load_assets()
                return

            # Réseau - doit toujours tourner pour éviter le timeout
            self._network_update(dt)

        if not self.is_paused:
            if getattr(self, 'game_started', False) and "Fin" not in self.current_map_name and self.player.hp_current > 0:
                self.play_time += dt * 1000.0
                
            if getattr(self, 'show_credits', False):
                self.credits_scroll_y -= dt * 60.0
                if self.credits_scroll_y < -3500:
                    self.show_credits = False
                    self.credits_finished = True
            elif getattr(self, 'is_end_game', False):
                self.end_game_timer += dt

            if self.game_started and self.current_save_slot:
                if pygame.time.get_ticks() - self.last_save_time >= 120000:
                    self.save_game()
                    self.last_save_time = pygame.time.get_ticks()
            # En mode client on laisse quand même le joueur se mettre à jour
            # visuellement (la position sera écrasée par l'état réseau).
            # On le met toujours à jour pour qu'il puisse jouer son animation de mort s'il meurt.
            self.player.update(self.obstacle_sprites, self.ladder_sprites, self.plateforme_sprites, dt)
                
            if self.is_multi and getattr(self, 'remote_player', None):
                self.remote_player.update(dt)
                
            # Check transition to Zone1 (Single-player or Host loads directly, Client requests)
            if pygame.sprite.spritecollideany(self.player, self.transition_sprites):
                if self.is_multi and self.network and self.network.role == "client":
                    self.network._send({"action": "request_map_change", "dest": 'assets/maps/Zone1.tmx'})
                else:
                    self.load_map('assets/maps/Zone1.tmx')

            # NPC
            for npc in self.npc_sprites:
                npc.update(self.player.rect, self.dialogue_box)

            # Portes (Hint)
            for door in self.doors:
                # On agrandit virtuellement la hitbox de la porte pour le hint (pour qu'il apparaisse un peu avant)
                if self.player.hitbox.colliderect(door['rect'].inflate(64, 64)):
                    self.dialogue_box.show("Appuyez sur [E] pour entrer")
                    break
            else:
                if self.dialogue_box.text == "Appuyez sur [E] pour entrer":
                    self.dialogue_box.hide()

            # Camera
            self.camera.update(self.player.rect)

            # Monstres
            for m in list(self.monster_sprites):
                if not self.is_multi or self.network.role == "host":
                    target_player = self.player
                    if self.is_multi and getattr(self, 'remote_player', None) and self.remote_player.hp_current > 0:
                        dist_local = pygame.math.Vector2(m.rect.center).distance_to(self.player.rect.center)
                        dist_remote = pygame.math.Vector2(m.rect.center).distance_to(self.remote_player.rect.center)
                        if dist_remote < dist_local:
                            target_player = self.remote_player

                    if hasattr(m, 'attack_state'):
                        m.update(target_player.rect, dt)
                    else:
                        m.update(target_player, self.obstacle_sprites)
                else:
                    if getattr(m, 'contact_timer', 0) > 0:
                        m.contact_timer -= 1
                    
                    if getattr(m, 'dead', False) or not getattr(m, 'alive', True):
                        if hasattr(m, 'attack_state'):
                            m.update(self.player.rect, dt)
                        else:
                            m.update(self.player, self.obstacle_sprites)
                    elif hasattr(m, '_update_visual'):
                        m._update_visual(dt * 1000)

                if hasattr(m, 'heal_allies'):
                    m.heal_allies(self.monster_sprites)

                is_m_dead = getattr(m, 'dead', False) or not getattr(m, 'alive', True)
                if not is_m_dead and m.rect.colliderect(self.player.hitbox) and self.player.hp_current > 0:
                    if getattr(m, 'contact_timer', 0) <= 0:
                        self.player.take_damage(getattr(m, 'ATTACK_DAMAGE', 10))
                        m.contact_timer = getattr(m, 'CONTACT_COOLDOWN', 60)
                        if self.player.hp_current <= 0:
                            self.killed_by_boss = ('Boss' in type(m).__name__ or hasattr(m, 'attack_state'))

                if not is_m_dead and hasattr(m, 'attack_state'):
                    if not hasattr(self, 'events_for_client'): self.events_for_client = []
                    # Collision pour les projectiles et ondes de choc internes du boss
                    for p in list(m.projectiles):
                        if p.rect.colliderect(self.player.hitbox) and self.player.hp_current > 0:
                            self.player.take_damage(15)
                            if 'Glacius' in type(m).__name__:
                                self.player.slow_timer = 180
                                self.player.slow_factor = 0.4
                            p.kill()
                            if self.player.hp_current <= 0:
                                self.killed_by_boss = True
                        elif self.is_multi and getattr(self, 'remote_player', None) and p.rect.colliderect(self.remote_player.rect) and self.remote_player.hp_current > 0:
                            p.kill()
                            effect = "glace" if 'Glacius' in type(m).__name__ else "lave"
                            self.events_for_client.append({"type": "boss_proj", "damage": 15, "effect": effect})

                    for sw in m.shockwaves:
                        if sw.rect.colliderect(self.player.hitbox) and self.player.hp_current > 0:
                            if getattr(sw, 'hit_player', False) == False:
                                self.player.take_damage(20)
                                if 'Glacius' in type(m).__name__:
                                    self.player.slow_timer = 180
                                    self.player.slow_factor = 0.25
                                sw.hit_player = True
                                if self.player.hp_current <= 0:
                                    self.killed_by_boss = True
                        elif self.is_multi and getattr(self, 'remote_player', None) and sw.rect.colliderect(self.remote_player.rect) and self.remote_player.hp_current > 0:
                            if not getattr(sw, 'hit_remote', False):
                                effect = "glace" if 'Glacius' in type(m).__name__ else "lave"
                                self.events_for_client.append({"type": "boss_sw", "damage": 20, "effect": effect})
                                sw.hit_remote = True

                    for h in m.hazards:
                        if h.rect.colliderect(self.player.hitbox) and self.player.hp_current > 0:
                            self.player.take_damage(getattr(h, 'damage', 1))
                            if self.player.hp_current <= 0:
                                self.killed_by_boss = True
                        elif self.is_multi and getattr(self, 'remote_player', None) and h.rect.colliderect(self.remote_player.rect) and self.remote_player.hp_current > 0:
                            effect = "glace" if 'Glacius' in type(m).__name__ else "lave"
                            self.events_for_client.append({"type": "boss_hazard", "damage": getattr(h, 'damage', 1), "effect": effect})

                is_m_dead_finished = (getattr(m, 'dead', False) and getattr(m, 'death_finished', True)) or (hasattr(m, 'alive') and not m.alive and getattr(m, 'death_finished', True))
                if is_m_dead_finished:
                    mob_type = type(m).__name__
                    self.score      += MOB_XP.get(mob_type, 10)
                    self.kill_count += 1
                    color = MOB_COLORS.get(mob_type, WHITE)
                    for _ in range(16):
                        self.particles.append(
                            Particle(m.rect.centerx, m.rect.centery, color))
                    
                    if hasattr(m, 'attack_state') and mob_type == 'Glacius':
                        self.boss_glace_dead = True
                        self.player.hp_current = self.player.hp_max
                        self.boss_death_pos = (m.rect.centerx, m.rect.bottom - 64)
                        
                        msg = "Bravo, tu as vaincu le boss !|Je te téléporte à la porte suivante."
                        npc = NPC(self.boss_death_pos, msg, [self.visibles_sprites, self.npc_sprites], on_end_callback=self.teleport_from_boss)
                    elif hasattr(m, 'attack_state') and mob_type == 'Pyros':
                        self.boss_lave_dead = True
                        self.player.hp_current = self.player.hp_max
                        self.boss_death_pos = (m.rect.centerx, m.rect.bottom - 64)
                        msg = "Bravo, tu as vaincu le gardien de la lave !|Je te téléporte hors d'ici."
                        npc = NPC(self.boss_death_pos, msg, [self.visibles_sprites, self.npc_sprites], on_end_callback=self.teleport_from_boss_lave)
                    else:
                        if hasattr(m, 'spawn_pos'):
                            self.killed_mobs.add((self.current_map_name, m.spawn_pos))
                            
                    m.kill()

            # Projectiles joueur → monstres
            for proj in list(self.player.capacite.projectiles):
                for m in list(self.monster_sprites):
                    is_dead = getattr(m, 'dead', False) or not getattr(m, 'alive', True)
                    if not is_dead and proj.rect.colliderect(m.rect):
                        proj.kill()
                        if not self.is_multi or self.network.role == "host":
                            m.take_damage(20)
                        elif self.network.role == "client":
                            if self.network:
                                self.pending_damage_events.append({"mob_id": getattr(m, 'id', -1), "amount": 20})
                        break

            # Mise à jour des projectiles ennemis
            self.enemy_proj_sprites.update(self.obstacle_sprites)

            # Projectiles ennemis → joueur
            for ep in list(self.enemy_proj_sprites):
                if ep.rect.colliderect(self.player.hitbox) and self.player.hp_current > 0:
                    self.player.take_damage(getattr(ep, 'damage', 10))
                    ep.kill()
                    if type(ep).__name__ == "BossProjectile":
                        self.killed_by_boss = True
                    else:
                        self.killed_by_boss = False
            
            if self.is_multi and self.network.role == "client":
                for proj in getattr(self, "remote_enemy_projs", []):
                    r = pygame.Rect(proj["x"], proj["y"], 16, 16)
                    if self.player.hitbox.colliderect(r) and self.player.hp_current > 0:
                        self.player.take_damage(10)
                        self.killed_by_boss = False
                for bp in getattr(self, "remote_boss_projs", []):
                    r = pygame.Rect(bp["x"], bp["y"], 16, 16)
                    if self.player.hitbox.colliderect(r) and self.player.hp_current > 0:
                        self.player.take_damage(15)
                        self.killed_by_boss = True
                for sw in getattr(self, "remote_boss_shockwaves", []):
                    r = pygame.Rect(sw["x"], sw["y"], sw.get("w", 32), sw.get("h", 32))
                    if self.player.hitbox.colliderect(r) and self.player.hp_current > 0:
                        self.player.take_damage(20)
                        self.killed_by_boss = True
                for hz in getattr(self, "remote_boss_hazards", []):
                    r = pygame.Rect(hz["x"], hz["y"], hz.get("w", 32), hz.get("h", 32))
                    if self.player.hitbox.colliderect(r) and self.player.hp_current > 0:
                        self.player.take_damage(1)
                        self.killed_by_boss = True

            # VFX + particules
            self.vfx_sprites.update()
            for p in self.particles:
                p.update()
            self.particles = [p for p in self.particles if p.life > 0]

    # ── Draw ──────────────────────────────────────────────────────

    def draw_health_bar(self):
        x, y  = 50, 50
        ratio = max(0, self.player.hp_current / self.player.hp_max)
        bar_w = self.player.health_bar_length
        
        # Fond et bordure
        pygame.draw.rect(self.screen, (40, 40, 40), (x - 4, y - 4, bar_w + 8, 28), border_radius=6)
        pygame.draw.rect(self.screen, (130, 0, 0), (x, y, bar_w, 20), border_radius=4)
        
        # Barre de vie
        if ratio > 0:
            pygame.draw.rect(self.screen, (0, 200, 50), (x, y, int(bar_w * ratio), 20), border_radius=4)
            
        # Texte PV sous la barre
        hp_text = self.font_hud.render(f"Joueur 1 : {int(self.player.hp_current)} / {int(self.player.hp_max)} PV", True, WHITE)
        hp_text_shadow = self.font_hud.render(f"Joueur 1 : {int(self.player.hp_current)} / {int(self.player.hp_max)} PV", True, BLACK)
        text_rect = hp_text.get_rect(midleft=(x, y + 36))
        self.screen.blit(hp_text_shadow, (text_rect.x + 1, text_rect.y + 1))
        self.screen.blit(hp_text, text_rect)

    def draw_status_indicators(self):
        y = 90
        p = self.player
        if p.is_poisoned and p.poison_timer > 0:
            s = p.poison_timer // 60 + 1
            self.screen.blit(
                self.font_hud.render(f"POISON {s}s", True, (180, 0, 255)), (50, y))
            y += 24
        if p.slow_timer > 0:
            s = p.slow_timer // 60 + 1
            self.screen.blit(
                self.font_hud.render(f"LENT {s}s", True, (0, 200, 255)), (50, y))
            y += 24
        if p.burn_timer > 0:
            s = p.burn_timer // 60 + 1
            self.screen.blit(
                self.font_hud.render(f"BRULURE {s}s", True, (255, 120, 0)), (50, y))

    def draw_remote_health_bar(self):
        """Barre de vie du joueur distant (haut droite)."""
        if not getattr(self, 'remote_player', None):
            return
        x = SCREEN_WIDTH - 280
        y = 50
        ratio = max(0, self.remote_player.hp_current / self.remote_player.hp_max)
        bar_w = 200
        
        # Fond et bordure
        pygame.draw.rect(self.screen, (40, 40, 40), (x - 4, y - 4, bar_w + 8, 28), border_radius=6)
        pygame.draw.rect(self.screen, (130, 0, 0), (x, y, bar_w, 20), border_radius=4)
        
        # Barre de vie allié (bleu)
        if ratio > 0:
            pygame.draw.rect(self.screen, (0, 100, 255), (x, y, int(bar_w * ratio), 20), border_radius=4)
            
        # Texte PV allié sous la barre
        hp_text = self.font_hud.render(f"Joueur 2 : {int(self.remote_player.hp_current)} / {int(self.remote_player.hp_max)} PV", True, WHITE)
        hp_text_shadow = self.font_hud.render(f"Joueur 2 : {int(self.remote_player.hp_current)} / {int(self.remote_player.hp_max)} PV", True, BLACK)
        text_rect = hp_text.get_rect(midleft=(x, y + 36))
        self.screen.blit(hp_text_shadow, (text_rect.x + 1, text_rect.y + 1))
        self.screen.blit(hp_text, text_rect)

    def draw(self, flip=True):
        if self.is_paused:
            self.menu.draw(self.game_started, self.network)
        else:
            shake = 0
            if self.shake_ref[0] > 0:
                self.shake_ref[0] -= 1
                shake = random.randint(-6, 6)

            self.screen.blit(
                self.background_image,
                (-int(self.camera.offset.x) + shake,
                 -int(self.camera.offset.y) + shake))

            for sprite in self.visibles_sprites:
                self.screen.blit(sprite.image, self.camera.apply(sprite.rect))

            for projectile in self.player.capacite.projectiles:
                self.screen.blit(projectile.image, self.camera.apply(projectile.rect))

            for ep in self.enemy_proj_sprites:
                self.screen.blit(ep.image, self.camera.apply(ep.rect))

            for m in self.monster_sprites:
                if hasattr(m, 'attack_state'):
                    m.draw(self.screen, -int(self.camera.offset.x), -int(self.camera.offset.y))
                    m.draw_health_bar(self.screen)
                else:
                    self.screen.blit(m.image, self.camera.apply(m.rect))
                    bar_rect = m.rect.move(-int(self.camera.offset.x),
                                           -int(self.camera.offset.y))
                    bw, bh = bar_rect.width, 6
                    bx, by = bar_rect.left, bar_rect.top - 12
                    ratio  = max(0.0, m.hp_current / m.hp_max)
                    pygame.draw.rect(self.screen, (139, 0, 0), (bx, by, bw, bh))
                    pygame.draw.rect(self.screen, (0, 220, 0), (bx, by, int(bw * ratio), bh))
                    pygame.draw.rect(self.screen, BLACK,        (bx, by, bw, bh), 1)

            is_boss_fight = any(hasattr(m, 'attack_state') for m in self.monster_sprites)
            if is_boss_fight:
                px = SCREEN_WIDTH - 120
                py = SCREEN_HEIGHT - 120
                
                # Detour blanc si primé
                if getattr(self.player, 'potion_primed', False):
                    pygame.draw.rect(self.screen, WHITE, (px - 5, py - 5, 74, 74), 3, border_radius=5)
                    text = self.potion_font.render(f"{self.player.potions_current} RESTANTES", True, WHITE)
                    self.screen.blit(text, (px - text.get_width() // 2 + 32, py - 30))
                
                # Nombre si non primé mais visible
                elif self.player.potions_current > 0:
                    text = self.potion_font.render(f"x{self.player.potions_current}", True, WHITE)
                    self.screen.blit(text, (px + 64, py + 32))
                else:
                    text = self.potion_font.render(f"0", True, RED)
                    self.screen.blit(text, (px + 64, py + 32))
                    
                self.screen.blit(self.potion_img, (px, py))

            for vfx in self.vfx_sprites:
                self.screen.blit(vfx.image, self.camera.apply(vfx.rect))

            for p in self.particles:
                p.draw(self.screen)

            if self.is_multi:
                for proj in getattr(self, "remote_projs", []):
                    r = pygame.Rect(proj["x"], proj["y"], 16, 16)
                    r = self.camera.apply(r)
                    pygame.draw.ellipse(self.screen, (255, 150, 0), r)
                for proj in getattr(self, "remote_enemy_projs", []):
                    r = pygame.Rect(proj["x"], proj["y"], 16, 16)
                    r = self.camera.apply(r)
                    pygame.draw.ellipse(self.screen, (255, 50, 0), r)
                for bp in getattr(self, "remote_boss_projs", []):
                    r = pygame.Rect(bp["x"], bp["y"], 16, 16)
                    r = self.camera.apply(r)
                    pygame.draw.ellipse(self.screen, (0, 255, 255), r)
                for sw in getattr(self, "remote_boss_shockwaves", []):
                    r = pygame.Rect(sw["x"], sw["y"], sw.get("w", 32), sw.get("h", 32))
                    r = self.camera.apply(r)
                    pygame.draw.rect(self.screen, (200, 200, 255), r, 3)
                for hz in getattr(self, "remote_boss_hazards", []):
                    r = pygame.Rect(hz["x"], hz["y"], hz.get("w", 32), hz.get("h", 32))
                    r = self.camera.apply(r)
                    pygame.draw.rect(self.screen, (255, 100, 0), r, 2)

            self.dialogue_box.draw()
            self.draw_health_bar()
            self.draw_status_indicators()

            if self.is_multi:
                self.draw_remote_health_bar()

            score_txt = self.font_hud.render(
                f"Score : {self.score}   Kills : {self.kill_count}   Respawns : {self.respawn_count}", True, WHITE)
            self.screen.blit(score_txt, (SCREEN_WIDTH - score_txt.get_width() - 20, 20))

            if getattr(self, 'game_started', False):
                timer_txt = self.font_hud.render(format_time(self.play_time), True, YELLOW)
                self.screen.blit(timer_txt, (SCREEN_WIDTH // 2 - timer_txt.get_width() // 2, 20))

            if self.player.hp_current <= 0:
                if self.death_time is None:
                    self.death_time = pygame.time.get_ticks()
                
                time_since_death = pygame.time.get_ticks() - self.death_time
                if time_since_death >= 1000:
                    progress = min(1.0, (time_since_death - 1000) / 1000.0)
                    
                    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                    overlay.fill((0, 0, 0, int(180 * progress)))
                    self.screen.blit(overlay, (0, 0))

                    txt = self.font_title.render("GAME OVER", True, RED)
                    txt.set_alpha(int(255 * progress))
                    self.screen.blit(txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2,
                                           SCREEN_HEIGHT // 2 - 80))

                    mouse_pos = pygame.mouse.get_pos()
                    btn_font  = pygame.font.SysFont("consolas", 28, bold=True)

                    # Bouton RÉAPPARAITRE
                    btn_surf_r = pygame.Surface((self.btn_respawn.width, self.btn_respawn.height), pygame.SRCALPHA)
                    color_r = (0, 160, 60, int(255 * progress)) if self.btn_respawn.collidepoint(mouse_pos) else (0, 110, 40, int(255 * progress))
                    pygame.draw.rect(btn_surf_r, color_r, btn_surf_r.get_rect(), border_radius=14)
                    pygame.draw.rect(btn_surf_r, (*WHITE, int(255 * progress)), btn_surf_r.get_rect(), 3, border_radius=14)
                    lbl_r = btn_font.render("REAPPARAITRE", True, WHITE)
                    lbl_r.set_alpha(int(255 * progress))
                    btn_surf_r.blit(lbl_r, lbl_r.get_rect(center=btn_surf_r.get_rect().center))
                    self.screen.blit(btn_surf_r, self.btn_respawn.topleft)

                    # Bouton MENU
                    btn_surf_m = pygame.Surface((self.btn_gameover_menu.width, self.btn_gameover_menu.height), pygame.SRCALPHA)
                    color_m = (0, 120, 210, int(255 * progress)) if self.btn_gameover_menu.collidepoint(mouse_pos) else (0, 80, 160, int(255 * progress))
                    pygame.draw.rect(btn_surf_m, color_m, btn_surf_m.get_rect(), border_radius=14)
                    pygame.draw.rect(btn_surf_m, (*WHITE, int(255 * progress)), btn_surf_m.get_rect(), 3, border_radius=14)
                    lbl_m = btn_font.render("MENU", True, WHITE)
                    lbl_m.set_alpha(int(255 * progress))
                    btn_surf_m.blit(lbl_m, lbl_m.get_rect(center=btn_surf_m.get_rect().center))
                    self.screen.blit(btn_surf_m, self.btn_gameover_menu.topleft)

            if self.save_indicator_timer > 0:
                text = self.save_font.render("Sauvegarde automatique...", True, WHITE)
                self.screen.blit(text, (SCREEN_WIDTH - text.get_width() - 50, 50))
                
                t = pygame.time.get_ticks() / 200.0
                cx_wheel = SCREEN_WIDTH - 25
                cy_wheel = 60
                radius = 10
                rect = pygame.Rect(cx_wheel - radius, cy_wheel - radius, radius * 2, radius * 2)
                start_angle = t
                end_angle = t + math.pi
                pygame.draw.arc(self.screen, WHITE, rect, start_angle, end_angle, 3)

            if self.is_multi and getattr(self, 'show_menu_overlay', False):
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 160))
                self.screen.blit(overlay, (0, 0))
                self.menu.draw(self.game_started, self.network)
                
            if getattr(self, 'show_credits', False):
                # Affichage des crédits (texte qui défile)
                y_offset = self.credits_scroll_y
                for line in CREDITS_TEXT:
                    if y_offset > -100 and y_offset < SCREEN_HEIGHT + 100:
                        if line.isupper() and "MERCI" not in line and "YGALE" not in line:
                            txt = self.credits_font_title.render(line, True, YELLOW)
                        else:
                            txt = self.credits_font_text.render(line, True, WHITE)
                        self.screen.blit(txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2, y_offset))
                    y_offset += 45
            elif getattr(self, 'is_end_game', False) and getattr(self, 'designfin_img', None):
                alpha = min(255, int((self.end_game_timer / 10.0) * 255))
                if alpha > 0:
                    self.designfin_img.set_alpha(alpha)
                    self.screen.blit(self.designfin_img, (0, 0))
                    
                    stat_font = pygame.font.SysFont("consolas", 40, bold=True)
                    chrono_txt = stat_font.render(f"{format_time(self.play_time)}", True, WHITE)
                    score_txt = stat_font.render(f"{self.score}", True, WHITE)
                    kills_txt = stat_font.render(f"{self.kill_count}", True, WHITE)
                    
                    chrono_txt.set_alpha(alpha)
                    score_txt.set_alpha(alpha)
                    kills_txt.set_alpha(alpha)
                    
                    cx = SCREEN_WIDTH // 2
                    cy_box = 690  # Descente légère des stats dans les encadrés
                    
                    # Espacement horizontal approximatif
                    offset_x = 280
                    
                    self.screen.blit(chrono_txt, (cx - offset_x - chrono_txt.get_width() // 2, cy_box - chrono_txt.get_height() // 2))
                    self.screen.blit(score_txt, (cx - score_txt.get_width() // 2, cy_box - score_txt.get_height() // 2))
                    self.screen.blit(kills_txt, (cx + offset_x - kills_txt.get_width() // 2, cy_box - kills_txt.get_height() // 2))
                    
                    if alpha == 255:
                        mouse_pos = pygame.mouse.get_pos()
                        if not getattr(self, 'credits_finished', False):
                            if self.btn_credits.collidepoint(mouse_pos):
                                hover_surf = pygame.Surface((self.btn_credits.width, self.btn_credits.height), pygame.SRCALPHA)
                                pygame.draw.rect(hover_surf, (255, 255, 255, 30), hover_surf.get_rect(), border_radius=10)
                                self.screen.blit(hover_surf, self.btn_credits.topleft)
                        else:
                            btn_font = pygame.font.SysFont("consolas", 28, bold=True)
                            btn_surf_m = pygame.Surface((self.btn_end_menu.width, self.btn_end_menu.height), pygame.SRCALPHA)
                            color_m = (0, 120, 210, 255) if self.btn_end_menu.collidepoint(mouse_pos) else (0, 80, 160, 255)
                            pygame.draw.rect(btn_surf_m, color_m, btn_surf_m.get_rect(), border_radius=14)
                            pygame.draw.rect(btn_surf_m, WHITE, btn_surf_m.get_rect(), 3, border_radius=14)
                            lbl_m = btn_font.render("MENU PRINCIPAL", True, WHITE)
                            btn_surf_m.blit(lbl_m, lbl_m.get_rect(center=btn_surf_m.get_rect().center))
                            self.screen.blit(btn_surf_m, self.btn_end_menu.topleft)

        if flip:
            pygame.display.flip()

    # ── Boucle principale ─────────────────────────────────────────

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == getattr(self.sound_manager, '_loop_event', -1):
                    try:
                        pygame.mixer.music.load(self.sound_manager._current_boucle)
                        pygame.mixer.music.set_volume(self.sound_manager.music_base_volume * self.sound_manager.global_volume)
                        pygame.mixer.music.play(-1)
                    except pygame.error:
                        pass

                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    if self.game_started:
                        if self.is_multi:
                            self.show_menu_overlay = not getattr(self, 'show_menu_overlay', False)
                            self.menu.state = "main"
                            self.player.input_locked = self.show_menu_overlay
                        else:
                            self.is_paused = not self.is_paused
                            self.menu.state = "main"

                if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
                    if not self.is_paused and self.player.hp_current > 0:
                        map_before = getattr(self, 'current_map_name', None)
                        # Interaction PNJ
                        for npc in self.npc_sprites:
                            if hasattr(npc, 'interact'):
                                npc.interact()
                        
                        if getattr(self, 'current_map_name', None) != map_before:
                            continue
                        
                        # Interaction Portes
                        for door in self.doors:
                            if self.player.hitbox.colliderect(door['rect'].inflate(64, 64)):
                                if door['type'] == 'porteglace' and not self.boss_glace_dead:
                                    self.dialogue_box.show("La porte est verrouillée...", owner=None)
                                    break
                                elif door['type'] == 'porte_to_glace' and not self.boss_lave_dead:
                                    self.dialogue_box.show("La porte vers la zone de glace est verrouillée...\nIl faut vaincre le boss de lave.", owner=None)
                                    break
                                
                                if 'boss' in self.current_map_name:
                                    self.coming_from_boss = True
                                    self.map_flag = "boss"
                                elif 'glace' in self.current_map_name:
                                    self.coming_from_glace = True
                                    self.map_flag = "glace"
                                elif 'lave' in self.current_map_name.lower():
                                    self.coming_from_lave = True
                                    self.map_flag = "lave"
                                
                                if self.is_multi and self.network and self.network.role == "client":
                                    req_flag = "none"
                                    if getattr(self, 'coming_from_boss', False): req_flag = "boss"
                                    elif getattr(self, 'coming_from_glace', False): req_flag = "glace"
                                    elif getattr(self, 'coming_from_lave', False): req_flag = "lave"
                                    self.network._send({"action": "request_map_change", "dest": door['dest'], "req_flag": req_flag})
                                else:
                                    self.load_map(door['dest'])
                                break

                # Potion
                potion_key = self.player.keybinds.get("potion", pygame.K_r)
                if event.type == pygame.KEYDOWN and event.key == potion_key:
                    if not self.is_paused and self.player.hp_current > 0:
                        is_boss_fight = any(hasattr(m, 'attack_state') for m in self.monster_sprites)
                        if is_boss_fight:
                            if self.player.potions_current > 0:
                                if not self.player.potion_primed:
                                    self.player.potion_primed = True
                                else:
                                    self.player.potion_primed = False
                                    self.player.potions_current -= 1
                                    self.player.hp_current = min(self.player.hp_max, self.player.hp_current + self.player.hp_max // 3)
                                    if self.sound_manager:
                                        try:
                                            self.sound_manager.play("heal")
                                        except:
                                            pass

                if getattr(self, 'is_end_game', False) and not getattr(self, 'show_credits', False):
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        if not getattr(self, 'credits_finished', False):
                            if self.btn_credits.collidepoint(event.pos):
                                self.show_credits = True
                                if getattr(self, 'sound_manager', None):
                                    try: self.sound_manager.play('clic')
                                    except: pass
                        else:
                            if self.btn_end_menu.collidepoint(event.pos):
                                if getattr(self, 'sound_manager', None):
                                    try: self.sound_manager.play('clic')
                                    except: pass
                                self._go_to_main_menu()

                # ── Boutons Game Over ───────────────────────────────
                if (not self.is_paused
                        and self.player.hp_current <= 0
                        and self.death_time is not None
                        and pygame.time.get_ticks() - self.death_time >= 2000
                        and event.type == pygame.MOUSEBUTTONDOWN
                        and event.button == 1):
                    if self.btn_respawn.collidepoint(event.pos):
                        self._respawn()
                        if self.is_multi and self.network:
                            self.network._send({"action": "respawn_team"})
                    elif self.btn_gameover_menu.collidepoint(event.pos):
                        self._go_to_main_menu()

                if (self.is_paused or (self.is_multi and getattr(self, 'show_menu_overlay', False))) and self.menu_input_blocked == 0:
                    action = self.menu.handle_input(event, self.network)

                    # Slider volume — action est un tuple ("volume_changed", valeur)
                    if isinstance(action, tuple) and action[0] == "volume_changed":
                        self.sound_manager.set_volume(action[1])

                    elif isinstance(action, tuple) and action[0] == "keybinds_changed":
                        if self.player:
                            self.player.keybinds = action[1]

                    elif action == "open_modes":
                        if self.game_started:
                            if self.is_multi:
                                self.show_menu_overlay = False
                                self.player.input_locked = False
                            else:
                                self.is_paused = False
                        else:
                            self.menu.state = "mode_selection"

                    elif action == "respawn":
                        if self.game_started and self.current_save_slot:
                            print(f"Rechargement de la dernière sauvegarde (Slot {self.current_save_slot}) !")
                            self.load_game(self.current_save_slot)
                            self.is_paused = False

                    elif isinstance(action, tuple) and action[0] == "play_story":
                        slot = action[1]
                        print(f"Mode Histoire lancé (Slot {slot}) !")
                        self.load_game(slot)
                        
                    elif isinstance(action, tuple) and action[0] == "new_game":
                        slot = action[1]
                        save_name = action[2] if len(action) > 2 else None
                        print(f"Nouvelle partie lancée (Slot {slot}) !")
                        self.load_game(slot)
                        if save_name:
                            self.current_save_name = save_name
                        self.save_game()
                        
                    elif isinstance(action, tuple) and action[0] == "delete_save":
                        slot = action[1]
                        self.delete_save(slot)

                    # ── HOST crée une session ───────────────────────
                    elif action == "multi_create_session":
                        print("Création de session multi...")
                        self._start_multi_as_host()

                    # ── CLIENT rejoint une session ──────────────────
                    elif action == "multi_join_session":
                        code = self.menu.input_code
                        print(f"Tentative de rejoindre le salon : {code}")
                        self._start_multi_as_client(code)

                    elif action == "launch_multi_coop":
                        self._launch_multi_game()
                        
                    elif action == "launch_multi_pvp":
                        self.load_map('assets/maps/PVP.tmx')
                        self._launch_multi_game()
                        
                    elif action == "disconnect_multi":
                        if getattr(self, 'network', None):
                            self.network.close()
                            self.network = None
                        self.menu.state = "multi_lobby"

                    elif action == "quit":
                        if self.game_started:
                            if self.is_multi and self.network:
                                try:
                                    import asyncio
                                    if self.network.ws and self.network.connected:
                                        asyncio.run_coroutine_threadsafe(self.network.ws.close(), self.network._loop)
                                except Exception:
                                    pass
                                self.network.connected = False
                                self.network = None
                                self.is_multi = False
                            self._go_to_main_menu()
                            self.show_menu_overlay = False
                        else:
                            pygame.quit()
                            sys.exit()

            # ── Vérification état réseau (en dehors des events) ─────
            if self.network is not None and self.is_paused:
                # HOST : la partie démarre quand le pair a rejoint
                if (self.network.role == "host"
                        and self.menu.state == "multi_host_wait"
                        and self.network.peer_joined):
                    print("Pair connecté ! Choix du mode multi.")
                    self.menu.state = "multi_mode_final"

                # CLIENT : la partie démarre dès que le serveur confirme "joined"
                elif (self.network.role == "client"
                        and self.menu.state == "multi_join_wait"
                        and self.network.peer_joined):
                    print("Code valide ! En attente de l'hôte.")
                    self.menu.state = "multi_client_wait_start"
                    
                # CLIENT en attente du démarrage par l'hôte
                elif (self.network.role == "client"
                        and self.menu.state == "multi_client_wait_start"):
                    for msg in self.network.poll():
                        # L'hôte envoie continuellement l'état du jeu (game_state) une fois la partie lancée
                        if msg.get("action") == "game_state" or msg.get("action") == "start_multi_game":
                            print("L'hôte a lancé la partie !")
                            self._launch_multi_game()
                            # On remet le message pour qu'il soit traité par le update normal
                            self.network.incoming.insert(0, msg)
                            break

            self.update(dt)
            self.draw()

#LANCEMENT DU JEU##########################################################################

if __name__ == '__main__':
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("SMILE")
    clock  = pygame.time.Clock()

    intro_path = os.path.join(ROOT_DIR, "assets/video/videointro.mp4")
    IntroVideo(screen, clock, intro_path).play()

    game = Game(screen, clock)
    game.sound_manager.start_music()
    game.fade_in()
    game.run()
