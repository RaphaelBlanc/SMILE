import pygame
import os

pygame.display.init()
pygame.display.set_mode((1, 1))

base_path = './assets/images/monstre/boss_glace'
folders = ['idle', 'walk', '1_atk', 'take_hit', 'death']

min_x, min_y = 9999, 9999
max_x, max_y = -1, -1

for folder in folders:
    dir_path = os.path.join(base_path, folder, folder)
    if not os.path.exists(dir_path):
        continue
    files = [f for f in os.listdir(dir_path) if f.endswith('.png')]
    for f in files:
        img = pygame.image.load(os.path.join(dir_path, f)).convert_alpha()
        r = img.get_bounding_rect()
        if r.width > 0:
            if r.left < min_x: min_x = r.left
            if r.top < min_y: min_y = r.top
            if r.right > max_x: max_x = r.right
            if r.bottom > max_y: max_y = r.bottom

print(f"Combined Bounding Box: left={min_x}, top={min_y}, right={max_x}, bottom={max_y}")
print(f"Width: {max_x - min_x}, Height: {max_y - min_y}")
