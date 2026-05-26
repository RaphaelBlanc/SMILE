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

for i in range(10):
    game.player.direction.x = 1
    game.player.current_speed = 10
    
    effective_speed = game.player.current_speed * game.player.slow_factor
    game.player.hitbox.x += int(game.player.direction.x * effective_speed)
    
    temp_rect = game.player.rect
    game.player.rect = game.player.hitbox
    hits = list(pygame.sprite.spritecollide(game.player, game.obstacle_sprites, False))
    
    if hits:
        highest_top = min(hit.rect.top for hit in hits)
        step_height = game.player.hitbox.bottom - highest_top
        
        if 0 < step_height <= 66:
            game.player.hitbox.y -= step_height
            new_hits = pygame.sprite.spritecollide(game.player, game.obstacle_sprites, False)
            if new_hits:
                print(f"Frame {i}: self.rect={game.player.rect}")
                print(f"Frame {i}: First hit rect={new_hits[0].rect}")
                print(f"Frame {i}: colliderect={game.player.rect.colliderect(new_hits[0].rect)}")
            game.player.hitbox.y += step_height
            
    game.player.rect = temp_rect
    game.player.check_collision('horizontal', game.obstacle_sprites)
    
    game.player.direction.y = 5
    game.player.hitbox.y += game.player.direction.y
    game.player.check_collision('vertical', game.obstacle_sprites, game.ladder_sprites)

