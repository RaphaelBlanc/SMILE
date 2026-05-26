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
    WIDTH    = 552
    HEIGHT   = 288
    THEME_PROJ   = ICE_BLUE
    THEME_SHOCK  = ICE_BLUE
    THEME_BG_TOP = (2,  8, 20)
    THEME_BG_BOT = (5, 20, 50)
    THEME_FLOOR  = (10, 30, 60)
    THEME_WALL   = (5,  15, 38)
    THEME_PLAT   = (30, 70,130)
    THEME_PBORD  = (80,160,220)

    TUNING = {
        "global_cd":  {1:2000, 2:1500, 3:1200},
        "windup":     {"punch": 800, "kick_wave": 1000, "laser_beam": 1200, "massive_smash": 1500},
        "cooldown":   {"punch": 1500, "kick_wave": 2000, "laser_beam": 3000, "massive_smash": 3000},
    }

    def __init__(self, pos, obstacles, floor_y):
        super().__init__(pos, obstacles, floor_y)
        self.HP_MAX = 1900
        self.hp = 1900
        self.phase = 1
        
        self.anim_idx = 0
        self.anim_timer = 0
        self.current_anim_key = "idle"
        self.animations = {}
        self._load_sprites()
        self.image = self.animations["idle"][0]
        self.rect = self.image.get_rect(topleft=pos)
        
        self._laser_placed = False

    def _load_sprites(self):
        import os
        base_path = './assets/images/monstre/boss_glace'
        
        def load_seq(folder_name, prefix):
            frames = []
            dir_path = os.path.join(base_path, folder_name)
            
            actual_dir = dir_path
            if os.path.exists(os.path.join(dir_path, folder_name)):
                actual_dir = os.path.join(dir_path, folder_name)
                
            if not os.path.exists(actual_dir):
                s = pygame.Surface((552, 288), pygame.SRCALPHA)
                return [s]
                
            files = [f for f in os.listdir(actual_dir) if f.endswith('.png')]
            for i in range(1, len(files) + 1):
                path = os.path.join(actual_dir, f"{prefix}_{i}.png")
                if os.path.exists(path):
                    try:
                        surf = pygame.image.load(path).convert_alpha()
                        cropped = pygame.Surface((184, 96), pygame.SRCALPHA)
                        cropped.blit(surf, (0, 0), (3, 17, 184, 96))
                        cropped = pygame.transform.scale(cropped, (552, 288))
                        frames.append(cropped)
                    except Exception:
                        pass
            if not frames:
                s = pygame.Surface((552, 288), pygame.SRCALPHA)
                return [s]
            return frames

        self.animations["idle"] = load_seq("idle", "idle")
        self.animations["walk"] = load_seq("walk", "walk")
        atk = load_seq("1_atk", "1_atk")
        self.animations["punch"] = atk
        self.animations["kick_wave"] = atk
        self.animations["laser_beam"] = atk
        self.animations["massive_smash"] = atk

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
            return # Shielded during laser
        super().take_damage(amount)

    def _get_attack_pool(self):
        pool = ["punch", "massive_smash"]
        if self.phase >= 2:
            pool.append("kick_wave")
        if self.phase >= 3:
            pool.append("laser_beam")
        return pool

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
        elif n == "kick_wave":
            self._dir = 1 if pr.centerx > self.rect.centerx else -1
            self.facing_right = self._dir == 1
            self.exec_timer = 500
        elif n == "punch":
            self._dir = 1 if pr.centerx > self.rect.centerx else -1
            self.facing_right = self._dir == 1
            self.exec_timer = 400
        elif n == "massive_smash":
            self.exec_timer = 600

    def _exec_attack(self, dt_ms, pr):
        n = self.attack_name
        if n == "punch":
            self._ex_punch(dt_ms)
        elif n == "kick_wave":
            self._ex_kick(dt_ms)
        elif n == "laser_beam":
            self._ex_laser(dt_ms)
        elif n == "massive_smash":
            self._ex_massive(dt_ms)

    def _ex_punch(self, dt_ms):
        if self.exec_timer == 400:
            cx = self.rect.right + 20 if self.facing_right else self.rect.left - 20
            p = BossProjectile((cx, self.rect.centery), self._dir * 20, 0, radius=40, color=ICE_BLUE, max_lifetime=150)
            self.projectiles.add(p)
            
        self.exec_timer -= dt_ms
        if self.exec_timer <= 0:
            self._end_attack()

    def _ex_kick(self, dt_ms):
        if self.exec_timer == 500:
            cx = self.rect.right + 10 if self.facing_right else self.rect.left - 10
            # A projectile that travels along the floor
            p = BossProjectile((cx, self.floor_y - 20), self._dir * 12, 0, radius=30, color=ICE_BLUE, max_lifetime=2000)
            p.freezes_player = True  # Custom flag for freezing effect
            # Make it look like a wave
            import pygame
            pygame.draw.polygon(p.image, (255,255,255), [(30, 60), (0, 0), (60, 0)])
            self.projectiles.add(p)
            
        self.exec_timer -= dt_ms
        if self.exec_timer <= 0:
            self._end_attack()
            
    def _ex_massive(self, dt_ms):
        if self.exec_timer == 600:
            # Huge shockwave
            sw1 = ShockWave(self.rect.centerx, self.floor_y, spread_speed=25, wave_height=120, color=ICE_BLUE)
            self.shockwaves.add(sw1)
            self._screen_shake_flag = True
            self._emit_dust(50, [ICE_BLUE, WHITE])
            
        self.exec_timer -= dt_ms
        if self.exec_timer <= 0:
            self._end_attack()

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
            
        # If animation state changed, reset the index to prevent IndexError!
        if self.current_anim_key != anim_key:
            self.current_anim_key = anim_key
            self.anim_idx = 0
            self.anim_timer = 0
            
        frames = self.animations[anim_key]
        
        # Safe bound check just in case
        if self.anim_idx >= len(frames):
            self.anim_idx = 0
            
        # Slower animation for better readability
        fps = 10
        if anim_key in ["punch", "kick_wave", "laser_beam", "massive_smash"]:
            fps = 15
            
        if self.attack_state == WINDUP:
            # Hold the first frame while charging up! This makes it VERY clear he's about to attack.
            self.anim_idx = 0
        else:
            self.anim_timer += dt_ms
            if self.anim_timer >= 1000 / fps:
                self.anim_timer = 0
                self.anim_idx = (self.anim_idx + 1) % len(frames)
            
        base = frames[self.anim_idx].copy()
        
        if self.attack_name == "laser_beam" and self.attack_state in (WINDUP, EXECUTING):
            import pygame
            pygame.draw.circle(base, (0, 200, 255, 100), (276, 144), 140, 15)
            pygame.draw.circle(base, (255, 255, 255, 150), (276, 144), 130, 5)
            
        # FIXED DIRECTION: flip if facing right (because base asset faces left)
        if self.facing_right:
            import pygame
            base = pygame.transform.flip(base, True, False)
            
        self.image = base

    def _draw_extras(self, screen, ox, oy):
        import math
        import pygame
        
        if self.attack_name == "massive_smash" and self.attack_state == WINDUP:
            pct = 1 - (self.windup_timer / max(1, self._get_windup("massive_smash")))
            r = int(400 * pct) # Huge circle
            if r > 5:
                surf = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                pygame.draw.circle(surf, (0, 150, 255, 80), (r, r), r)
                pygame.draw.circle(surf, (0, 200, 255, 150), (r, r), r, 4)
                screen.blit(surf, (self.rect.centerx - r + ox, self.floor_y - r + oy))
                
        elif self.attack_name == "laser_beam" and self.attack_state == WINDUP:
            # Draw aiming line
            if hasattr(self, '_laser_target'):
                pygame.draw.line(screen, (0, 200, 255, 150), (self.rect.centerx + ox, self.rect.centery + oy), (self._laser_target[0] + ox, self._laser_target[1] + oy), 2)


class GlaciusLaserHazard(pygame.sprite.Sprite):
    def __init__(self, x, y, target_x, target_y, duration=1500):
        super().__init__()
        import pygame
        self.born = pygame.time.get_ticks()
        self.life = duration
        
        # LASER DAMAGE INCREASED FROM 1 TO 5 (applied per frame during collision!)
        self.damage = 5
        
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
        import pygame
        if pygame.time.get_ticks() - self.born > self.life:
            self.kill()

"""

new_content = content[:start_idx] + new_glacius + content[end_idx:]

with open('src/boss.py', 'w') as f:
    f.write(new_content)

print("Glacius boss successfully replaced v6!")
