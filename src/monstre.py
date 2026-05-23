import pygame
import math
import random
import os

# ================================================================
#  MONSTRE.PY  —  Ennemis avec machine à états — SMILE
# ================================================================
#
#  FONCTIONNALITÉS COMMUNES (BaseEnemy) :
#    ✔ Vie + barre de vie flottante
#    ✔ Cooldown de contact (contact_timer / CONTACT_COOLDOWN)
#    ✔ Retour au spawn + promenade quand le joueur est perdu de vue
#    ✔ Sprites pré-calculés (plus de redraw chaque frame = 0 lag)
#    ✔ Chargeur PNG prêt pour les animations
#
#  MONSTRES :
#    1.  ChienEnrage       — glisse si sauté par-dessus
#    2.  GoblinMelee       — corps-à-corps, stuné quand touché
#    3.  GoblinArcher      — distance, repositionnement, flèches
#    4.  EspritFeu         — bonds rapides, brûle au contact
#    5.  EspritGlace       — lent mais gèle le joueur au contact
#    6.  EspritFoudre      — téléportation aléatoire, choc électrique
#    7.  EspritNature      — soigne ses alliés proches, poison passif
#    8.  GolemPierre        — très lent, tremblement de terre, renforce 1 s
# ================================================================


# ────────────────────────────────────────────
#  COULEURS
# ────────────────────────────────────────────
BROWN        = (139,  69,  19)
DARK_RED     = (139,   0,   0)
GREEN_DARK   = (  0, 100,   0)
GREEN_LIGHT  = ( 50, 200,  50)
PURPLE       = (100,   0, 150)
YELLOW       = (255, 220,   0)
ORANGE       = (255, 140,   0)
WHITE        = (255, 255, 255)
BLACK        = (  0,   0,   0)
RED          = (255,   0,   0)
GRAY         = (140, 130, 120)
CYAN         = (  0, 220, 255)
BLUE_ICE     = ( 80, 160, 255)
BLUE_DARK    = ( 20,  40, 120)
ELECTRIC     = (200, 255,   0)
NATURE_GREEN = ( 30, 180,  60)

SCREEN_WIDTH  = 1920
SCREEN_HEIGHT = 1072


# ================================================================
#  UTILITAIRE : fabrique une surface pré-dessinée (évite le redraw)
# ================================================================

def _make_surf(w, h, draw_fn, *args):
    """
    Crée une surface SRCALPHA (w×h), appelle draw_fn(surf, *args)
    dessus, et retourne la surface. Utilisé pour pré-calculer les
    frames des placeholders sans redessiner chaque frame.
    """
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    draw_fn(surf, *args)
    return surf


# ================================================================
#  CLASSE DE BASE
# ================================================================

class BaseEnemy(pygame.sprite.Sprite):
    """
    Socle commun à tous les monstres.

    Constantes à surcharger :
      DETECT_RANGE   — distance de détection
      LOSE_RANGE     — distance de perte de vue
      PATROL_SPEED   — vitesse de promenade (0 = stationnaire)
      PATROL_RADIUS  — amplitude de la promenade (px)
    """

    DETECT_RANGE  = 400
    LOSE_RANGE    = 600
    PATROL_SPEED  = 1
    PATROL_RADIUS = 100

    def __init__(self, pos, hp, groups, capacite_absorbable=None):
        super().__init__(groups)

        self.spawn_pos  = (int(pos[0]), int(pos[1]))
        self.hp_max     = hp
        self.hp_current = hp
        self.dead       = False
        self.capacite_absorbable = capacite_absorbable

        self.contact_timer    = 0
        self.CONTACT_COOLDOWN = 90

        # Bornes de promenade
        self._patrol_targets = [
            self.spawn_pos[0] - self.PATROL_RADIUS,
            self.spawn_pos[0] + self.PATROL_RADIUS,
        ]
        self._patrol_idx = 0

        # Image placeholder par défaut
        self.image = pygame.Surface((32, 32))
        self.image.fill((200, 0, 200))
        self.rect  = self.image.get_rect(topleft=pos)

        # Système d'animation PNG (optionnel)
        self._sprites    = {}
        self._anim_timer = 0.0
        self._anim_index = 0
        self._anim_speed = 0.12

    # ── Chargeur PNG ─────────────────────────────────────────────
    def _load_sprites(self, folder_name, states, target_size):
        """
        Charge assets/images/monstres/<folder_name>/<etat>/frame_XXX.png
        Ne plante pas si les fichiers sont absents.
        """
        dossier_base = os.path.join("assets", "images", "monstres", folder_name)
        for state in states:
            path = os.path.join(dossier_base, state)
            if not os.path.isdir(path):
                continue
            frames = []
            for fname in sorted(os.listdir(path)):
                if fname.lower().endswith(".png"):
                    try:
                        surf = pygame.image.load(
                            os.path.join(path, fname)
                        ).convert_alpha()
                        surf = pygame.transform.scale(surf, target_size)
                        frames.append(surf)
                    except pygame.error:
                        pass
            if frames:
                self._sprites[state] = frames

    def _animate(self, state, dt, loop=True):
        """
        Retourne la frame courante.
        Appeler dans update() → self.image = self._animate(state, dt)
        Puis flipper si facing_left.
        """
        if state not in self._sprites or not self._sprites[state]:
            return self.image
        frames = self._sprites[state]
        self._anim_timer += dt
        if self._anim_timer >= self._anim_speed:
            self._anim_timer = 0.0
            self._anim_index = (self._anim_index + 1) % len(frames) if loop \
                               else min(self._anim_index + 1, len(frames) - 1)
        return frames[self._anim_index]

    # ── Vie ───────────────────────────────────────────────────────
    def take_damage(self, amount):
        self.hp_current -= amount
        if self.hp_current <= 0:
            self.hp_current = 0
            self.dead = True
            self.on_death()

    def on_death(self):
        self.kill()

    def tick_contact_timer(self):
        if self.contact_timer > 0:
            self.contact_timer -= 1

    # ── Retour spawn / promenade ──────────────────────────────────
    def _do_return_to_spawn(self, obstacles):
        tx = self.spawn_pos[0]
        if abs(self.rect.centerx - tx) < 8:
            return True
        d = 1 if tx > self.rect.centerx else -1
        self._try_move(d * self.PATROL_SPEED, obstacles)
        return False

    def _do_wander(self, obstacles):
        if self.PATROL_SPEED == 0:
            return
        tx = self._patrol_targets[self._patrol_idx]
        if abs(self.rect.centerx - tx) < 8:
            self._patrol_idx = (self._patrol_idx + 1) % 2
        d = 1 if tx > self.rect.centerx else -1
        self._try_move(d * self.PATROL_SPEED, obstacles)

    # ── Barre de vie ──────────────────────────────────────────────
    def draw_health_bar(self, surface):
        if self.dead:
            return
        bw, bh = self.rect.width, 6
        x, y   = self.rect.left, self.rect.top - 12
        ratio  = max(0.0, self.hp_current / self.hp_max)
        pygame.draw.rect(surface, DARK_RED,    (x, y, bw, bh))
        pygame.draw.rect(surface, (0, 220, 0), (x, y, int(bw * ratio), bh))
        pygame.draw.rect(surface, BLACK,       (x, y, bw, bh), 1)

    # ── Physique ──────────────────────────────────────────────────
    def distance_to(self, other_rect):
        a = pygame.math.Vector2(self.rect.center)
        b = pygame.math.Vector2(other_rect.center)
        return a.distance_to(b)

    def _try_move(self, dx, obstacles):
        self.rect.x += int(dx)
        for hit in pygame.sprite.spritecollide(self, obstacles, False):
            if dx > 0: self.rect.right = hit.rect.left
            else:      self.rect.left  = hit.rect.right

    def _apply_gravity(self, obstacles):
        self.vy += 0.8
        if self.vy > 18: self.vy = 18
        self.rect.y += int(self.vy)
        for hit in pygame.sprite.spritecollide(self, obstacles, False):
            if self.vy > 0:
                self.rect.bottom = hit.rect.top
                self.vy = 0


