import pygame
import sys
sys.path.append('src')
from main import Game, Tile

pygame.init()
pygame.display.set_mode((1920, 1072))

game = Game()
game.obstacle_sprites = pygame.sprite.Group()
game.ladder_sprites = pygame.sprite.Group()

dummy_surf = pygame.Surface((32, 32))
game.player.hitbox.bottom = 2720
game.player.hitbox.right = 3168
game.player.hitbox.y = 2720 - 128

# Step FIRST, then Floor
t2 = Tile((3168, 2688), dummy_surf, [game.obstacle_sprites])
t1 = Tile((3136, 2720), dummy_surf, [game.obstacle_sprites])

# Simulate move right
game.player.direction.x = 1
game.player.current_speed = 10
game.player.move(game.obstacle_sprites, game.ladder_sprites)

# Simulate gravity
game.player.direction.x = 0
game.player.direction.y = 5
game.player.move(game.obstacle_sprites, game.ladder_sprites)

print(f"After vertical gravity - Player bottom: {game.player.hitbox.bottom}")

