import pygame
import cv2
import sys
import os
from config import SCREEN_WIDTH, SCREEN_HEIGHT

class IntroVideo:
    def __init__(self, screen, clock, video_path):
        self.screen     = screen
        self.clock      = clock
        self.video_path = video_path
    def play(self):
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            print(f"INTRO : impossible d'ouvrir {self.video_path}, on passe.")
            return
        fps_video = cap.get(cv2.CAP_PROP_FPS) or 30.0
        audio_path = None
        try:
            try:
                from moviepy.editor import VideoFileClip   
            except ImportError:
                from moviepy import VideoFileClip           
            import tempfile
            clip = VideoFileClip(self.video_path)
            if clip.audio is not None:
                tmp = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)
                audio_path = tmp.name
                tmp.close()
                clip.audio.write_audiofile(audio_path, logger=None)
                pygame.mixer.music.stop()
                pygame.mixer.music.load(audio_path)
                pygame.mixer.music.play()
            clip.close()
        except Exception as e:
            print(f"INTRO : audio non disponible ({e})")
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    cap.release()
                    pygame.mixer.music.stop()
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN and event.key in (
                        pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                    running = False
            success, frame = cap.read()
            if not success:
                break
            h_vid, w_vid, _ = frame.shape
            if w_vid > 192 and h_vid > 108:
                margin_x = int(w_vid * 0.05)
                margin_y = int(h_vid * 0.05)
                frame = frame[margin_y:h_vid-margin_y, margin_x:w_vid-margin_x]
            frame = cv2.resize(frame, (SCREEN_WIDTH, SCREEN_HEIGHT))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = frame.transpose(1, 0, 2)
            surf  = pygame.surfarray.make_surface(frame)
            self.screen.blit(surf, (0, 0))
            hint_font = pygame.font.SysFont("consolas", 22)
            hint      = hint_font.render("ESPACE  pour passer", True, (200, 200, 200))
            self.screen.blit(hint, (SCREEN_WIDTH - hint.get_width() - 24,
                                    SCREEN_HEIGHT - hint.get_height() - 16))
            pygame.display.flip()
            self.clock.tick(fps_video)
        cap.release()
        pygame.mixer.music.stop()
        fade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        fade.fill((0, 0, 0))
        last_surf = surf if 'surf' in locals() else fade
        for alpha in range(0, 256, 5):
            self.screen.blit(last_surf, (0, 0))
            fade.set_alpha(alpha)
            self.screen.blit(fade, (0, 0))
            pygame.display.flip()
            pygame.time.delay(16)
        self.screen.fill((0, 0, 0))
        pygame.display.flip()
        pygame.time.delay(200)
        if audio_path:
            try:
                import os as _os
                _os.remove(audio_path)
            except Exception:
                pass
