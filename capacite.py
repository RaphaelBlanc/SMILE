import pygame

#CLASS capacite########################################################################

class Capacite:
    def __init__(self, player):
        self.player = player
        self.last_dash_time = 0
        self.last_fire_time = 0      # Stocke le moment du dernier tir
        self.fire_cooldown = 500
        self.projectiles = pygame.sprite.Group() # On stocke les boules de feu ici

    def dash(self, obstacles):
        current_time = pygame.time.get_ticks()
        keys = pygame.key.get_pressed()

        if keys[pygame.K_v] and (current_time - self.last_dash_time > 1000):
            dash_dir = pygame.math.Vector2(1, 0)
            if self.player.direction.x < 0:
                dash_dir = pygame.math.Vector2(-1, 0)
            
            for _ in range(10):
                self.player.rect.x += int(dash_dir.x * 12)
                self.player.check_collision('horizontal', obstacles)
            
            self.player.direction.y = 0
            self.last_dash_time = current_time

    def bdf(self):
        keys = pygame.key.get_pressed()
        current_time = pygame.time.get_ticks() # On récupère le temps actuel
        
        if keys[pygame.K_f] and (current_time - self.last_fire_time > self.fire_cooldown): # Touche F pour tirer

            keys = pygame.key.get_pressed()
            if self.player.facing_right:
                direction = 1
            else:
                direction = -1
            # On crée la boule de feu à la position du joueur
            nouvelle_boule = Projectile(self.player.rect.center, direction)
            self.projectiles.add(nouvelle_boule)

            self.last_fire_time = current_time

#CLASS Projectile########################################################################

class Projectile(pygame.sprite.Sprite):
    def __init__(self, pos, direction):
        super().__init__()
        self.image = pygame.Surface((16, 16))
        self.image.fill((255, 165, 0)) # Orange
        self.rect = self.image.get_rect(center=pos)
        self.speed = 15
        self.direction = direction # 1 ou -1

    def update(self, obstacles):
        # La boule avance toute seule
        self.rect.x += self.speed * self.direction
        
        # Si elle touche un mur, elle disparaît
        if pygame.sprite.spritecollide(self, obstacles, False):
            self.kill()
        
        # Si elle sort de l'écran, on la supprime pour ne pas ramer
        if self.rect.x < 0 or self.rect.x > 1920:
            self.kill()
