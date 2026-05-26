import pygame
import os

pygame.display.init()
pygame.display.set_mode((1, 1))

src_path = './assets/images/monstre/boss_glace-removebg-preview.png'
dest_path = './assets/images/monstre/boss_glace_fixed.png'

sheet = pygame.image.load(src_path).convert_alpha()
w, h = sheet.get_size()

cols = 11
rows = 6

cell_w = w / cols
cell_h = h / rows

new_frame_w = 128
new_frame_h = 128

new_sheet = pygame.Surface((new_frame_w * cols, new_frame_h * rows), pygame.SRCALPHA)
new_sheet.fill((0, 0, 0, 0))

for row in range(rows):
    for col in range(cols):
        # Original cell bounds
        x1 = int(col * cell_w)
        y1 = int(row * cell_h)
        x2 = int((col + 1) * cell_w)
        y2 = int((row + 1) * cell_h)
        
        # Extract the cell
        cell_surf = pygame.Surface((x2 - x1, y2 - y1), pygame.SRCALPHA)
        cell_surf.blit(sheet, (0, 0), (x1, y1, x2 - x1, y2 - y1))
        
        # Find the bounding box of non-transparent pixels
        rect = cell_surf.get_bounding_rect()
        
        if rect.width > 0 and rect.height > 0:
            # Crop to the actual sprite
            sprite_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            sprite_surf.blit(cell_surf, (0, 0), rect)
            
            # Center horizontally, but align to the BOTTOM vertically so the boss doesn't bounce!
            target_x = col * new_frame_w + (new_frame_w - rect.width) // 2
            target_y = row * new_frame_h + (new_frame_h - rect.height) - 10 # 10px padding from bottom
            
            new_sheet.blit(sprite_surf, (target_x, target_y))

pygame.image.save(new_sheet, dest_path)
print(f"Saved fixed sprite sheet to {dest_path}")
