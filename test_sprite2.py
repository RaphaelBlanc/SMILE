import pygame
pygame.display.init()
pygame.display.set_mode((1,1))
img = pygame.image.load('./assets/images/monstre/boss_glace.png')
print(f"Size: {img.get_width()}x{img.get_height()}")
