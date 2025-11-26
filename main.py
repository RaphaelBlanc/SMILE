import pygame
import pytmx
import sys
import os

# --- CONFIGURATION GLOBALE ---
# ATTENTION : La fenêtre sera immense !
LARGEUR_ECRAN = 2816  # Taille exacte de votre image
HAUTEUR_ECRAN = 1536
TITRE_FENETRE = "Jeu Tiled - Full Map & Collisions"
NOM_FICHIER_CARTE = "MAPS.tmx"

# --- CONFIGURATION JOUEUR ---
PLAYER_SIZE = 32       # Taille du cube joueur en pixels
PLAYER_COLOR = (0, 255, 0) # Vert vif
PLAYER_SPEED = 5       # Vitesse de déplacement
START_X, START_Y = 100, 100 # Position de départ


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, walls_rects):
        super().__init__()
        # Création visuelle du cube
        self.image = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE))
        self.image.fill(PLAYER_COLOR)
        
        # Création de la hitbox (le rectangle physique)
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        
        self.speed = PLAYER_SPEED
        self.walls = walls_rects # Le joueur doit connaître la liste des murs

    def update(self, keys_pressed):
        # Calcul du mouvement souhaité
        dx, dy = 0, 0
        if keys_pressed[pygame.K_LEFT]:
            dx = -self.speed
        if keys_pressed[pygame.K_RIGHT]:
            dx = self.speed
        if keys_pressed[pygame.K_UP]:
            dy = -self.speed
        if keys_pressed[pygame.K_DOWN]:
            dy = self.speed

        # --- LOGIQUE DE COLLISION "GLISSANTE" ---
        # On déplace d'abord en X, puis on vérifie.
        # Ensuite on déplace en Y, puis on vérifie.
        # C'est ce qui permet de glisser contre un mur.

        # 1. Mouvement Horizontal (X)
        self.rect.x += dx
        collision_x = self.check_collision()
        if collision_x:
            if dx > 0: # On allait à droite, on a tapé le côté gauche d'un mur
                self.rect.right = collision_x.left
            elif dx < 0: # On allait à gauche, on a tapé le côté droit d'un mur
                self.rect.left = collision_x.right

        # 2. Mouvement Vertical (Y)
        self.rect.y += dy
        collision_y = self.check_collision()
        if collision_y:
            if dy > 0: # On descendait, on a tapé le haut d'un mur
                self.rect.bottom = collision_y.top
            elif dy < 0: # On montait, on a tapé le bas d'un mur
                self.rect.top = collision_y.bottom

        # Empêcher de sortir de l'écran (Optionnel, vu la taille de l'écran)
        self.rect.clamp_ip(pygame.Rect(0, 0, LARGEUR_ECRAN, HAUTEUR_ECRAN))

    def check_collision(self):
        # pygame.Rect.collidelist retourne l'index du premier rectangle touché
        # ou -1 si aucun n'est touché.
        index = self.rect.collidelist(self.walls)
        if index != -1:
            return self.walls[index] # On retourne le Rect du mur touché
        return None


def main():
    # 1. Initialisation
    pygame.init()
    # Note: Sur certains Linux, ajouter le flag pygame.FULLSCREEN pourrait aider si la fenêtre est trop grande
    # screen = pygame.display.set_mode((LARGEUR_ECRAN, HAUTEUR_ECRAN), pygame.FULLSCREEN)
    screen = pygame.display.set_mode((LARGEUR_ECRAN, HAUTEUR_ECRAN))
    pygame.display.set_caption(TITRE_FENETRE)
    clock = pygame.time.Clock()

    # 2. Chargement Sécurisé
    dossier_script = os.path.dirname(os.path.abspath(__file__))
    chemin_carte = os.path.join(dossier_script, NOM_FICHIER_CARTE)

    try:
        tmx_data = pytmx.load_pygame(chemin_carte)
    except FileNotFoundError:
        print(f"ERREUR : Fichier {NOM_FICHIER_CARTE} introuvable.")
        sys.exit()
    except Exception as e:
        print(f"Erreur lors du chargement de la carte ou de l'image : {e}")
        sys.exit()

    # 3. Préparation des Murs (Hitboxes)
    walls_list = []
    for obj in tmx_data.objects:
        # Si votre type dans Tiled est "bloquant"
        if obj.type == "bloquant":
            # On crée un rectangle Pygame pour chaque mur
            wall_rect = pygame.Rect(obj.x, obj.y, obj.width, obj.height)
            walls_list.append(wall_rect)
    
    print(f"{len(walls_list)} murs invisibles chargés.")

    # 4. Création du Joueur
    # On lui passe la liste des murs pour qu'il gère ses collisions
    player = Player(START_X, START_Y, walls_list)
    
    # Groupe de sprites (pratique pour dessiner/mettre à jour)
    all_sprites = pygame.sprite.Group()
    all_sprites.add(player)

    # --- BOUCLE PRINCIPALE ---
    running = True
    while running:
        # Gestion des entrées
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            # Raccourci pour quitter si la fenêtre est trop grande (Echap)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        keys = pygame.key.get_pressed()
        
        # Mise à jour du joueur (mouvement + collisions)
        all_sprites.update(keys)

        # --- DESSIN ---
        screen.fill((0,0,0)) # Nettoyage noir

        # A. Dessiner le fond (Image Tiled)
        for layer in tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledImageLayer) and layer.image:
                 # On dessine tout en 0,0 car pas de caméra
                screen.blit(layer.image, (0, 0))

        # B. Dessiner le joueur
        all_sprites.draw(screen)

        # C. (Optionnel) Mode Debug : Dessiner les murs en rouge pour vérifier
        # Commentez ces deux lignes si vous voulez qu'ils soient vraiment invisibles
        for wall in walls_list:
             pygame.draw.rect(screen, (255, 0, 0), wall, 2)

        pygame.display.flip()
        clock.tick(60) # 60 FPS

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()