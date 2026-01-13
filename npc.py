import pygame

# Constantes pour le dessin de l'UI
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1072

class DialogueBox:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont("Arial", 30)
        self.visible = False
        self.text = ""
        
        # Dimensions et positionnement
        self.box_width = 800
        self.box_height = 150
        x_pos = (SCREEN_WIDTH - self.box_width) // 2
        y_pos = SCREEN_HEIGHT - self.box_height - 50 
        self.rect = pygame.Rect(x_pos, y_pos, self.box_width, self.box_height)

    def show(self, text):
        self.text = text
        self.visible = True

    def hide(self):
        self.visible = False

    def draw(self):
        if self.visible:
            # Fond et bordure
            pygame.draw.rect(self.screen, BLACK, self.rect)
            pygame.draw.rect(self.screen, WHITE, self.rect, 4)
            
            # Texte centré
            text_surf = self.font.render(self.text, True, WHITE)
            text_rect = text_surf.get_rect(center=self.rect.center)
            self.screen.blit(text_surf, text_rect)

class NPC(pygame.sprite.Sprite):
    def __init__(self, pos, message, groups):
        super().__init__(groups)
        self.image = pygame.Surface((32, 64))
        self.image.fill((0, 0, 255)) # Bleu pour le PNJ
        self.rect = self.image.get_rect(topleft=pos)
        
        self.message = message
        self.detection_radius = 150

    def update(self, player_rect, dialogue_box):
        # Calcul de la distance avec le joueur
        npc_center = pygame.math.Vector2(self.rect.center)
        player_center = pygame.math.Vector2(player_rect.center)
        distance = npc_center.distance_to(player_center)
        
        if distance <= self.detection_radius:
            dialogue_box.show(self.message)
        else:
            # On ne cache la boite que si c'est notre message qui est affiché
            if dialogue_box.text == self.message:
                dialogue_box.hide()