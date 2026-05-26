import re

with open('src/boss.py', 'r') as f:
    content = f.read()

start_idx = content.find("class Glacius(BossBase):")
end_idx = content.find("# ══════════════════════════════════════════════════════════════════════════════\n#  BOSS 3 – GRANIT")

if start_idx == -1 or end_idx == -1:
    print("Could not find Glacius bounds!")
    exit(1)

new_glacius = """class Glacius(BossBase):
    NAME     = "GLACIUS"
    HP_MAX   = 1900
    WIDTH    = 256
    HEIGHT   = 256
    THEME_PROJ   = ICE_BLUE
    THEME_SHOCK  = ICE_BLUE
    THEME_BG_TOP = (2,  8, 20)
    THEME_BG_BOT = (5, 20, 50)
    THEME_FLOOR  = (10, 30, 60)
    THEME_WALL   = (5,  15, 38)
    THEME_PLAT   = (30, 70,130)
    THEME_PBORD  = (80,160,220)

    TUNING = {
        "global_cd":  {1:1200, 2:800, 3:600}, # Fast!
        "windup":     {"hammer_smash": 500, "dash_punch": 400, "laser_beam": 800},
        "cooldown":   {"hammer_smash": 800, "dash_punch": 600, "laser_beam": 1200},
    }

    def __init__(self, pos, obstacles, floor_y):
        super().__init__(pos, obstacles, floor_y)
        self.HP_MAX = 1900
        self.hp = 1900
        self.phase = 1
        
        self.anim_idx = 0
        self.anim_timer = 0
        self.animations = {}
        self._load_sprites()
        self.image = self.animations["idle"][0]
        self.rect = self.image.get_rect(topleft=pos)
        
        self._laser_placed = False
        self._dash_hit = False

    def _load_sprites(self):
        try:
            sheet = pygame.image.load('./assets/images/monstre/boss_glace-removebg-preview.png').convert_alpha()
        except Exception as e:
            print("ERROR loading sprite:", e)
            sheet = pygame.Surface((676, 369), pygame.SRCALPHA)
            sheet.fill((255, 0, 255))
        
        def extract_row(row_idx, count=11):
            frames = []
            y1 = int(row_idx * 369 / 6)
            y2 = int((row_idx + 1) * 369 / 6)
            fh = y2 - y1
            
            for i in range(count):
                x1 = int(i * 676 / 11)
                x2 = int((i + 1) * 676 / 11)
                fw = x2 - x1
                
                surf = pygame.Surface((fw, fh), pygame.SRCALPHA)
                surf.blit(sheet, (0, 0), (x1, y1, fw, fh))
                # Scale it up to 256x256
                surf = pygame.transform.scale(surf, (256, 256))
                frames.append(surf)
            return frames
            
        self.animations["idle"] = extract_row(0)
        self.animations["walk"] = extract_row(1)
        self.animations["dash_punch"] = extract_row(2)
        self.animations["hammer_smash"] = extract_row(3)
        self.animations["laser_beam"] = extract_row(5)

    def _update_phase(self):
        if self.hp > 1400:
            new_phase = 1
        elif self.hp > 600:
            new_phase = 2
        else:
            new_phase = 3
            
        if self.phase != new_phase:
            self.phase = new_phase
            self._phase_burst()

    def take_damage(self, amount):
        if self.attack_name == "laser_beam" and self.attack_state in (WINDUP, EXECUTING):
            return # Shielded during laser!
        super().take_damage(amount)

    def _get_attack_pool(self):
        if self.phase == 1:
            return ["hammer_smash"]
        elif self.phase == 2:
            return ["hammer_smash", "dash_punch"]
        else:
            return ["hammer_smash", "dash_punch", "laser_beam"]

    def _get_windup(self, n):   return self.TUNING["windup"].get(n, 900)
    def _get_cooldown(self, n): return self.TUNING["cooldown"].get(n, 1000)
    def _get_global_cd(self):  return self.TUNING["global_cd"][self.phase]

    def _start_attack(self, pr):
        n = self.attack_name
        self.anim_idx = 0
        self.anim_timer = 0
        if n == "laser_beam":
            self._laser_placed = False
            self.exec_timer = 1500
            self._laser_target = (pr.centerx, pr.centery)
        elif n == "dash_punch":
            self._dash_dir = 1 if pr.centerx > self.rect.centerx else -1
            self.facing_right = self._dash_dir == 1
            self.exec_timer = 400
        elif n == "hammer_smash":
            self.exec_timer = 500

    def _exec_attack(self, dt_ms, pr):
        n = self.attack_name
        if n == "hammer_smash":
            self._ex_hammer(dt_ms)
        elif n == "dash_punch":
            self._ex_dash(dt_ms)
        elif n == "laser_beam":
            self._ex_laser(dt_ms)

    def _ex_hammer(self, dt_ms):
        if self.exec_timer == 500:
            sw1 = ShockWave(self.rect.centerx, self.floor_y, spread_speed=18, wave_height=80, color=ICE_BLUE)
            self.shockwaves.add(sw1)
            self._screen_shake_flag = True
            self._emit_dust(30, [ICE_BLUE, WHITE])
            
        self.exec_timer -= dt_ms
        if self.exec_timer <= 0:
            self._end_attack()

    def _ex_dash(self, dt_ms):
        self.vx = self._dash_dir * 30 
        self.exec_timer -= dt_ms
        
        import random
        if random.random() > 0.5:
            self._emit_dust(1, [ICE_BLUE])
            
        if self.exec_timer <= 0 or self._hit_wall:
            self.vx = 0
            self._end_attack()
            cx = self.rect.right + 20 if self.facing_right else self.rect.left - 20
            p = BossProjectile((cx, self.rect.centery), self._dash_dir * 15, 0, radius=30, color=ICE_BLUE, max_lifetime=200)
            self.projectiles.add(p)

    def _ex_laser(self, dt_ms):
        if not self._laser_placed:
            self._laser_placed = True
            laser = GlaciusLaserHazard(self.rect.centerx, self.rect.centery - 20, self._laser_target[0], self._laser_target[1])
            self.hazards.add(laser)
            
        self.exec_timer -= dt_ms
        if self.exec_timer <= 0:
            self._end_attack()

    def _update_visual(self, dt_ms):
        anim_key = "idle"
        
        if self.attack_state == WINDUP or self.attack_state == EXECUTING:
            anim_key = self.attack_name
        elif self.vx != 0:
            anim_key = "walk"
            
        if anim_key not in self.animations:
            anim_key = "idle"
            
        frames = self.animations[anim_key]
        fps = 30 # Increased for fluidity
        
        self.anim_timer += dt_ms
        if self.anim_timer >= 1000 / fps:
            self.anim_timer = 0
            self.anim_idx = (self.anim_idx + 1) % len(frames)
            
        base = frames[self.anim_idx].copy()
        
        if self.attack_name == "laser_beam" and self.attack_state in (WINDUP, EXECUTING):
            pygame.draw.circle(base, (0, 200, 255, 100), (128, 128), 120, 10)
            pygame.draw.circle(base, (255, 255, 255, 150), (128, 128), 110, 4)
            
        if not self.facing_right:
            base = pygame.transform.flip(base, True, False)
            
        self.image = base

    def _draw_extras(self, screen, ox, oy):
        import math
        # Draw highly visible transparent blue damage zones and warnings
        
        if self.attack_name == "hammer_smash" and self.attack_state == WINDUP:
            # Pulsing blue AoE circle warning
            pct = 1 - (self.windup_timer / max(1, self._get_windup("hammer_smash")))
            r = int(240 * pct)
            if r > 5:
                surf = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                pygame.draw.circle(surf, (0, 150, 255, 80), (r, r), r)
                pygame.draw.circle(surf, (0, 200, 255, 150), (r, r), r, 4)
                screen.blit(surf, (self.rect.centerx - r + ox, self.floor_y - r + oy))
                
        elif self.attack_name == "dash_punch" and self.attack_state == WINDUP:
            # Draw blue transparent rectangle indicating dash trajectory
            rect_w = 600
            rect_h = 100
            rect_x = self.rect.centerx + ox if self.facing_right else self.rect.centerx - rect_w + ox
            rect_y = self.rect.bottom - rect_h + oy
            
            alpha = int(80 + 40 * math.sin(pygame.time.get_ticks() / 100.0))
            s = pygame.Surface((rect_w, rect_h), pygame.SRCALPHA)
            s.fill((0, 150, 255, alpha))
            pygame.draw.rect(s, (0, 200, 255, alpha + 50), (0, 0, rect_w, rect_h), 4)
            screen.blit(s, (rect_x, rect_y))


class GlaciusLaserHazard(pygame.sprite.Sprite):
    def __init__(self, x, y, target_x, target_y, duration=1500):
        super().__init__()
        self.born = pygame.time.get_ticks()
        self.life = duration
        
        import math
        dx = target_x - x
        dy = target_y - y
        self.angle = math.atan2(dy, dx)
        self.length = 2500
        
        end_x = x + math.cos(self.angle) * self.length
        end_y = y + math.sin(self.angle) * self.length
        
        min_x = min(x, end_x) - 40
        max_x = max(x, end_x) + 40
        min_y = min(y, end_y) - 40
        max_y = max(y, end_y) + 40
        
        w = int(max_x - min_x)
        h = int(max_y - min_y)
        
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        
        lx1 = x - min_x
        ly1 = y - min_y
        lx2 = end_x - min_x
        ly2 = end_y - min_y
        
        pygame.draw.line(self.image, (0, 100, 255, 80), (lx1, ly1), (lx2, ly2), 80)
        pygame.draw.line(self.image, (0, 150, 255, 120), (lx1, ly1), (lx2, ly2), 60)
        pygame.draw.line(self.image, (0, 200, 255, 180), (lx1, ly1), (lx2, ly2), 30)
        pygame.draw.line(self.image, (255, 255, 255, 255), (lx1, ly1), (lx2, ly2), 10)
        
        self.rect = self.image.get_rect(topleft=(min_x, min_y))
        try:
            self.mask = pygame.mask.from_surface(self.image)
        except Exception:
            pass

    def update(self, obstacles=None):
        if pygame.time.get_ticks() - self.born > self.life:
            self.kill()

"""

new_content = content[:start_idx] + new_glacius + content[end_idx:]

with open('src/boss.py', 'w') as f:
    f.write(new_content)

print("Glacius boss successfully replaced!")
