import pygame
import sys

pygame.init()
pygame.display.set_mode((1, 1), pygame.HIDDEN)
img = pygame.image.load('assets/images/trophy.png').convert_alpha()
w, h = img.get_size()

# BFS floodfill
visited = set()
queue = [(0,0), (w-1,0), (0,h-1), (w-1,h-1)]

for q in queue:
    visited.add(q)

transparent = pygame.Color(0,0,0,0)

def is_bg(c):
    r, g, b, a = c
    if a == 0: return True
    if abs(r-g) < 20 and abs(g-b) < 20 and r > 100:
        return True
    return False

head = 0
while head < len(queue):
    x, y = queue[head]
    head += 1
    
    c = img.get_at((x, y))
    if is_bg(c):
        img.set_at((x, y), transparent)
        for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
            nx, ny = x+dx, y+dy
            if 0 <= nx < w and 0 <= ny < h:
                if (nx, ny) not in visited:
                    visited.add((nx, ny))
                    queue.append((nx, ny))

pygame.image.save(img, 'assets/images/trophy.png')
print("Done")
