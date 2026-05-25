import pygame

# On définit les constantes nécessaires pour ce fichier
ORANGE = (255, 165, 0)
SCREEN_WIDTH = 1920

#CLASS PROJECTILE #########################################################

class Projectile(pygame.sprite.Sprite):
    def __init__(self, pos, direction):
        super().__init__()
        self.image = pygame.Surface((16, 16))
        self.image.fill(ORANGE) 
        self.rect = self.image.get_rect(center=pos)
        self.speed = 15
        self.direction = direction 
        self.life = 0

    def update(self, obstacles):
        # Mouvement simple
        self.rect.x += self.speed * self.direction
        
        # Destruction si collision ou fin de vie
        if pygame.sprite.spritecollide(self, obstacles, False):
            self.kill()
        
        self.life += 1
        if self.life > 100:  # Environ 1.6 secondes de durée de vol (à 60 FPS)
            self.kill()

#CLASS CAPACITE ###########################################################

class Capacite:
    def __init__(self, player):
        self.player = player
        self.last_dash_time = 0
        self.last_fire_time = 0      
        self.fire_cooldown = 500
        self.projectiles = pygame.sprite.Group()

    def dash(self, obstacles, dash_key=pygame.K_v, force = False):
        current_time = pygame.time.get_ticks()
        keys = pygame.key.get_pressed()

        triggered = force or keys[dash_key]

        if triggered and (current_time - self.last_dash_time > 1000):
            if self.player.facing_right:
                direction_finale = 1  # Vers la droite
            else:
                direction_finale = -1
            
            for _ in range(10):
                self.player.rect.x += int(direction_finale * 12)
                self.player.check_collision('horizontal', obstacles)
            
            self.player.direction.y = 0 
            self.last_dash_time = current_time

    def bdf(self, attack_key=pygame.K_f):
        keys = pygame.key.get_pressed()
        current_time = pygame.time.get_ticks() 
        
        if keys[attack_key] and (current_time - self.last_fire_time > self.fire_cooldown): 
            if self.player.facing_right:
                direction = 1
            else:
                direction = -1
            
            nouvelle_boule = Projectile(self.player.rect.center, direction)
            self.projectiles.add(nouvelle_boule)
            self.last_fire_time = current_time
