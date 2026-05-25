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
        self.owner = None
        
        # Dimensions et positionnement
        self.box_width = 800
        self.box_height = 150
        x_pos = (SCREEN_WIDTH - self.box_width) // 2
        y_pos = SCREEN_HEIGHT - self.box_height - 50 
        self.rect = pygame.Rect(x_pos, y_pos, self.box_width, self.box_height)

    def show(self, text, owner=None):
        self.text = text
        self.visible = True
        if owner is not None:
            self.owner = owner

    def hide(self):
        self.visible = False
        self.owner = None

    def draw(self):
        if self.visible:
            # Texte centré
            text_surf = self.font.render(self.text, True, BLACK)
            text_rect = text_surf.get_rect(center=self.rect.center)
            
            # Contour blanc pour lisibilité
            outline = self.font.render(self.text, True, WHITE)
            self.screen.blit(outline, (text_rect.x - 2, text_rect.y))
            self.screen.blit(outline, (text_rect.x + 2, text_rect.y))
            self.screen.blit(outline, (text_rect.x, text_rect.y - 2))
            self.screen.blit(outline, (text_rect.x, text_rect.y + 2))
            
            self.screen.blit(text_surf, text_rect)

class NPC(pygame.sprite.Sprite):
    def __init__(self, pos, message, groups):
        super().__init__(groups)
        self.image = pygame.Surface((32, 64))
        self.image.fill((0, 0, 255)) # Bleu pour le PNJ
        self.rect = self.image.get_rect(topleft=pos)
        
        self.messages = message.split('|') if message else ["..."]
        self.msg_index = 0
        self.detection_radius = 150
        self.player_in_range = False
        self.is_interacting = False

    def update(self, player_rect, dialogue_box):
        npc_center = pygame.math.Vector2(self.rect.center)
        player_center = pygame.math.Vector2(player_rect.center)
        distance = npc_center.distance_to(player_center)
        
        if distance <= self.detection_radius:
            self.player_in_range = True
            if self.is_interacting:
                current_text = self.messages[self.msg_index]
                if len(self.messages) > 1:
                    current_text += " [E pour suite]"
                dialogue_box.show(current_text, owner=self)
            else:
                dialogue_box.show("Appuyez sur [E] pour interagir", owner=self)
        else:
            self.player_in_range = False
            self.is_interacting = False
            self.msg_index = 0
            if getattr(dialogue_box, 'owner', None) == self:
                dialogue_box.hide()

    def interact(self):
        if self.player_in_range:
            if not self.is_interacting:
                self.is_interacting = True
                self.msg_index = 0
            else:
                self.msg_index += 1
                if self.msg_index >= len(self.messages):
                    self.is_interacting = False
                    self.msg_index = 0