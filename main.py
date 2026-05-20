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
from monstre import (
    ChienEnrage, GoblinMelee, GoblinArcher,
    EspritFeu, EspritGlace, EspritFoudre, EspritNature,
    GolemPierre,
)

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
    """
    Gere le decalage (offset) de la camera pour centrer l'ecran sur le joueur.
    - Lerp (glissement doux).
    - Blocage aux 4 bords de la map.
    """

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

#CLASS GAME#########################################################################

class Game:

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("SMILE")
        self.clock = pygame.time.Clock()

        # Polices HUD (Hugo)
        self.font_hud   = pygame.font.SysFont("consolas", 18, bold=True)
        self.font_small = pygame.font.SysFont("consolas", 14)
        self.font_title = pygame.font.SysFont("consolas", 42, bold=True)

        # --- ETATS DU JEU ---
        self.is_paused    = True
        self.game_started = False
        self.score        = 0
        self.kill_count   = 0
        self.particles    = []

        # Screen-shake pour GolemPierre (Hugo)
        self.shake_ref = [0]

        # --- GESTIONNAIRE DE SON ---
        self.sound_manager = SoundManager()
        self.menu = Menu(self.screen)

        # --- GROUPES DE SPRITES ---
        self.visibles_sprites   = pygame.sprite.Group()
        self.obstacle_sprites   = pygame.sprite.Group()
        self.npc_sprites        = pygame.sprite.Group()
        self.ladder_sprites     = pygame.sprite.Group()   # ton code
        self.monster_sprites    = pygame.sprite.Group()   # Hugo
        self.enemy_proj_sprites = pygame.sprite.Group()   # Hugo
        self.vfx_sprites        = pygame.sprite.Group()   # Hugo

        # --- UI DIALOGUE ---
        self.dialogue_box = DialogueBox(self.screen)

        # --- CHARGEMENT DE LA MAP TILED (map1.tmx = ton code) ---
        tmx_data = load_pygame('map1.tmx')

        map_pixel_width  = tmx_data.width  * tmx_data.tilewidth
        map_pixel_height = tmx_data.height * tmx_data.tileheight

        # --- CAMERA ---
        self.camera = Camera(map_pixel_width, map_pixel_height)

        # --- FOND ---
        try:
            layer_fond = tmx_data.get_layer_by_name('Background')
            self.background_image = layer_fond.image
        except (ValueError, AttributeError):
            print("ERREUR : Calque 'Background' introuvable.")
            self.background_image = pygame.Surface((map_pixel_width, map_pixel_height))
            self.background_image.fill((50, 50, 50))

        # --- TILES DE COLLISION ---
        for x, y, surf in tmx_data.get_layer_by_name('Collisions').tiles():
            if surf:
                Tile((x * 32, y * 32), surf, [self.obstacle_sprites])

        # --- TILES D'ECHELLE (ton code) ---
        try:
            for x, y, surf in tmx_data.get_layer_by_name('Echelles').tiles():
                pos = (x * 32, y * 32)
                Tile(pos, surf, [self.ladder_sprites])
            print(f"INFO : {len(self.ladder_sprites)} tuile(s) d'echelle chargee(s).")
        except ValueError:
            print("INFO : Calque 'Echelles' introuvable — echelles ignorees.")

        # --- OBJETS TILED : monstres, PNJ, spawn joueur (Hugo) ---
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

        # Fallback PNJ si aucun calque Objets
        if not any(self.npc_sprites):
            NPC((600, 500), "Salut Voyageur ! Attention aux trous !",
                [self.visibles_sprites, self.npc_sprites])

        # --- JOUEUR ---
        self.player = Player(player_spawn, self.sound_manager)
        self.visibles_sprites.add(self.player)

    # -------------------------------------------------------------------------

    def _spawn_mob(self, obj_type, pos):
        """Instancie un monstre selon son type Tiled (Hugo)."""
        groups    = [self.monster_sprites]
        mob_class = MOB_CLASSES[obj_type]
        if obj_type == "GoblinArcher":
            mob_class(pos, groups, arrow_groups=[self.enemy_proj_sprites])
        elif obj_type == "GolemPierre":
            mob_class(pos, groups, screen_shake_ref=self.shake_ref)
        elif obj_type in ("EspritFeu", "EspritGlace", "EspritFoudre", "EspritNature"):
            mob_class(pos, groups, vfx_groups=[self.vfx_sprites])
        else:
            mob_class(pos, groups)

    # -------------------------------------------------------------------------

    def update(self, dt):
        if not self.is_paused:

            # JOUEUR
            if self.player.hp_current > 0:
                self.player.update(self.obstacle_sprites, self.ladder_sprites, dt)

            # NPC
            for npc in self.npc_sprites:
                npc.update(self.player.rect, self.dialogue_box)

            # CAMERA (ton code)
            self.camera.update(self.player.rect)

            # MONSTRES (Hugo)
            for m in list(self.monster_sprites):
                m.update(self.player, self.obstacle_sprites)

                if hasattr(m, 'heal_allies'):
                    m.heal_allies(self.monster_sprites)

                # Contact joueur
                if m.rect.colliderect(self.player.rect) and self.player.hp_current > 0:
                    if m.contact_timer <= 0:
                        self.player.take_damage(getattr(m, 'ATTACK_DAMAGE', 10))
                        m.contact_timer = m.CONTACT_COOLDOWN

                # Mort du monstre → particules + score
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
                        m.take_damage(20)
                        proj.kill()
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

    # -------------------------------------------------------------------------

    def draw_health_bar(self):
        """Barre de vie fixe en haut a gauche."""
        x, y  = 50, 50
        ratio = max(0, self.player.hp_current / self.player.hp_max)
        bar_w = self.player.health_bar_length
        pygame.draw.rect(self.screen, RED,   (x, y, bar_w, 20))
        pygame.draw.rect(self.screen, GREEN, (x, y, int(bar_w * ratio), 20))
        pygame.draw.rect(self.screen, BLACK, (x, y, bar_w, 20), 3)

    def draw_status_indicators(self):
        """Affiche les indicateurs de statut (poison/ralenti/brulure) — Hugo."""
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

    def draw(self):
        if self.is_paused:
            self.menu.draw(self.game_started)
        else:
            # --- SCREEN-SHAKE (Hugo) ---
            shake = 0
            if self.shake_ref[0] > 0:
                self.shake_ref[0] -= 1
                shake = random.randint(-6, 6)

            # 1. FOND avec offset camera + shake
            self.screen.blit(
                self.background_image,
                (-int(self.camera.offset.x) + shake,
                 -int(self.camera.offset.y) + shake)
            )

            # 2. SPRITES DU MONDE avec offset camera
            for sprite in self.visibles_sprites:
                self.screen.blit(sprite.image, self.camera.apply(sprite.rect))

            # 3. PROJECTILES JOUEUR avec offset camera
            for projectile in self.player.capacite.projectiles:
                self.screen.blit(projectile.image, self.camera.apply(projectile.rect))

            # 4. PROJECTILES ENNEMIS avec offset camera
            for ep in self.enemy_proj_sprites:
                self.screen.blit(ep.image, self.camera.apply(ep.rect))

            # 5. MONSTRES + barres de vie avec offset camera (Hugo)
            for m in self.monster_sprites:
                self.screen.blit(m.image, self.camera.apply(m.rect))
                # Barre de vie flottante : on la dessine a la position ecran
                bar_rect = m.rect.move(-int(self.camera.offset.x),
                                       -int(self.camera.offset.y))
                bw, bh = bar_rect.width, 6
                bx, by = bar_rect.left, bar_rect.top - 12
                ratio  = max(0.0, m.hp_current / m.hp_max)
                pygame.draw.rect(self.screen, (139, 0, 0),    (bx, by, bw, bh))
                pygame.draw.rect(self.screen, (0, 220, 0),    (bx, by, int(bw * ratio), bh))
                pygame.draw.rect(self.screen, BLACK,           (bx, by, bw, bh), 1)

            # 6. VFX avec offset camera
            for vfx in self.vfx_sprites:
                self.screen.blit(vfx.image, self.camera.apply(vfx.rect))

            # 7. PARTICULES (deja en coordonnees ecran via positions absolues)
            for p in self.particles:
                p.draw(self.screen)

            # 8. UI FIXE (sans offset)
            self.dialogue_box.draw()
            self.draw_health_bar()
            self.draw_status_indicators()

            # Score (Hugo)
            score_txt = self.font_hud.render(
                f"Score : {self.score}   Kills : {self.kill_count}", True, WHITE)
            self.screen.blit(score_txt, (SCREEN_WIDTH - score_txt.get_width() - 20, 20))

            # 9. GAME OVER (Hugo)
            if self.player.hp_current <= 0:
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 140))
                self.screen.blit(overlay, (0, 0))
                txt = self.font_title.render("GAME OVER", True, RED)
                self.screen.blit(txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2,
                                       SCREEN_HEIGHT // 2 - txt.get_height() // 2))

        pygame.display.flip()

    # -------------------------------------------------------------------------

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                # ECHAP — toggle pause si jeu deja commence
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    if self.game_started:
                        self.is_paused = not self.is_paused
                        self.menu.state = "main"

                # MENU
                if self.is_paused:
                    action = self.menu.handle_input(event)

                    if action == "open_modes":
                        if self.game_started:
                            self.is_paused = False
                        else:
                            self.menu.state = "mode_selection"

                    elif action == "play_story":
                        print("Mode Histoire lance !")
                        self.game_started = True
                        self.is_paused    = False

                    elif action == "play_multi":
                        print("Mode Multi lance !")
                        self.game_started = True
                        self.is_paused    = False

                    elif action == "quit":
                        pygame.quit()
                        sys.exit()

            self.update(dt)
            self.draw()

#LANCEMENT DU JEU##########################################################################

if __name__ == '__main__':
    game = Game()
    game.run()