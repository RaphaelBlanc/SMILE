import pygame

class SoundManager:
    def __init__(self):
        # Initialisation du mélangeur de sons
        pygame.mixer.init()
        
        # Dictionnaire pour stocker les sons
        self.sounds = {}
        
        # Chargement des effets sonores
        self.load_sound("jump", "assets/boing.wav", volume=0.2)
        self.load_sound("dash", "assets/dash.wav", volume=0.3)
        self.load_sound("fireball", "assets/fireball.wav", volume=0.4)
        
        # Chargement de la musique de fond
        try:
            pygame.mixer.music.load("assets/background_music.mp3")
            pygame.mixer.music.set_volume(0.1)
            pygame.mixer.music.play(-1) # -1 pour jouer en boucle
        except pygame.error:
            print("Musique de fond introuvable.")

    def load_sound(self, name, path, volume=0.5):
        """Charge un son avec sécurité si le fichier est manquant"""
        try:
            sound = pygame.mixer.Sound(path)
            sound.set_volume(volume)
            self.sounds[name] = sound
        except FileNotFoundError:
            print(f"Attention : Le fichier son '{path}' est introuvable.")
            self.sounds[name] = None

    def play(self, name):
        """Joue un son par son nom"""
        sound = self.sounds.get(name)
        if sound:
            sound.play()