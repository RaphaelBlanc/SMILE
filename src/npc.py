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
    def __init__(self, pos, message, groups, on_end_callback=None, name=None, pnj_type=None):
        super().__init__(groups)
        
        # Déterminer quel sprite utiliser en fonction du nom ou du pnj_type
        sprite_filename = "vieux.png" # Fallback par défaut
        
        name_lower = str(name).lower() if name else ""
        type_lower = str(pnj_type).lower() if pnj_type else ""
        
        if "chevalier" in name_lower or "porte" in type_lower or "glace" in type_lower:
            sprite_filename = "chevalier.png"
        elif "boss" in name_lower or "boss" in type_lower:
            sprite_filename = "geant_de_glace.png"
        elif "alchimiste" in name_lower or "magic" in name_lower:
            sprite_filename = "alchimiste.png"
        elif "enfant" in name_lower:
            sprite_filename = "enfants.png"
        elif "nain" in name_lower or "savant" in name_lower:
            sprite_filename = "nain_savants.png"
        elif "orc" in name_lower or "garde" in name_lower:
            sprite_filename = "orc_armure.png"
        elif "pretre" in name_lower or "demon" in name_lower:
            sprite_filename = "pretre_demoniaque.png"
        elif "sdf" in name_lower or "pauvre" in name_lower:
            sprite_filename = "sdf.png"
        elif "maitre" in name_lower or "esclave" in name_lower:
            sprite_filename = "maitre_esclave.png"
        elif "vieux" in name_lower or "sage" in name_lower:
            sprite_filename = "vieux.png"
        else:
            if "pnj_boss" in type_lower or "pnjboss" in type_lower:
                sprite_filename = "geant_de_glace.png"
            elif "pnjporteglace" in type_lower:
                sprite_filename = "chevalier.png"
            else:
                sprite_list = [
                    "alchimiste.png", "chevalier.png", "enfants.png", 
                    "maitre_esclave.png", "nain_savants.png", "orc_armure.png", 
                    "pretre_demoniaque.png", "sdf.png", "vieux.png"
                ]
                h_idx = int(pos[0] + pos[1]) % len(sprite_list)
                sprite_filename = sprite_list[h_idx]

        # Charger l'image depuis le dossier assets
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        path_option1 = os.path.join(current_dir, "assets", "images", "pnj", sprite_filename)
        path_option2 = os.path.join(os.path.dirname(current_dir), "assets", "images", "pnj", sprite_filename)
        path = path_option1 if os.path.isfile(path_option1) else path_option2
        
        if sprite_filename == "geant_de_glace.png":
            orig_size = (96, 120)
        else:
            orig_size = (64, 88)
            
        SCALE_FACTOR = 1.8
        target_size = (int(orig_size[0] * SCALE_FACTOR), int(orig_size[1] * SCALE_FACTOR))
            
        if os.path.isfile(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                self.image = pygame.transform.scale(img, target_size)
            except Exception as e:
                print(f"⚠️ Erreur de chargement PNJ {sprite_filename} : {e}")
                self.image = pygame.Surface(target_size)
                self.image.fill((0, 0, 255))
        else:
            self.image = pygame.Surface(target_size)
            self.image.fill((0, 0, 255))
            
        # Aligne le bas-centre du sprite agrandi avec la hitbox initiale pour éviter de flotter ou s'enfoncer
        orig_rect = pygame.Rect(pos[0], pos[1], orig_size[0], orig_size[1])
        self.rect = self.image.get_rect()
        self.rect.midbottom = orig_rect.midbottom
        
        self.set_message(message)
        self.detection_radius = 200
        self.player_in_range = False
        self.is_interacting = False
        self.on_end_callback = on_end_callback

    def set_message(self, message):
        self.messages = message.split('|') if message else ["..."]
        self.msg_index = 0

    def update(self, player_rect, dialogue_box):
        npc_center = pygame.math.Vector2(self.rect.center)
        player_center = pygame.math.Vector2(player_rect.center)
        distance = npc_center.distance_to(player_center)
        
        if distance <= self.detection_radius:
            self.player_in_range = True
            if self.is_interacting:
                current_text = self.messages[self.msg_index]
                if self.msg_index < len(self.messages) - 1:
                    current_text += " [E pour suite]"
                else:
                    if self.on_end_callback:
                        current_text += " [E pour y aller]"
                    else:
                        current_text += " [E pour fermer]"
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
                    if self.on_end_callback:
                        self.on_end_callback()