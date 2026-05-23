import pygame

class SoundManager:
    def __init__(self):
        # Initialisation du mélangeur de sons
        pygame.mixer.init()
        
        # Volume général (100% par défaut)
        self.global_volume = 1.0 
        
        # Dictionnaire pour stocker les sons et leur volume d'origine
        self.sounds = {}
        self.music_base_volume = 0.1
        
        # Chargement des effets sonores
        self.load_sound("jump", "assets/audio/boing.wav", volume=0.2)
        self.load_sound("dash", "assets/audio/dash.wav", volume=0.3)
        self.load_sound("fireball", "assets/audio/fireball.wav", volume=0.4)
        
        # Chargement de la musique de fond
        try:
            pygame.mixer.music.load("assets/audio/background_music.mp3")
            pygame.mixer.music.set_volume(self.music_base_volume * self.global_volume)
            pygame.mixer.music.play(-1) # -1 pour jouer en boucle
        except pygame.error:
            print("Musique de fond introuvable.")

    def load_sound(self, name, path, volume=0.5):
        """Charge un son avec sécurité si le fichier est manquant"""
        try:
            sound = pygame.mixer.Sound(path)
            # Applique le volume en prenant en compte le volume global
            sound.set_volume(volume * self.global_volume)
            
            # On stocke le son ET son volume de base
            self.sounds[name] = {
                "sound": sound,
                "base_volume": volume
            }
        except FileNotFoundError:
            print(f"Attention : Le fichier son '{path}' est introuvable.")
            self.sounds[name] = None

    def play(self, name):
        """Joue un son par son nom"""
        sound_data = self.sounds.get(name)
        # On vérifie que la donnée existe et que le son a bien été chargé
        if sound_data and sound_data["sound"]:
            sound_data["sound"].play()

    def set_volume(self, volume):
        """Met à jour le volume global (musique + effets sonores)"""
        self.global_volume = volume
        
        # Mise à jour de la musique
        pygame.mixer.music.set_volume(self.music_base_volume * self.global_volume)
        
        # Mise à jour de tous les bruitages en respectant leur mixage d'origine
        for name, sound_data in self.sounds.items():
            if sound_data and sound_data["sound"]:
                nouveau_volume = sound_data["base_volume"] * self.global_volume
                sound_data["sound"].set_volume(nouveau_volume)