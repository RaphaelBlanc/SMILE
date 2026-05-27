import pygame
import math
import random
import os
import cv2
from config import ROOT_DIR, SCREEN_WIDTH, SCREEN_HEIGHT

class Particle:
    def __init__(self, x, y, color):
        self.x     = float(x)
        self.y     = float(y)
        self.vx    = random.uniform(-4, 4)
        self.vy    = random.uniform(-6, -1)
        self.life  = random.randint(18, 35)
        self.r     = random.randint(3, 7)
        self.color = color
    def update(self):
        self.x  += self.vx
        self.vy += 0.4
        self.y  += self.vy
        self.life -= 1
    def draw(self, surface):
        if self.life > 0:
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.r)
class AssetManager:
    def __init__(self):
        pass
class Tile(pygame.sprite.Sprite):
    def __init__(self, pos, surf, groups):
        super().__init__(groups)
        self.image = surf
        self.rect  = self.image.get_rect(topleft=pos)
class Camera:
    def __init__(self, map_width, map_height):
        self.map_width  = map_width
        self.map_height = map_height
        self.offset     = pygame.math.Vector2(0, 0)
        self.lerp_speed = 0.10
    def update(self, target_rect):
        target_x = target_rect.centerx - SCREEN_WIDTH  // 2
        target_y = target_rect.centery - SCREEN_HEIGHT // 2
        self.offset.x += (target_x - self.offset.x) * self.lerp_speed
        self.offset.y += (target_y - self.offset.y) * self.lerp_speed
        self.offset.x = max(0, min(self.offset.x, self.map_width  - SCREEN_WIDTH))
        self.offset.y = max(0, min(self.offset.y, self.map_height - SCREEN_HEIGHT))
    def apply(self, rect):
        return rect.move(-int(self.offset.x), -int(self.offset.y))
class RemotePlayer(pygame.sprite.Sprite):
    def __init__(self, pos, player_num=2):
        super().__init__()
        self.player_num = player_num
        self.hp_current = 100
        self.hp_max     = 100
        self.facing_right = True
        self.is_sprinting = False
        self.on_ladder = False
        self.status = "idle_right"
        self.dx = 0
        self.dy = 0
        from animator import Animator
        self.animations = {}
        self._load_assets()
        self.animator = Animator(self.animations, fps=8)
        self.image = self.animations["idle_right"][0]
        self.rect  = self.image.get_rect(topleft=pos)
    def _load_assets(self):
        import os
        from config import ROOT_DIR
        actions = [
            'idle_right', 'idle_left', 'run_right', 'run_left', 
            'sprint_right', 'sprint_left', 'jump_right', 'jump_left', 
            'land_right', 'land_left', 'death', 'back', 'front'
        ]
        self.animations = {action: [] for action in actions}
        if self.player_num == 2:
            base_path = os.path.join(ROOT_DIR, 'assets', 'images', 'player2', 'mouvements')
            prefix = "Slime2_"
            death_file = "Slime2_Death.png"
            fill_color = (0, 200, 255)
        else:
            base_path = os.path.join(ROOT_DIR, 'assets', 'images', 'player', 'mouvements')
            prefix = "Slime1_"
            death_file = "Slime1_Death_body.png"
            fill_color = (0, 200, 0)
        SLIME_SIZE = (225, 225) 
        ROW_FRONT = 0
        ROW_BACK  = 1
        ROW_LEFT  = 2
        ROW_RIGHT = 3
        def slice_sheet(filename, cols, rows):
            path = os.path.join(base_path, filename)
            if not os.path.exists(path):
                return None
            try:
                sheet = pygame.image.load(path).convert_alpha()
                frame_w = sheet.get_width() // cols
                frame_h = sheet.get_height() // rows
                sheet_frames = []
                for r in range(rows):
                    row_frames = []
                    for c in range(cols):
                        rect = pygame.Rect(c * frame_w, r * frame_h, frame_w, frame_h)
                        img = pygame.Surface((frame_w, frame_h), pygame.SRCALPHA)
                        img.blit(sheet, (0, 0), rect)
                        img = pygame.transform.scale(img, SLIME_SIZE)
                        row_frames.append(img)
                    sheet_frames.append(row_frames)
                return sheet_frames
            except Exception as e:
                print(f"Erreur decoupage {filename}: {e}")
                return None
        idle_frames = slice_sheet(f"{prefix}Idle_body.png", cols=6, rows=4)
        if idle_frames:
            self.animations['front']      = idle_frames[ROW_FRONT]
            self.animations['back']       = idle_frames[ROW_BACK]
            self.animations['idle_left']  = idle_frames[ROW_LEFT]
            self.animations['idle_right'] = idle_frames[ROW_RIGHT]
            self.animations['run_left']     = idle_frames[ROW_LEFT]
            self.animations['run_right']    = idle_frames[ROW_RIGHT]
            self.animations['sprint_left']  = idle_frames[ROW_LEFT]
            self.animations['sprint_right'] = idle_frames[ROW_RIGHT]
            self.animations['jump_left']    = idle_frames[ROW_LEFT]
            self.animations['jump_right']   = idle_frames[ROW_RIGHT]
            self.animations['land_left']    = idle_frames[ROW_LEFT]
            self.animations['land_right']   = idle_frames[ROW_RIGHT]
        death_frames = slice_sheet(death_file, cols=10, rows=4)
        if death_frames:
            self.animations['death'] = death_frames[ROW_FRONT]
        for state in self.animations:
            if not self.animations[state]:
                placeholder = pygame.Surface(SLIME_SIZE, pygame.SRCALPHA)
                placeholder.fill(fill_color)
                self.animations[state].append(placeholder)
    def apply_state(self, state: dict):
        new_x = state.get("x", self.rect.x)
        new_y = state.get("y", self.rect.y)
        self.dx = new_x - self.rect.x
        self.dy = new_y - self.rect.y
        self.rect.x = new_x
        self.rect.y = new_y
        self.hp_current = state.get("hp", self.hp_current)
    def take_damage(self, amount):
        pass  
    def update(self, dt):
        loop = (self.status != 'death')
        self.image = self.animator.get_current_frame(dt, self.status, loop=loop)
