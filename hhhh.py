import pygame as pg
import sys

# --- Constantes du Jeu ---
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
TILE_SIZE = 16  # Taille des tuiles (16x16 pixels)
FPS = 60
BG_COLOR = (135, 206, 235)  # Bleu ciel

# --- Vitesse et Gravité ---
GRAVITY = 0.8        
JUMP_STRENGTH = -16  
PLAYER_SPEED = 7     

# --- Définition du Terrain (Map) ---
MAP_COLS = SCREEN_WIDTH // TILE_SIZE
MAP_ROWS = SCREEN_HEIGHT // TILE_SIZE

# --- CORRECTION APPLIQUÉE ICI ---
# 1. Créer une liste de chaînes de caractères ('0' pour le ciel) pour toutes les rangées
GAME_MAP = ['0' * MAP_COLS for _ in range(MAP_ROWS)]

# 2. Placer le sol sur la dernière rangée
GAME_MAP[MAP_ROWS - 1] = '1' * MAP_COLS 

# 3. Placer la petite plateforme pour tester les sauts
# L'indice est maintenant valide car GAME_MAP a MAP_ROWS éléments
# Note: On doit s'assurer que la longueur totale de la chaîne reste MAP_COLS
platform_padding_width = MAP_COLS // 2 - 5 
# On recalcule la marge restante pour s'assurer que la chaîne fait exactement MAP_COLS de long
platform_start_index = platform_padding_width
platform_end_index = platform_padding_width + 10
remaining_padding = MAP_COLS - platform_end_index

GAME_MAP[MAP_ROWS - 5] = '0' * platform_start_index + '1' * 10 + '0' * remaining_padding

# --- Reste des Classes (identiques) ---

class Tile(pg.sprite.Sprite):
    def __init__(self, x, y, size):
        super().__init__()
        self.image = pg.Surface([size, size])
        self.image.fill((34, 139, 34)) 
        self.rect = self.image.get_rect(topleft=(x, y))

class Player(pg.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.width = 16
        self.height = 32
        self.image = pg.Surface([self.width, self.height])
        self.image.fill((255, 0, 0)) 
        self.rect = self.image.get_rect(topleft=(x, y))
        self.velocity = pg.math.Vector2(0, 0)
        self.on_ground = False
        
    def get_input(self, keys):
        if keys[pg.K_d]:
            self.velocity.x = PLAYER_SPEED
        elif keys[pg.K_q]:
            self.velocity.x = -PLAYER_SPEED
        else:
            self.velocity.x = 0
            
        if keys[pg.K_SPACE] and self.on_ground:
            self.velocity.y = JUMP_STRENGTH
            self.on_ground = False

    def apply_gravity(self):
        self.velocity.y += GRAVITY
        if self.velocity.y > 20: 
            self.velocity.y = 20
        self.rect.y += self.velocity.y
        
    def horizontal_movement_collision(self, tiles):
        self.rect.x += self.velocity.x
        
        # Gestion des bords de l'écran
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH

        # Collision avec les tuiles
        for tile in tiles:
            if self.rect.colliderect(tile.rect):
                if self.velocity.x > 0:
                    self.rect.right = tile.rect.left
                elif self.velocity.x < 0:
                    self.rect.left = tile.rect.right

    def vertical_movement_collision(self, tiles):
        self.apply_gravity()
        self.on_ground = False
        
        for tile in tiles:
            if self.rect.colliderect(tile.rect):
                if self.velocity.y > 0:
                    self.rect.bottom = tile.rect.top
                    self.velocity.y = 0
                    self.on_ground = True
                elif self.velocity.y < 0:
                    self.rect.top = tile.rect.bottom
                    self.velocity.y = 0

    def update(self, keys, tiles):
        self.get_input(keys)
        self.horizontal_movement_collision(tiles)
        self.vertical_movement_collision(tiles)
            
class Level:
    def __init__(self, surface, map_data):
        self.display_surface = surface
        self.setup_level(map_data)
        
    def setup_level(self, map_data):
        self.tiles = pg.sprite.Group()
        self.player = pg.sprite.GroupSingle()
        
        for row_index, row in enumerate(map_data):
            for col_index, tile_char in enumerate(row):
                x = col_index * TILE_SIZE
                y = row_index * TILE_SIZE
                
                if tile_char == '1': 
                    tile_sprite = Tile(x, y, TILE_SIZE)
                    self.tiles.add(tile_sprite)

        player_start_y = (MAP_ROWS - 2) * TILE_SIZE - 32
        self.player.add(Player(400, player_start_y))
        
    def run(self):
        self.tiles.draw(self.display_surface)
        keys = pg.key.get_pressed()
        self.player.update(keys, self.tiles.sprites())
        self.player.draw(self.display_surface)

def main():
    pg.init()
    screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pg.display.set_caption("Metroidvania - Zone de Test Statique (1920x1080)")
    clock = pg.time.Clock()
    
    level = Level(screen, GAME_MAP)
    
    while True:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.quit()
                sys.exit()
                
        screen.fill(BG_COLOR)
        level.run()
        
        pg.display.flip()
        clock.tick(FPS)

if __name__ == '__main__':
    main()
