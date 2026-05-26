import pygame
import sys
sys.path.append('src')
from main import Game

pygame.init()
pygame.display.set_mode((1920, 1072))

game = Game()
game.load_map('assets/maps/map_glace.tmx')

game.player.hitbox.bottom = 2720
game.player.hitbox.right = 3100
game.player.hitbox.y = 2720 - 128
game.player.hitbox.x = 3100 - 128

game.player.direction.x = 1
game.player.current_speed = 10
effective_speed = game.player.current_speed * game.player.slow_factor
game.player.hitbox.x += int(game.player.direction.x * effective_speed)

game.player.rect = game.player.hitbox
print("Player rect:", game.player.rect)

# manually check collision with ALL obstacles
manual_hits = []
for obs in game.obstacle_sprites:
    if game.player.rect.colliderect(obs.rect):
        manual_hits.append(obs)

print("Manual hits:", [h.rect for h in manual_hits])

# move up
game.player.hitbox.y -= 32
print("Player rect after step:", game.player.rect)

manual_hits2 = []
for obs in game.obstacle_sprites:
    if game.player.rect.colliderect(obs.rect):
        manual_hits2.append(obs)

print("Manual hits after step:", [h.rect for h in manual_hits2])

