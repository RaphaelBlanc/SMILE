#SECTION IMPORT #######################################################################

import pygame
import sys
import random
import math
from pytmx.util_pygame import load_pygame
from player import Player
from son import SoundManager
from menu import Menu
from npc import NPC
from npc import DialogueBox
from network import Network
from monstre import (
    ChienEnrage, GoblinMelee, GoblinArcher,
    EspritFeu, EspritGlace, EspritFoudre, EspritNature,
    GolemPierre,
)
from config import ROOT_DIR
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
}
MOB_COLORS = {
    "ChienEnrage": (180,90,30),   "GoblinMelee":  (60,160,60),
    "GoblinArcher":(60,200,100),  "EspritFeu":    (255,100,0),
    "EspritGlace": (80,180,255),  "EspritFoudre": (220,255,0),
    "EspritNature":(30,200,80),   "GolemPierre":  (140,130,120),
}
MOB_XP = {
    "ChienEnrage":20, "GoblinMelee":30, "GoblinArcher":40,
    "EspritFeu":35,   "EspritGlace":35, "EspritFoudre":45,
    "EspritNature":30,"GolemPierre":100,
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
    """Représentation locale du joueur distant — mis à jour par les messages réseau."""
    def __init__(self, pos):
        super().__init__()
        self.image = pygame.Surface((32, 64))
        self.image.fill((0, 200, 255))      # cyan pour distinguer
        self.rect  = self.image.get_rect(topleft=pos)
        self.hp_current = 100
        self.hp_max     = 100

    def apply_state(self, state: dict):
        self.rect.x     = state.get("x",  self.rect.x)
        self.rect.y     = state.get("y",  self.rect.y)
        self.hp_current = state.get("hp", self.hp_current)

#CLASS GAME#########################################################################

class Game:

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("SMILE")
        self.clock  = pygame.time.Clock()

        # Polices HUD
        self.font_hud   = pygame.font.SysFont("consolas", 18, bold=True)
        self.font_small = pygame.font.SysFont("consolas", 14)
        self.font_title = pygame.font.SysFont("consolas", 42, bold=True)

        # --- ETATS DU JEU ---
        self.is_paused    = True
        self.game_started = False
        self.score        = 0
        self.kill_count   = 0
        self.particles    = []

        # Screen-shake pour GolemPierre
        self.shake_ref = [0]
        self.mob_counter = 0

        # --- MODE MULTI ---
        self.network       = None          # Network() créé à la demande
        self.is_multi      = False         # True si partie réseau
        self.remote_player = None          # RemotePlayer (l'autre joueur)
        self.net_timer     = 0             # compteur pour envoi état (host)

        # --- SON / MENU ---
        self.sound_manager = SoundManager()
        self.menu          = Menu(self.screen)

        # --- GROUPES DE SPRITES ---
        self.visibles_sprites   = pygame.sprite.Group()
        self.obstacle_sprites   = pygame.sprite.Group()
        self.npc_sprites        = pygame.sprite.Group()
        self.ladder_sprites     = pygame.sprite.Group()
        self.monster_sprites    = pygame.sprite.Group()
        self.enemy_proj_sprites = pygame.sprite.Group()
        self.vfx_sprites        = pygame.sprite.Group()

        # --- UI DIALOGUE ---
        self.dialogue_box = DialogueBox(self.screen)

        # --- CHARGEMENT DE LA MAP ---
        tmx_data = load_pygame(os.path.join(ROOT_DIR, 'assets/maps/map1.tmx'))
        map_pixel_width  = tmx_data.width  * tmx_data.tilewidth
        map_pixel_height = tmx_data.height * tmx_data.tileheight

        # Camera
        self.camera = Camera(map_pixel_width, map_pixel_height)

        # Fond
        try:
            layer_fond = tmx_data.get_layer_by_name('Background')
            self.background_image = layer_fond.image
        except (ValueError, AttributeError):
            print("ERREUR : Calque 'Background' introuvable.")
            self.background_image = pygame.Surface((map_pixel_width, map_pixel_height))
            self.background_image.fill((50, 50, 50))

        # Collisions
        for x, y, surf in tmx_data.get_layer_by_name('Collisions').tiles():
            if surf:
                Tile((x * 32, y * 32), surf, [self.obstacle_sprites])

        # Echelles
        try:
            for x, y, surf in tmx_data.get_layer_by_name('Echelles').tiles():
                Tile((x * 32, y * 32), surf, [self.ladder_sprites])
            print(f"INFO : {len(self.ladder_sprites)} tuile(s) d'echelle chargee(s).")
        except ValueError:
            print("INFO : Calque 'Echelles' introuvable — echelles ignorees.")

        # Objets Tiled
        player_spawn = (200, 200)
        try:
            for obj in tmx_data.get_layer_by_name('Objets'):
                obj_type = getattr(obj, 'type', None) or obj.properties.get('type', None)
                pos = (int(obj.x), int(obj.y))
                if obj_type == 'SpawnJoueur':
                    player_spawn = pos
                elif obj_type == 'NPC':
                    msg = obj.properties.get('message', 'Bonjour !')
                    NPC(pos, msg, [self.visibles_sprites, self.npc_sprites])
                elif obj_type in MOB_CLASSES:
                    self._spawn_mob(obj_type, pos)
        except ValueError:
            print("INFO : Calque 'Objets' introuvable — monstres non charges depuis Tiled.")

        if not any(self.npc_sprites):
            NPC((600, 500), "Salut Voyageur ! Attention aux trous !",
                [self.visibles_sprites, self.npc_sprites])

        # Joueur local
        self.player = Player(player_spawn, self.sound_manager, self.menu.keybinds)
        self.visibles_sprites.add(self.player)

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
        # Crée le fantôme du joueur distant
        self.remote_player = RemotePlayer(self.player.rect.topleft)
        self.visibles_sprites.add(self.remote_player)

    def _network_update(self, dt):
        """Envoi/réception réseau — appelé chaque frame quand multi actif."""
        if self.network is None:
            return

        if self.network.role == "host":
            self.net_timer += dt
            if self.net_timer >= 1 / 60:          # 60 fois/seconde (fluide)
                self.net_timer = 0
                state = {
                    "p1_x":  self.player.rect.x,
                    "p1_y":  self.player.rect.y,
                    "p1_hp": self.player.hp_current,
                }
                mobs_state = []
                for m in self.monster_sprites:
                    mobs_state.append({"id": getattr(m, 'id', -1), "x": m.rect.x, "y": m.rect.y, "hp": m.hp_current})
                state["mobs"] = mobs_state
                state["projs"] = [{"x": p.rect.x, "y": p.rect.y} for p in self.player.capacite.projectiles]
                state["enemy_projs"] = [{"x": p.rect.x, "y": p.rect.y} for p in self.enemy_proj_sprites]
                self.network.send_game_state(state)

            for msg in self.network.poll():
                self.last_msg_time = pygame.time.get_ticks()
                if msg.get("action") == "input":
                    if self.remote_player:
                        self.remote_player.rect.x     = msg.get("p2_x", self.remote_player.rect.x)
                        self.remote_player.rect.y     = msg.get("p2_y", self.remote_player.rect.y)
                        self.remote_player.hp_current = msg.get("p2_hp", self.remote_player.hp_current)
                    self.remote_projs = msg.get("projs", [])
                elif msg.get("action") == "damage_mob":
                    mob_id = msg.get("mob_id")
                    mob = next((m for m in self.monster_sprites if getattr(m, 'id', None) == mob_id), None)
                    if mob:
                        mob.take_damage(msg.get("amount", 20))

        # ── CLIENT : envoie son état (P2), reçoit l'état du host (P1) ──────
        elif self.network.role == "client":
            self.net_timer += dt
            if self.net_timer >= 1 / 60:
                self.net_timer = 0
                state = {
                    "p2_x":  self.player.rect.x,
                    "p2_y":  self.player.rect.y,
                    "p2_hp": self.player.hp_current,
                    "projs": [{"x": p.rect.x, "y": p.rect.y} for p in self.player.capacite.projectiles]
                }
                self.network.send_client_state(state)

            for msg in self.network.poll():
                self.last_msg_time = pygame.time.get_ticks()
                if msg.get("action") == "game_state":
                    # Le joueur distant pour le client = p1 dans l'état host
                    if self.remote_player:
                        self.remote_player.rect.x     = msg.get("p1_x", self.remote_player.rect.x)
                        self.remote_player.rect.y     = msg.get("p1_y", self.remote_player.rect.y)
                        self.remote_player.hp_current = msg.get("p1_hp", self.remote_player.hp_current)

                    self.remote_projs = msg.get("projs", [])
                    self.remote_enemy_projs = msg.get("enemy_projs", [])

                    mobs_state = msg.get("mobs", [])
                    received_ids = {m["id"] for m in mobs_state}
                    for m_state in mobs_state:
                        mob = next((m for m in self.monster_sprites if getattr(m, 'id', None) == m_state["id"]), None)
                        if mob:
                            mob.rect.x = m_state["x"]
                            mob.rect.y = m_state["y"]
                            mob.hp_current = m_state["hp"]
                    for m in list(self.monster_sprites):
                        if getattr(m, 'id', None) not in received_ids:
                            m.dead = True
                            m.hp_current = 0

    # ── Spawn mobs ────────────────────────────────────────────────

    def _spawn_mob(self, obj_type, pos):
        groups    = [self.monster_sprites]
        mob_class = MOB_CLASSES[obj_type]
        if obj_type == "GoblinArcher":
            mob = mob_class(pos, groups, arrow_groups=[self.enemy_proj_sprites])
        elif obj_type == "GolemPierre":
            mob = mob_class(pos, groups, screen_shake_ref=self.shake_ref)
        elif obj_type in ("EspritFeu", "EspritGlace", "EspritFoudre", "EspritNature"):
            mob = mob_class(pos, groups, vfx_groups=[self.vfx_sprites])
        else:
            mob = mob_class(pos, groups)
        mob.id = self.mob_counter
        self.mob_counter += 1

    # ── Update ────────────────────────────────────────────────────

    def update(self, dt):
        if not self.is_paused:
            if self.is_multi and self.network:
                # Initialise le timer de message si pas encore fait
                if getattr(self, 'last_msg_time', 0) == 0:
                    self.last_msg_time = pygame.time.get_ticks()
                
                # Déconnexion par timeout (3 secondes sans message)
                if pygame.time.get_ticks() - self.last_msg_time > 3000:
                    self.network.connected = False

                if not self.network.connected:
                    print("Déconnexion détectée, retour au menu...")
                    self.is_multi = False
                    self.game_started = False
                    self.is_paused = True
                    self.menu.state = "main"
                    self.network = None
                    self.last_msg_time = 0
                    return

            # Réseau
            if self.is_multi:
                self._network_update(dt)

            # Joueur local (le client ne contrôle son perso que si rôle client,
            # le host contrôle le sien normalement)
            if self.player.hp_current > 0:
                # En mode client on laisse quand même le joueur se mettre à jour
                # visuellement (la position sera écrasée par l'état réseau)
                self.player.update(self.obstacle_sprites, self.ladder_sprites, dt)

            # NPC
            for npc in self.npc_sprites:
                npc.update(self.player.rect, self.dialogue_box)

            # Camera
            self.camera.update(self.player.rect)

            # Monstres
            for m in list(self.monster_sprites):
                if not self.is_multi or self.network.role == "host":
                    m.update(self.player, self.obstacle_sprites)
                else:
                    if getattr(m, 'contact_timer', 0) > 0:
                        m.contact_timer -= 1

                if hasattr(m, 'heal_allies'):
                    m.heal_allies(self.monster_sprites)

                if m.rect.colliderect(self.player.rect) and self.player.hp_current > 0:
                    if m.contact_timer <= 0:
                        self.player.take_damage(getattr(m, 'ATTACK_DAMAGE', 10))
                        m.contact_timer = m.CONTACT_COOLDOWN

                if m.dead:
                    mob_type = type(m).__name__
                    self.score      += MOB_XP.get(mob_type, 10)
                    self.kill_count += 1
                    color = MOB_COLORS.get(mob_type, WHITE)
                    for _ in range(16):
                        self.particles.append(
                            Particle(m.rect.centerx, m.rect.centery, color))
                    m.kill()

            # Projectiles joueur → monstres
            for proj in list(self.player.capacite.projectiles):
                for m in list(self.monster_sprites):
                    if not m.dead and proj.rect.colliderect(m.rect):
                        proj.kill()
                        if not self.is_multi or self.network.role == "host":
                            m.take_damage(20)
                        elif self.network.role == "client":
                            if self.network:
                                self.network._send({"action": "damage_mob", "mob_id": getattr(m, 'id', -1), "amount": 20})
                        break

            # Projectiles ennemis → joueur
            for ep in list(self.enemy_proj_sprites):
                if ep.rect.colliderect(self.player.rect) and self.player.hp_current > 0:
                    self.player.take_damage(getattr(ep, 'damage', 10))
                    ep.kill()

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
        pygame.draw.rect(self.screen, RED,   (x, y, bar_w, 20))
        pygame.draw.rect(self.screen, GREEN, (x, y, int(bar_w * ratio), 20))
        pygame.draw.rect(self.screen, BLACK, (x, y, bar_w, 20), 3)

    def draw_status_indicators(self):
        y = 80
        p = self.player
        if p.is_poisoned and p.poison_timer > 0:
            s = p.poison_timer // 60 + 1
            self.screen.blit(
                self.font_hud.render(f"POISON {s}s", True, (180, 0, 255)), (50, y))
            y += 24
        if p.slow_timer > 0:
            s = p.slow_timer // 60 + 1
            self.screen.blit(
                self.font_hud.render(f"RALENTI {s}s", True, (100, 180, 255)), (50, y))
            y += 24
        if p.burn_timer > 0:
            s = p.burn_timer // 60 + 1
            self.screen.blit(
                self.font_hud.render(f"BRULURE {s}s", True, (255, 120, 0)), (50, y))

    def draw_remote_health_bar(self):
        """Barre de vie du joueur distant (haut droite)."""
        if self.remote_player is None:
            return
        x = SCREEN_WIDTH - 250
        y = 50
        ratio = max(0, self.remote_player.hp_current / self.remote_player.hp_max)
        bar_w = 200
        pygame.draw.rect(self.screen, RED,            (x, y, bar_w, 20))
        pygame.draw.rect(self.screen, (0, 200, 255),  (x, y, int(bar_w * ratio), 20))
        pygame.draw.rect(self.screen, BLACK,           (x, y, bar_w, 20), 3)
        lbl = self.font_small.render("P2", True, (0, 200, 255))
        self.screen.blit(lbl, (x - 30, y))

    def draw(self):
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
                self.screen.blit(m.image, self.camera.apply(m.rect))
                bar_rect = m.rect.move(-int(self.camera.offset.x),
                                       -int(self.camera.offset.y))
                bw, bh = bar_rect.width, 6
                bx, by = bar_rect.left, bar_rect.top - 12
                ratio  = max(0.0, m.hp_current / m.hp_max)
                pygame.draw.rect(self.screen, (139, 0, 0), (bx, by, bw, bh))
                pygame.draw.rect(self.screen, (0, 220, 0), (bx, by, int(bw * ratio), bh))
                pygame.draw.rect(self.screen, BLACK,        (bx, by, bw, bh), 1)

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

            self.dialogue_box.draw()
            self.draw_health_bar()
            self.draw_status_indicators()

            if self.is_multi:
                self.draw_remote_health_bar()

            score_txt = self.font_hud.render(
                f"Score : {self.score}   Kills : {self.kill_count}", True, WHITE)
            self.screen.blit(score_txt, (SCREEN_WIDTH - score_txt.get_width() - 20, 20))

            if self.player.hp_current <= 0:
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 140))
                self.screen.blit(overlay, (0, 0))
                txt = self.font_title.render("GAME OVER", True, RED)
                self.screen.blit(txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2,
                                       SCREEN_HEIGHT // 2 - txt.get_height() // 2))

        pygame.display.flip()

    # ── Boucle principale ─────────────────────────────────────────

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    if self.game_started:
                        self.is_paused = not self.is_paused
                        self.menu.state = "main"

                if self.is_paused:
                    action = self.menu.handle_input(event, self.network)

                    # Slider volume — action est un tuple ("volume_changed", valeur)
                    if isinstance(action, tuple) and action[0] == "volume_changed":
                        self.sound_manager.set_volume(action[1])

                    elif action == "open_modes":
                        if self.game_started:
                            self.is_paused = False
                        else:
                            self.menu.state = "mode_selection"

                    elif action == "play_story":
                        print("Mode Histoire lancé !")
                        self.game_started = True
                        self.is_paused    = False

                    # ── HOST crée une session ───────────────────────
                    elif action == "multi_create_session":
                        print("Création de session multi...")
                        self._start_multi_as_host()

                    # ── CLIENT rejoint une session ──────────────────
                    elif action == "multi_join_session":
                        code = self.menu.input_code
                        print(f"Tentative de rejoindre le salon : {code}")
                        self._start_multi_as_client(code)

                    elif action == "quit":
                        pygame.quit()
                        sys.exit()

            # ── Vérification état réseau (en dehors des events) ─────
            if self.network is not None and self.is_paused:
                # HOST : la partie démarre quand le pair a rejoint
                if (self.network.role == "host"
                        and self.menu.state == "multi_host_wait"
                        and self.network.peer_joined):
                    print("Pair connecté ! Démarrage de la partie multi.")
                    self._launch_multi_game()

                # CLIENT : la partie démarre dès que le serveur confirme "joined"
                elif (self.network.role == "client"
                        and self.menu.state == "multi_join_wait"
                        and self.network.peer_joined):
                    print("Code valide ! Démarrage de la partie multi.")
                    self._launch_multi_game()

            self.update(dt)
            self.draw()

#LANCEMENT DU JEU##########################################################################

if __name__ == '__main__':
    game = Game()
    game.run()