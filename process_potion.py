import pygame
import sys

pygame.init()
screen = pygame.display.set_mode((1, 1), pygame.HIDDEN)
img = pygame.image.load("assets/images/potion.png").convert_alpha()
width, height = img.get_size()

new_img = pygame.Surface((width, height), pygame.SRCALPHA)

def color_distance(c1, c2):
    return sum((a - b)**2 for a, b in zip(c1[:3], c2[:3])) ** 0.5

bg_colors = [(255, 255, 255), (230, 230, 230)]

for y in range(height):
    for x in range(width):
        c = img.get_at((x, y))
        is_bg = False
        for bg in bg_colors:
            if color_distance(c, bg) < 15:  # Tolerance for compression artifacts
                is_bg = True
                break
        if not is_bg:
            new_img.set_at((x, y), c)

pygame.image.save(new_img, "assets/images/potion.png")
print("Saved transparent potion.png")
