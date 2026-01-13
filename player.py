
import pygame 
from capacite import Capacite

# settings.py
RED = (255, 0, 0)
GRAVITY = 0.8
JUMP_FORCE = -16
PLAYER_SPEED = 6
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1072
HP_MAX = 100

#CLASS PLAYER########################################################################
class Player(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image = pygame.Surface((32, 64))
        self.image.fill(RED)
        self.rect = self.image.get_rect(topleft=pos)
        
        self.direction = pygame.math.Vector2(0, 0)
        self.facing_right = True 

        self.count_jump = 0
        self.jump_pressed = False

        self.last_dash_time = 0
        self.capacite = Capacite(self) 

        self.normal_speed = 6
        self.sprint_speed = 10
        self.current_speed = self.normal_speed

        self.hp_max = HP_MAX
        self.hp_current = 100
        self.health_bar_length = 200

    def get_input(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_d]:
            self.direction.x = 1
            self.facing_right = True
        elif keys[pygame.K_a]:
            self.direction.x = -1
            self.facing_right = False
        else:
            self.direction.x = 0

        if keys[pygame.K_LSHIFT]:
            self.current_speed = self.sprint_speed
        else:
            self.current_speed = self.normal_speed
        
        if keys[pygame.K_SPACE] and not self.jump_pressed:
            self.jump()
            self.jump_pressed = True
        if not keys[pygame.K_SPACE]:
            self.jump_pressed = False
    
    def jump(self):
        if self.count_jump < 2:
            self.direction.y = JUMP_FORCE
            self.count_jump += 1

    def apply_gravity(self):
        self.direction.y += GRAVITY
        # On limite la vitesse de chute pour éviter que le perso traverse le sol
        if self.direction.y > 16:
            self.direction.y = 16

    def move(self, obstacles):
        # Mouvement horizontal
        self.rect.x += self.direction.x * self.current_speed
        self.check_collision('horizontal', obstacles)
        # Mouvement vertical
        self.rect.y += self.direction.y
        self.check_collision('vertical', obstacles)

    def check_collision(self, direction, obstacles):
        hits = pygame.sprite.spritecollide(self, obstacles, False)
        if hits:
            if direction == 'horizontal':
                if self.direction.x > 0: self.rect.right = hits[0].rect.left
                if self.direction.x < 0: self.rect.left = hits[0].rect.right
            if direction == 'vertical':
                if self.direction.y > 0:
                    self.rect.bottom = hits[0].rect.top
                    self.direction.y = 0
                    self.count_jump = 0
                if self.direction.y < 0:
                    self.rect.top = hits[0].rect.bottom
                    self.direction.y = 0

    def update(self, obstacles):
        self.get_input()
        self.capacite.bdf() 
        self.capacite.projectiles.update(obstacles)
        
        self.apply_gravity()   # Puis la gravité s'applique
        self.move(obstacles)    # Puis on déplace normalement
        self.capacite.dash(obstacles)
