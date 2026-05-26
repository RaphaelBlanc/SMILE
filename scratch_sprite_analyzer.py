import pygame

pygame.display.init()
pygame.display.set_mode((1,1))
img = pygame.image.load('./assets/images/monstre/boss_glace-removebg-preview.png')
w, h = img.get_size()
print(f"Dimensions: {w}x{h}")
if h % 128 == 0:
    print(f"Likely 128x128 frames. Cols={w/128}, Rows={h/128}")
elif h % 96 == 0:
    print(f"Likely {w/(h/96)}x96 frames. Rows={h/96}")
elif h % 6 == 0:
    print(f"6 Rows: {w/(h/6)}x{h/6}")
else:
    print(f"Not perfectly divisible. Rows estimate 6 => width={w}, height={h}, h/6={h/6}")
