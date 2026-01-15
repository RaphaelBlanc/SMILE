# Fichier : animator.py
import pygame

class Animator:
    def __init__(self, animations_dict, fps=8):
        self.animations = animations_dict
        self.fps = fps
        self.animation_speed = 1.0 / fps
        self.timer = 0
        self.frame_index = 0
        self.current_state = "idle"

    def get_current_frame(self, dt, state, loop=True):
        # 1. On vérifie si l'état existe et n'est pas vide
        if state not in self.animations or len(self.animations[state]) == 0:
            # On essaie de se rabattre sur 'idle_right' si l'état actuel pose problème
            state = 'idle_right'
            # Si même 'idle_right' est vide, on renvoie une surface vide pour éviter le crash
            if state not in self.animations or len(self.animations[state]) == 0:
                return pygame.Surface((32, 64))

        if state != self.current_state:
            self.current_state = state
            self.frame_index = 0
            self.timer = 0

        self.timer += dt
        if self.timer >= self.animation_speed:
            self.timer = 0
        
            # 2. Sécurité anti-division par zéro
            num_frames = len(self.animations[self.current_state])
            if num_frames > 0:
                if loop:
                    self.frame_index = (self.frame_index + 1) % num_frames
                else:
                    if self.frame_index < num_frames - 1:
                        self.frame_index += 1
    
        return self.animations[self.current_state][int(self.frame_index)]