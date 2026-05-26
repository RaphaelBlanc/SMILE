import pygame
import os
from config import ROOT_DIR

class SoundManager:
    def __init__(self):
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        
        self.global_volume = 1.0 
        
        self.sounds = {}
        self.music_base_volume = 0.1
        self._music_path = os.path.join(ROOT_DIR, "assets/audio/background_music.mp3")
        
        self.load_sound("jump",         os.path.join(ROOT_DIR, "assets/audio/boing.wav"),        volume=0.2)
        self.load_sound("dash",         os.path.join(ROOT_DIR, "assets/audio/dash.mp3"),         volume=0.3)
        self.load_sound("fireball",     os.path.join(ROOT_DIR, "assets/audio/fireball.mp3"),     volume=0.2)
        self.load_sound("chien_detect", os.path.join(ROOT_DIR, "assets/audio/chien_detect.mp3"), volume=0.2)
        self.load_sound("chien_attack", os.path.join(ROOT_DIR, "assets/audio/chien_attack.mp3"), volume=0.1)
        self.load_sound("chien_death",  os.path.join(ROOT_DIR, "assets/audio/chien_death.mp3"),  volume=0.6)

        self.music_intro_path = os.path.join(ROOT_DIR, "assets/audio/smile_fire_intro.mp3")
        self.music_boucle_path = os.path.join(ROOT_DIR, "assets/audio/smile_fire_boucle.mp3")

        try:
            pygame.mixer.music.load(self.music_intro_path)
            pygame.mixer.music.queue(self.music_boucle_path, loops=-1)
            pygame.mixer.music.set_volume(self.music_base_volume * self.global_volume)
            self.music_intro_done = False
        except pygame.error as e:
            print(f"Erreur musique : {e}")

    def update(self):
        pass

    def start_music(self):
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(self.music_intro_path)
            pygame.mixer.music.queue(self.music_boucle_path)   # ← pas de loops=-1 ici
            pygame.mixer.music.set_volume(self.music_base_volume * self.global_volume)
            pygame.mixer.music.play()
            pygame.mixer.music.set_endevent(pygame.USEREVENT + 1)
            self._loop_event = pygame.USEREVENT + 1
        except pygame.error as e:
            print(f"Erreur musique : {e}")

    def load_sound(self, name, path, volume=0.5):
        try:
            sound = pygame.mixer.Sound(path)
            sound.set_volume(volume * self.global_volume)
            self.sounds[name] = {
                "sound": sound,
                "base_volume": volume
            }
        except FileNotFoundError:
            print(f"Attention : Le fichier son '{path}' est introuvable.")
            self.sounds[name] = None

    def play(self, name):
        sound_data = self.sounds.get(name)
        if sound_data and sound_data["sound"]:
            sound_data["sound"].play()

    def set_volume(self, volume):
        self.global_volume = volume
        pygame.mixer.music.set_volume(self.music_base_volume * self.global_volume)
    
        for name, sound_data in self.sounds.items():
            if sound_data and sound_data["sound"]:
                sound_data["sound"].set_volume(sound_data["base_volume"] * self.global_volume)
