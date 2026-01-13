import pygame
import sys
import cv2

pygame.init()

# fenêtre principale
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("SMILE")

# Couleurs
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
BLUE = (0, 102, 204)
RED = (255, 0, 0)
PURPLE = (127, 0, 255)
# Polices
titre = pygame.font.SysFont("Comic Sans MS", 150)
button_police = pygame.font.SysFont("Comic Sans MS", 35)
sous_titre_police = pygame.font.SysFont("Comic Sans MS", 20)

#différentes images 
smile_image = pygame.image.load("logo_jeu.png")
background_menu = pygame.image.load("background_menu.png")
background_menu = pygame.transform.scale(background_menu, (800,600))
background_jouer = pygame.image.load("télécharger.png")
background_jouer = pygame.transform.scale(background_jouer, (800,600))
#différentes vidéos


def draw_text(text, font, color, surface, x, y):
    text_obj = font.render(text, True, color)
    text_rect = text_obj.get_rect(center=(x, y))
    surface.blit(text_obj, text_rect)

def main_menu():
    while True:
    
        screen.fill(WHITE)
        screen.blit(background_menu, (0,0))
        screen.blit(smile_image, (0,0))
        mx, my = pygame.mouse.get_pos() # Position de la souris

        #rectangles pour les boutons
        button_1 = pygame.Rect(300, 300, 200, 100)
        button_2 = pygame.Rect(300, 450, 200, 100)

        #boutons
        pygame.draw.rect(screen, BLUE, button_1)
        pygame.draw.rect(screen, BLUE, button_2)

        #texte
        draw_text("SMILE", titre, RED, screen, 400, 100)
        draw_text("On sait que ca va vous plaire", button_police, PURPLE,screen,400, 200)
        draw_text("JOUER", button_police, WHITE, screen, 400, 350)
        draw_text("QUITTER", button_police, WHITE, screen, 400, 500)

        #événements
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Clic gauche
                    if button_1.collidepoint((mx, my)):
                        game_loop() # Lancer le jeu
                    if button_2.collidepoint((mx, my)):
                        pygame.quit()
                        sys.exit()

        pygame.display.update()

def game_loop():
    # code du jeu 
    running = True
    while running:
        screen.blit(background_jouer, (0,0))
        #screen.fill(GRAY)
        draw_text("bien répondu...", sous_titre_police, BLACK, screen, 400, 300)
        draw_text("Appuie sur ÉCHAP pour supprimer ton OS", button_police, BLACK, screen, 400, 400)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False # Retourne au menu

        pygame.display.update()

main_menu()