# ================================================================
#  1. CHIEN ENRAGÉ
# ================================================================

class ChienEnrage(BaseEnemy):

    PATROL_SPEED  = 2
    PATROL_RADIUS = 120
    CHASE_SPEED   = 5
    SLIDE_SPEED   = 4
    SLIDE_DECAY   = 0.15
    TURN_DELAY    = 45
    DETECT_RANGE  = 500
    LOSE_RANGE    = 750
    ATTACK_RANGE  = 40
    ATTACK_DAMAGE = 15
    ATTACK_CD     = 90

    ST_WANDER = "wander"
    ST_RETURN = "return"
    ST_CHASE  = "chase"
    ST_SLIDE  = "slide"

    def __init__(self, pos, groups):
        super().__init__(pos, hp=60, groups=groups, capacite_absorbable="dash")
        self.CONTACT_COOLDOWN = 80

        w, h = 48, 32
        self.image = self._build_img(w, h)
        self.rect  = self.image.get_rect(topleft=pos)

        self.state        = self.ST_WANDER
        self.facing_right = True
        self.slide_vx     = 0.0
        self.turn_timer   = 0
        self.attack_timer = 0
        self.vy           = 0

    @staticmethod
    def _build_img(w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        pygame.draw.ellipse(s, BROWN, (0, 8, w, 20))
        pygame.draw.polygon(s, DARK_RED, [(4, 8), (10, 0), (16, 8)])
        pygame.draw.polygon(s, DARK_RED, [(32, 8), (38, 0), (44, 8)])
        pygame.draw.ellipse(s, (180, 100, 40), (28, 12, 16, 12))
        pygame.draw.circle(s, RED,   (36, 10), 4)
        pygame.draw.circle(s, BLACK, (37, 10), 2)
        for px in [6, 14, 28, 36]:
            pygame.draw.rect(s, DARK_RED, (px, 26, 6, 6))
        return s

    def update(self, player, obstacles):
        if self.dead: return
        self.tick_contact_timer()
        self._apply_gravity(obstacles)
        dist = self.distance_to(player.rect)

        if self.state in (self.ST_WANDER, self.ST_RETURN):
            if dist < self.DETECT_RANGE:
                self.state = self.ST_CHASE
        elif self.state == self.ST_CHASE:
            player_above = player.rect.bottom < self.rect.top + 10
            if player_above and abs(player.rect.centerx - self.rect.centerx) < 60:
                self._enter_slide()
            elif dist > self.LOSE_RANGE:
                self.state = self.ST_RETURN
        elif self.state == self.ST_SLIDE:
            if abs(self.slide_vx) < 0.5:
                self.slide_vx = 0
                self.state = self.ST_CHASE if dist < self.LOSE_RANGE else self.ST_RETURN

        if self.state == self.ST_WANDER:
            self._do_wander(obstacles)
        elif self.state == self.ST_RETURN:
            if self._do_return_to_spawn(obstacles): self.state = self.ST_WANDER
        elif self.state == self.ST_CHASE:
            self._do_chase(player, obstacles)
        elif self.state == self.ST_SLIDE:
            self._do_slide(obstacles)

        if self.attack_timer > 0: self.attack_timer -= 1
        if dist < self.ATTACK_RANGE and self.state == self.ST_CHASE:
            if self.attack_timer == 0 and self.contact_timer == 0:
                player.take_damage(self.ATTACK_DAMAGE)
                self.attack_timer  = self.ATTACK_CD
                self.contact_timer = self.CONTACT_COOLDOWN

    def _do_chase(self, player, obstacles):
        if self.turn_timer > 0:
            self.turn_timer -= 1; return
        d = 1 if player.rect.centerx > self.rect.centerx else -1
        if (d == 1) != self.facing_right:
            self.turn_timer = self.TURN_DELAY
            self.facing_right = (d == 1); return
        self._try_move(d * self.CHASE_SPEED, obstacles)

    def _enter_slide(self):
        self.state    = self.ST_SLIDE
        self.slide_vx = self.CHASE_SPEED * (1 if self.facing_right else -1)
        self.turn_timer = self.TURN_DELAY

    def _do_slide(self, obstacles):
        self._try_move(self.slide_vx, obstacles)
        if self.slide_vx > 0: self.slide_vx = max(0.0, self.slide_vx - self.SLIDE_DECAY)
        else:                  self.slide_vx = min(0.0, self.slide_vx + self.SLIDE_DECAY)


# ================================================================
#  2a. GOBELIN CORPS-À-CORPS
# ================================================================

class GoblinMelee(BaseEnemy):

    PATROL_SPEED  = 1
    PATROL_RADIUS = 80
    SPEED         = 3
    DETECT_RANGE  = 480
    LOSE_RANGE    = 700
    ATTACK_RANGE  = 38
    ATTACK_DAMAGE = 12
    ATTACK_CD     = 70
    STUN_DURATION = 20

    ST_WANDER = "wander"
    ST_RETURN = "return"
    ST_CHASE  = "chase"
    ST_ATTACK = "attack"
    ST_STUN   = "stun"

    def __init__(self, pos, groups):
        super().__init__(pos, hp=40, groups=groups, capacite_absorbable="slash")
        self.CONTACT_COOLDOWN = 70

        w, h = 28, 40
        self.image = self._build_img(w, h)
        self.rect  = self.image.get_rect(topleft=pos)

        self.state        = self.ST_WANDER
        self.facing_right = True
        self.attack_timer = 0
        self.stun_timer   = 0
        self.vy           = 0

    @staticmethod
    def _build_img(w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        pygame.draw.rect(s, GREEN_DARK,  (4, 16, 20, 24))
        pygame.draw.ellipse(s, GREEN_LIGHT, (4, 0, 20, 20))
        pygame.draw.circle(s, YELLOW, (9,  7), 3)
        pygame.draw.circle(s, YELLOW, (19, 7), 3)
        pygame.draw.circle(s, BLACK,  (10, 7), 1)
        pygame.draw.circle(s, BLACK,  (20, 7), 1)
        pygame.draw.rect(s, ORANGE, (22, 8, 6, 14))
        pygame.draw.polygon(s, (200, 100, 0), [(22, 8), (28, 4), (28, 14)])
        return s

    def update(self, player, obstacles):
        if self.dead: return
        self.tick_contact_timer()
        self._apply_gravity(obstacles)
        dist = self.distance_to(player.rect)

        if self.attack_timer > 0: self.attack_timer -= 1
        if self.stun_timer > 0:
            self.stun_timer -= 1; self.state = self.ST_STUN; return

        if self.state in (self.ST_WANDER, self.ST_RETURN):
            if dist < self.DETECT_RANGE: self.state = self.ST_CHASE
        elif self.state == self.ST_CHASE:
            if dist <= self.ATTACK_RANGE: self.state = self.ST_ATTACK
            elif dist > self.LOSE_RANGE:  self.state = self.ST_RETURN
        elif self.state == self.ST_ATTACK:
            if dist > self.ATTACK_RANGE + 20: self.state = self.ST_CHASE

        if self.state == self.ST_WANDER:
            self._do_wander(obstacles)
        elif self.state == self.ST_RETURN:
            if self._do_return_to_spawn(obstacles): self.state = self.ST_WANDER
        elif self.state == self.ST_CHASE:
            d = 1 if player.rect.centerx > self.rect.centerx else -1
            self.facing_right = (d == 1)
            self._try_move(d * self.SPEED, obstacles)
        elif self.state == self.ST_ATTACK:
            if self.attack_timer == 0 and self.contact_timer == 0:
                player.take_damage(self.ATTACK_DAMAGE)
                self.attack_timer  = self.ATTACK_CD
                self.contact_timer = self.CONTACT_COOLDOWN

    def take_damage(self, amount):
        super().take_damage(amount)
        if not self.dead:
            self.stun_timer = self.STUN_DURATION
            self.state      = self.ST_STUN


# ================================================================
#  2b. GOBELIN ARCHER
# ================================================================

class Arrow(pygame.sprite.Sprite):
    SPEED = 10

    def __init__(self, pos, direction, groups):
        super().__init__(groups)
        s = pygame.Surface((18, 6), pygame.SRCALPHA)
        pygame.draw.rect(s, BROWN, (0, 2, 14, 2))
        pygame.draw.polygon(s, (200, 200, 220), [(14, 0), (18, 3), (14, 6)])
        pygame.draw.polygon(s, WHITE,           [(0, 0), (4, 3), (0, 6)])
        if direction == -1:
            s = pygame.transform.flip(s, True, False)
        self.image     = s
        self.rect      = self.image.get_rect(center=pos)
        self.direction = direction
        self.damage    = 10

    def update(self, obstacles):
        self.rect.x += self.SPEED * self.direction
        if pygame.sprite.spritecollide(self, obstacles, False): self.kill()
        if self.rect.right < 0 or self.rect.left > SCREEN_WIDTH: self.kill()


class GoblinArcher(BaseEnemy):

    PATROL_SPEED   = 1
    PATROL_RADIUS  = 80
    PREFERRED_DIST = 250
    RETREAT_DIST   = 180
    DETECT_RANGE   = 600
    LOSE_RANGE     = 850
    SHOOT_CD       = 120
    SPEED          = 2

    ST_WANDER   = "wander"
    ST_RETURN   = "return"
    ST_POSITION = "position"
    ST_SHOOT    = "shoot"
    ST_RETREAT  = "retreat"

    def __init__(self, pos, groups, arrow_groups):
        super().__init__(pos, hp=30, groups=groups, capacite_absorbable="arrow")
        self.CONTACT_COOLDOWN = 100

        w, h = 28, 40
        self.image = self._build_img(w, h)
        self.rect  = self.image.get_rect(topleft=pos)

        self.state        = self.ST_WANDER
        self.facing_right = True
        self.shoot_timer  = 0
        self.vy           = 0
        self.arrow_groups = arrow_groups
        self.arrows       = pygame.sprite.Group()

    @staticmethod
    def _build_img(w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        pygame.draw.rect(s, GREEN_DARK,    (4, 16, 20, 24))
        pygame.draw.ellipse(s, GREEN_LIGHT, (4, 0, 20, 20))
        pygame.draw.circle(s, YELLOW, (9,  7), 3)
        pygame.draw.circle(s, YELLOW, (19, 7), 3)
        pygame.draw.circle(s, BLACK,  (10, 7), 1)
        pygame.draw.circle(s, BLACK,  (20, 7), 1)
        pygame.draw.arc(s, BROWN, pygame.Rect(20, 6, 10, 22),
                        math.radians(60), math.radians(300), 2)
        pygame.draw.line(s, WHITE, (25, 8), (25, 26), 1)
        return s

    def update(self, player, obstacles):
        if self.dead: return
        self.tick_contact_timer()
        self._apply_gravity(obstacles)
        dist = self.distance_to(player.rect)

        if self.shoot_timer > 0: self.shoot_timer -= 1

        if self.state in (self.ST_WANDER, self.ST_RETURN):
            if dist < self.DETECT_RANGE: self.state = self.ST_POSITION
        elif self.state == self.ST_POSITION:
            if dist > self.LOSE_RANGE: self.state = self.ST_RETURN
            elif dist < self.RETREAT_DIST: self.state = self.ST_RETREAT
            elif abs(dist - self.PREFERRED_DIST) < 40: self.state = self.ST_SHOOT
        elif self.state == self.ST_SHOOT:
            if dist > self.LOSE_RANGE: self.state = self.ST_RETURN
            elif dist < self.RETREAT_DIST: self.state = self.ST_RETREAT
            elif abs(dist - self.PREFERRED_DIST) > 60: self.state = self.ST_POSITION
        elif self.state == self.ST_RETREAT:
            if dist > self.LOSE_RANGE: self.state = self.ST_RETURN
            elif dist > self.PREFERRED_DIST: self.state = self.ST_POSITION

        d = 1 if player.rect.centerx > self.rect.centerx else -1
        self.facing_right = (d == 1)

        if self.state == self.ST_WANDER:
            self._do_wander(obstacles)
        elif self.state == self.ST_RETURN:
            if self._do_return_to_spawn(obstacles): self.state = self.ST_WANDER
        elif self.state == self.ST_POSITION:
            if dist > self.PREFERRED_DIST + 40: self._try_move(d * self.SPEED, obstacles)
            elif dist < self.PREFERRED_DIST - 40: self._try_move(-d * self.SPEED, obstacles)
        elif self.state == self.ST_RETREAT:
            self._try_move(-d * self.SPEED * 2, obstacles)
        elif self.state == self.ST_SHOOT:
            if self.shoot_timer == 0:
                Arrow(self.rect.center, d, [self.arrows] + list(self.arrow_groups))
                self.shoot_timer = self.SHOOT_CD

        if dist < 40 and self.contact_timer == 0:
            player.take_damage(8)
            self.contact_timer = self.CONTACT_COOLDOWN

        self.arrows.update(obstacles)


# ================================================================
#  ESPRITS ÉLÉMENTAIRES
#  Comportement : WANDER → RETURN → CHASE → JUMP → EXPLODE → mort
#
#  Quand l'esprit détecte le joueur il fonce vers lui en sautant.
#  Dès qu'il touche le joueur (ou le sol sous lui) il explose :
#    → effets élémentaires appliqués
#    → l'esprit meurt (se dissout)
#  L'explosion est visuelle (flash + cercle) pendant quelques frames.
# ================================================================

class ExplosionVFX(pygame.sprite.Sprite):
    """Flash visuel d'explosion — vit quelques frames puis disparaît."""
    def __init__(self, pos, color, radius, groups):
        super().__init__(groups)
        d = radius * 2
        self.image = pygame.Surface((d, d), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (*color, 180), (radius, radius), radius)
        pygame.draw.circle(self.image, (*color[:3], 80), (radius, radius), radius, 4)
        self.rect  = self.image.get_rect(center=pos)
        self.timer = 18   # frames de vie

    def update(self, *args):
        self.timer -= 1
        # Fondu sortant
        alpha = max(0, int(255 * self.timer / 18))
        self.image.set_alpha(alpha)
        if self.timer <= 0:
            self.kill()


class EspritBase(BaseEnemy):
    """
    Socle commun aux 4 esprits élémentaires.

    Machine à états :
      WANDER  — petit saut sur place, attend
      RETURN  — retourne au spawn
      CHASE   — fonce en sautant vers le joueur
      EXPLODE — frame d'explosion (VFX + effets), puis meurt

    Chaque sous-classe surcharge :
      COULEUR_CORPS / COULEUR_AURA — couleurs du placeholder
      EXPLOSION_RADIUS             — rayon de l'explosion
      _apply_explosion(player)     — effets élémentaires uniques
    """

    PATROL_SPEED     = 0
    PATROL_RADIUS    = 0
    SPEED            = 3
    JUMP_FORCE       = -11   # saut d'attaque vigoureux
    DETECT_RANGE     = 380
    LOSE_RANGE       = 560
    EXPLOSION_RADIUS = 50    # rayon de détection de l'explosion

    COULEUR_CORPS = PURPLE
    COULEUR_AURA  = (180, 0, 255)

    ST_WANDER  = "wander"
    ST_RETURN  = "return"
    ST_CHASE   = "chase"
    ST_EXPLODE = "explode"

    def __init__(self, pos, groups, hp, capacite, vfx_groups=None):
        super().__init__(pos, hp=hp, groups=groups, capacite_absorbable=capacite)

        w = h = 30
        self.image = self._build_img(w, h)
        self.rect  = self.image.get_rect(topleft=pos)

        self.state        = self.ST_WANDER
        self.vy           = 0
        self.on_floor     = False
        self.bounce_timer = random.randint(60, 120)

        # Groupes où spawner les VFX d'explosion (optionnel)
        self.vfx_groups = vfx_groups or []

    def _build_img(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        pygame.draw.ellipse(s, self.COULEUR_CORPS, (0, 4, w, h - 4))
        pygame.draw.ellipse(s, self.COULEUR_AURA,  (5, 0, w - 10, h // 2))
        pygame.draw.circle(s, WHITE,  (9,  9), 3)
        pygame.draw.circle(s, WHITE,  (21, 9), 3)
        pygame.draw.circle(s, BLACK,  (10, 9), 1)
        pygame.draw.circle(s, BLACK,  (22, 9), 1)
        return s

    def _apply_explosion(self, player):
        """Effets de l'explosion — surchargé par chaque esprit."""
        player.take_damage(10)

    def update(self, player, obstacles):
        if self.dead: return
        self.tick_contact_timer()

        dist = self.distance_to(player.rect)

        # ── Transitions ──────────────────────────────────────────
        if self.state in (self.ST_WANDER, self.ST_RETURN):
            if dist < self.DETECT_RANGE:
                self.state = self.ST_CHASE

        elif self.state == self.ST_CHASE:
            if dist > self.LOSE_RANGE:
                self.state = self.ST_RETURN
            # Déclenche l'explosion si :
            #  a) touche directement le rect du joueur
            #  b) atterrit sur le sol très proche du joueur horizontalement
            player_contact = self.rect.colliderect(player.rect)
            floor_under_player = (
                self.on_floor
                and abs(self.rect.centerx - player.rect.centerx) < self.EXPLOSION_RADIUS
                and abs(self.rect.bottom - player.rect.bottom) < 40
            )
            if player_contact or floor_under_player:
                self.state = self.ST_EXPLODE

        elif self.state == self.ST_EXPLODE:
            # Applique les effets, spawn le VFX, meurt
            self._apply_explosion(player)
            ExplosionVFX(
                self.rect.center,
                self.COULEUR_CORPS,
                self.EXPLOSION_RADIUS,
                self.vfx_groups
            )
            self.on_death()
            return

        # ── Physique + actions ───────────────────────────────────
        self._apply_gravity_esprit(obstacles)

        if self.state == self.ST_WANDER:
            self.bounce_timer -= 1
            if self.bounce_timer <= 0 and self.on_floor:
                self.vy = self.JUMP_FORCE * 0.4
                self.bounce_timer = random.randint(80, 140)

        elif self.state == self.ST_RETURN:
            if self._do_return_to_spawn(obstacles):
                self.state = self.ST_WANDER

        elif self.state == self.ST_CHASE:
            d = 1 if player.rect.centerx > self.rect.centerx else -1
            self._try_move(d * self.SPEED, obstacles)
            # Saute en continu pour franchir les obstacles ET s'élancer sur le joueur
            if self.on_floor:
                # Saut plus fort si le joueur est au-dessus
                player_above = player.rect.centery < self.rect.centery - 20
                force = self.JUMP_FORCE * 1.1 if player_above else self.JUMP_FORCE * 0.9
                self.vy = force

    def _apply_gravity_esprit(self, obstacles):
        self.vy += 0.8
        if self.vy > 14: self.vy = 14
        self.rect.y  += int(self.vy)
        self.on_floor = False
        for hit in pygame.sprite.spritecollide(self, obstacles, False):
            if self.vy > 0:
                self.rect.bottom = hit.rect.top
                self.vy = 0; self.on_floor = True


# ── Esprit du Feu ──────────────────────────────────────────────

class EspritFeu(EspritBase):
    """
    Rapide — saute et explose en brûlant le joueur (DOT).
    Capacité absorbable : "fireball"
    """
    SPEED            = 4
    JUMP_FORCE       = -12
    DETECT_RANGE     = 450
    LOSE_RANGE       = 650
    EXPLOSION_RADIUS = 60
    COULEUR_CORPS    = (220, 60,  0)
    COULEUR_AURA     = (255, 200, 0)
    BURN_DPS         = 5
    BURN_DUR         = 3   # secondes

    def __init__(self, pos, groups, vfx_groups=None):
        super().__init__(pos, groups, hp=30, capacite="fireball",
                         vfx_groups=vfx_groups)
        self.image = self._build_img(30, 30)

    def _apply_explosion(self, player):
        player.take_damage(12)
        if hasattr(player, 'burn_timer'):
            player.burn_timer = self.BURN_DUR * 60
            player.burn_dps   = self.BURN_DPS


# ── Esprit de Glace ────────────────────────────────────────────

class EspritGlace(EspritBase):
    """
    Lent mais gèle le joueur à l'explosion (slow puissant + zone).
    Capacité absorbable : "ice_shot"
    """
    SPEED            = 1
    JUMP_FORCE       = -8
    DETECT_RANGE     = 350
    LOSE_RANGE       = 500
    EXPLOSION_RADIUS = 70    # plus grand — zone de gel
    COULEUR_CORPS    = BLUE_ICE
    COULEUR_AURA     = CYAN
    SLOW_DUR         = 180   # ~3 s
    SLOW_FAC         = 0.25

    def __init__(self, pos, groups, vfx_groups=None):
        super().__init__(pos, groups, hp=35, capacite="ice_shot",
                         vfx_groups=vfx_groups)
        self.image = self._build_img_ice(30, 30)

    def _build_img_ice(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        pygame.draw.ellipse(s, BLUE_ICE, (0, 4, w, h - 4))
        pygame.draw.ellipse(s, CYAN,     (5, 0, w - 10, h // 2))
        # Cristaux de glace
        for cx, cy in [(5, 18), (15, 22), (24, 16)]:
            pygame.draw.polygon(s, WHITE,
                                [(cx, cy-6), (cx+3, cy), (cx, cy+4), (cx-3, cy)])
        pygame.draw.circle(s, WHITE,    (9,  9), 3)
        pygame.draw.circle(s, WHITE,    (21, 9), 3)
        pygame.draw.circle(s, BLUE_DARK, (10, 9), 1)
        pygame.draw.circle(s, BLUE_DARK, (22, 9), 1)
        return s

    def _apply_explosion(self, player):
        player.take_damage(8)
        player.slow_timer  = self.SLOW_DUR
        player.slow_factor = self.SLOW_FAC


# ── Esprit de Foudre ───────────────────────────────────────────

class EspritFoudre(EspritBase):
    """
    Très rapide — se téléporte près du joueur puis plonge dessus.
    L'explosion électrique inflige des dégâts + impulsion verticale.
    Capacité absorbable : "thunder"
    """
    SPEED            = 5
    JUMP_FORCE       = -14
    DETECT_RANGE     = 500
    LOSE_RANGE       = 700
    EXPLOSION_RADIUS = 55
    COULEUR_CORPS    = (180, 180, 0)
    COULEUR_AURA     = ELECTRIC
    SHOCK_DAMAGE     = 18
    TELEPORT_CD      = 150   # frames entre téléportations

    def __init__(self, pos, groups, vfx_groups=None):
        super().__init__(pos, groups, hp=25, capacite="thunder",
                         vfx_groups=vfx_groups)
        self.image   = self._build_img_thunder(30, 30)
        self.tp_timer = 0

    def _build_img_thunder(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        pygame.draw.ellipse(s, (180, 180, 20), (0, 4, w, h - 4))
        pygame.draw.ellipse(s, ELECTRIC,       (5, 0, w - 10, h // 2))
        pts = [(15, 2), (9, 13), (14, 13), (7, 27), (19, 11), (13, 11)]
        pygame.draw.polygon(s, WHITE, pts)
        pygame.draw.circle(s, WHITE,  (9,  9), 3)
        pygame.draw.circle(s, WHITE,  (21, 9), 3)
        pygame.draw.circle(s, BLACK,  (10, 9), 1)
        pygame.draw.circle(s, BLACK,  (22, 9), 1)
        return s

    def update(self, player, obstacles):
        if self.dead: return

        # Téléportation périodique en CHASE pour se repositionner
        if self.state == self.ST_CHASE:
            if self.tp_timer > 0:
                self.tp_timer -= 1
            elif self.on_floor:
                # Se téléporte à côté du joueur avant de sauter
                offset_x = random.choice([-80, 80])
                nx = max(32, min(1920 - 32, player.rect.centerx + offset_x))
                self.rect.centerx = nx
                self.rect.bottom  = player.rect.bottom
                self.vy           = 0
                self.tp_timer     = self.TELEPORT_CD

        super().update(player, obstacles)

    def _apply_explosion(self, player):
        player.take_damage(self.SHOCK_DAMAGE)
        # Impulsion : propulse le joueur vers le haut
        if hasattr(player, 'direction'):
            player.direction.y = -10


# ── Esprit de Nature ───────────────────────────────────────────

class EspritNature(EspritBase):
    """
    Empoisonne le joueur à l'explosion + soigne ses alliés proches.
    Capacité absorbable : "poison_cloud"
    """
    SPEED            = 2
    JUMP_FORCE       = -10
    DETECT_RANGE     = 350
    LOSE_RANGE       = 500
    EXPLOSION_RADIUS = 65
    COULEUR_CORPS    = NATURE_GREEN
    COULEUR_AURA     = GREEN_LIGHT
    POISON_DPS       = 3
    POISON_DUR       = 4   # secondes
    HEAL_AMOUNT      = 8
    HEAL_RADIUS      = 130
    HEAL_CD          = 180

    def __init__(self, pos, groups, vfx_groups=None):
        super().__init__(pos, groups, hp=20, capacite="poison_cloud",
                         vfx_groups=vfx_groups)
        self.image      = self._build_img_nature(30, 30)
        self.heal_timer = 0

    def _build_img_nature(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        pygame.draw.ellipse(s, NATURE_GREEN, (0, 4, w, h - 4))
        pygame.draw.ellipse(s, GREEN_LIGHT,  (5, 0, w - 10, h // 2))
        for angle, r in [(0, 8), (120, 8), (240, 8)]:
            rad = math.radians(angle)
            lx  = int(15 + r * math.cos(rad))
            ly  = int(15 + r * math.sin(rad))
            pygame.draw.ellipse(s, (0, 160, 30), (lx - 4, ly - 3, 8, 6))
        pygame.draw.circle(s, WHITE,  (9,  9), 3)
        pygame.draw.circle(s, WHITE,  (21, 9), 3)
        pygame.draw.circle(s, BLACK,  (10, 9), 1)
        pygame.draw.circle(s, BLACK,  (22, 9), 1)
        return s

    def update(self, player, obstacles):
        if self.dead: return
        # Soin des alliés pendant la chasse
        if self.heal_timer > 0: self.heal_timer -= 1
        super().update(player, obstacles)

    def heal_allies(self, monster_group):
        """À appeler depuis le Game — soigne les voisins."""
        if self.heal_timer > 0 or self.dead: return
        for ally in monster_group:
            if ally is self or ally.dead: continue
            if self.distance_to(ally.rect) < self.HEAL_RADIUS:
                ally.hp_current = min(ally.hp_max,
                                      ally.hp_current + self.HEAL_AMOUNT)
        self.heal_timer = self.HEAL_CD

    def _apply_explosion(self, player):
        player.take_damage(6)
        if hasattr(player, 'is_poisoned'):
            player.is_poisoned  = True
            player.poison_timer = self.POISON_DUR * 60
            player.poison_dps   = self.POISON_DPS


# ================================================================
#  GOLEM DE PIERRE  (corrigé : sprites pré-calculés, plus de lag)
# ================================================================

class GolemPierre(BaseEnemy):

    PATROL_SPEED   = 0
    PATROL_RADIUS  = 0
    SPEED          = 1
    DETECT_RANGE   = 600
    LOSE_RANGE     = 900
    STOMP_RANGE    = 90
    QUAKE_RANGE    = 350
    STOMP_DAMAGE   = 25
    QUAKE_DAMAGE   = 15
    QUAKE_SLOW_DUR = 120
    QUAKE_SLOW_FAC = 0.4
    ATTACK_CD      = 90
    REINFORCE_DUR  = 60

    ST_SLEEP     = "sleep"
    ST_RETURN    = "return"
    ST_CHASE     = "chase"
    ST_REINFORCE = "reinforce"
    ST_STOMP     = "stomp"
    ST_QUAKE     = "quake"

    def __init__(self, pos, groups, screen_shake_ref=None):
        super().__init__(pos, hp=200, groups=groups, capacite_absorbable="stone_armor")
        self.CONTACT_COOLDOWN = 120
        self.screen_shake_ref = screen_shake_ref

        w, h = 56, 72
        # ── Pré-calcul des surfaces (UNE SEULE FOIS) ────────────
        self._img_sleep  = self._build_img(w, h, active=False)
        self._img_active = self._build_img(w, h, active=True)
        # Deux frames de clignotement pour le reinforce
        self._img_blink0 = self._build_img(w, h, active=True)
        self._img_blink1 = self._build_img(w, h, active=False)

        self.image = self._img_sleep
        self.rect  = self.image.get_rect(topleft=pos)

        self.state           = self.ST_SLEEP
        self.facing_right    = True
        self.attack_timer    = 0
        self.reinforce_timer = 0
        self._pending_attack = self.ST_STOMP
        self.vy              = 0

    @staticmethod
    def _build_img(w, h, active=True):
        eye_col  = (220, 30, 30) if active else (50, 20, 20)
        glow_col = (255, 60, 60) if active else (40, 10, 10)
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        pygame.draw.rect(s, GRAY,        (8, 16, 40, 56))
        pygame.draw.rect(s, GRAY,        (4,  0, 48, 24))
        pygame.draw.line(s, (80, 70, 60), (14, 20), (28, 42), 2)
        pygame.draw.line(s, (80, 70, 60), (38, 14), (30, 36), 2)
        pygame.draw.rect(s, eye_col,  (10, 6, 12, 10))
        pygame.draw.rect(s, eye_col,  (34, 6, 12, 10))
        pygame.draw.circle(s, glow_col, (16, 11), 4)
        pygame.draw.circle(s, glow_col, (40, 11), 4)
        pygame.draw.rect(s, (90, 80, 70),   (0,  24, 10, 32))
        pygame.draw.rect(s, (90, 80, 70),   (46, 24, 10, 32))
        pygame.draw.rect(s, (110, 100, 90), (0,  52, 12, 14))
        pygame.draw.rect(s, (110, 100, 90), (44, 52, 12, 14))
        return s

    def update(self, player, obstacles):
        if self.dead: return
        self.tick_contact_timer()
        self._apply_gravity(obstacles)
        dist = self.distance_to(player.rect)

        if self.attack_timer > 0: self.attack_timer -= 1

        # Reinforce : figé, clignotement par swap de surface pré-calculée
        if self.reinforce_timer > 0:
            self.reinforce_timer -= 1
            self.image = self._img_blink0 if (self.reinforce_timer // 8) % 2 == 0 \
                         else self._img_blink1
            return

        # Transitions
        if self.state == self.ST_SLEEP:
            if dist < self.DETECT_RANGE:
                self.image = self._img_active
                self.state = self.ST_CHASE

        elif self.state == self.ST_RETURN:
            pass

        elif self.state == self.ST_CHASE:
            if dist > self.LOSE_RANGE:
                self.image = self._img_sleep
                self.state = self.ST_RETURN
            elif dist <= self.STOMP_RANGE:
                self._pending_attack = self.ST_STOMP
                self.reinforce_timer = self.REINFORCE_DUR
            elif dist <= self.QUAKE_RANGE:
                self._pending_attack = self.ST_QUAKE
                self.reinforce_timer = self.REINFORCE_DUR

        elif self.state == self.ST_REINFORCE:
            self.state = self._pending_attack

        elif self.state in (self.ST_STOMP, self.ST_QUAKE):
            self.state = self.ST_CHASE

        # Actions
        d = 1 if player.rect.centerx > self.rect.centerx else -1
        self.facing_right = (d == 1)

        if self.state == self.ST_CHASE:
            self._try_move(d * self.SPEED, obstacles)

        elif self.state == self.ST_RETURN:
            if self._do_return_to_spawn(obstacles):
                self.image = self._img_sleep
                self.state = self.ST_SLEEP

        elif self.state == self.ST_STOMP:
            if self.attack_timer == 0 and self.contact_timer == 0:
                player.take_damage(self.STOMP_DAMAGE)
                self.contact_timer = self.CONTACT_COOLDOWN
                self.attack_timer  = self.ATTACK_CD
                self.state         = self.ST_CHASE

        elif self.state == self.ST_QUAKE:
            if self.attack_timer == 0:
                self._do_quake(player)
                self.attack_timer = self.ATTACK_CD
                self.state        = self.ST_CHASE

    def _do_quake(self, player):
        dist = self.distance_to(player.rect)
        if dist <= self.QUAKE_RANGE:
            player.take_damage(self.QUAKE_DAMAGE)
            player.slow_timer  = self.QUAKE_SLOW_DUR
            player.slow_factor = self.QUAKE_SLOW_FAC
        if self.screen_shake_ref is not None:
            self.screen_shake_ref[0] = 20


# ================================================================
#  ABSORPTION KIRBY  —  logique côté joueur
# ================================================================
"""
──────────────────────────────────────────────────────────────────
  Dans player.py — __init__ :
      self.absorbed_capacite = None
      self.slow_timer        = 0
      self.slow_factor       = 1.0
      self.burn_timer        = 0
      self.burn_dps          = 0

  Dans player.py — update :
      # Ralentissement
      if self.slow_timer > 0: self.slow_timer -= 1
      else:                   self.slow_factor = 1.0
      # Brûlure
      if self.burn_timer > 0:
          self.burn_timer -= 1
          if self.burn_timer % 60 == 0:
              self.hp_current = max(0, self.hp_current - self.burn_dps)

  Dans player.py — move / get_input :
      effective_speed = self.current_speed * self.slow_factor

  Quand un monstre meurt (Game/TestMob) :
      cap = getattr(m, 'capacite_absorbable', None)
      if cap:
          player.absorbed_capacite = cap
          # → déclencher l'animation d'absorption, activer la capa dans Capacite.py

──────────────────────────────────────────────────────────────────
  TABLE DES CAPACITÉS
──────────────────────────────────────────────────────────────────
  "dash"          ChienEnrage    — sprint rapide
  "slash"         GoblinMelee    — attaque mêlée rapide
  "arrow"         GoblinArcher   — tir de flèche
  "fireball"      EspritFeu      — boule de feu brûlante
  "ice_shot"      EspritGlace    — projectile glaçant (slow)
  "thunder"       EspritFoudre   — éclair (damage + impulsion)
  "poison_cloud"  EspritNature   — nuage empoisonnant
  "stone_armor"   GolemPierre    — armure temporaire

──────────────────────────────────────────────────────────────────
  SPRITES ANIMÉS — quand les PNG sont prêts
──────────────────────────────────────────────────────────────────
  Décommenter _load_sprites() dans chaque __init__.
  Structure :
    assets/images/monstres/chien_enrage/wander/frame_001.png ...
  Puis dans update() :
    self.image = self._animate(self.state, dt)
    if not self.facing_right:
        self.image = pygame.transform.flip(self.image, True, False)

──────────────────────────────────────────────────────────────────
  SCREEN-SHAKE (GolemPierre)
──────────────────────────────────────────────────────────────────
  Dans TestMob.__init__ :
      self.shake_ref = [0]
  Passer à GolemPierre(..., screen_shake_ref=self.shake_ref)
  Dans draw() :
      shake = 0
      if self.shake_ref[0] > 0:
          self.shake_ref[0] -= 1
          shake = random.randint(-6, 6)
      self.screen.blit(self.background, (shake, shake))
"""