import pygame
import os
pygame.display.init()
pygame.display.set_mode((1,1))
img = pygame.image.load('./assets/images/monstre/boss_glace/idle/idle/idle_1.png')
print("Image size:", img.get_size())
print("Bounding rect:", img.get_bounding_rect())
