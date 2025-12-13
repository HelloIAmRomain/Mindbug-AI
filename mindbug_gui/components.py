import pygame
from constants import *

class Button:
    """Bouton simple avec effet de survol."""
    def __init__(self, rect, text, font, action_id, color=COLOR_BTN_NORMAL, hover_color=COLOR_BTN_HOVER):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.action_id = action_id # Chaîne retournée lors du clic (ex: "PLAY")
        self.color = color
        self.hover_color = hover_color

    def draw(self, screen):
        mouse_pos = pygame.mouse.get_pos()
        current_color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.color
        
        # Fond
        pygame.draw.rect(screen, current_color, self.rect, border_radius=12)
        pygame.draw.rect(screen, COLOR_WHITE, self.rect, 2, border_radius=12)
        
        # Texte
        txt_surf = self.font.render(self.text, True, COLOR_WHITE)
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        screen.blit(txt_surf, txt_rect)

    def is_clicked(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False

class Toggle:
    """Interrupteur ON/OFF."""
    def __init__(self, x, y, label, font, initial_value=False):
        self.rect = pygame.Rect(x, y, 60, 30)
        self.label = label
        self.font = font
        self.value = initial_value

    def draw(self, screen):
        # Dessin du label à gauche
        label_surf = self.font.render(self.label, True, COLOR_BLACK)
        screen.blit(label_surf, (self.rect.x - label_surf.get_width() - 20, self.rect.y + 5))
        
        # Couleur dynamique (Vert si ON, Rouge si OFF)
        color = COLOR_BTN_PLAY if self.value else COLOR_BTN_QUIT
        
        # Dessin du switch
        pygame.draw.rect(screen, color, self.rect, border_radius=15)
        pygame.draw.rect(screen, COLOR_BLACK, self.rect, 2, border_radius=15)
        
        # Cercle indicateur (Knob)
        circle_x = self.rect.right - 15 if self.value else self.rect.x + 15
        pygame.draw.circle(screen, COLOR_WHITE, (circle_x, self.rect.centery), 12)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.value = not self.value
                return True
        return False

class CardThumbnail:
    """Miniature de carte pour le sélecteur de deck."""
    def __init__(self, card_data, x, y, w, h, img_cache, is_selected):
        self.rect = pygame.Rect(x, y, w, h)
        self.card = card_data
        # On essaie de récupérer l'image depuis le cache passé en paramètre
        self.image = img_cache.get(card_data.image_path)
        self.is_selected = is_selected

    def draw(self, screen):
        # 1. Image ou Fallback
        if self.image:
            # Note: Idéalement les images sont déjà redimensionnées dans le cache du Menu
            # Mais par sécurité on peut scale ici si nécessaire, ou assumer que le cache est propre.
            # Pour la grille, un smoothscale à chaque frame peut être lourd si beaucoup de cartes.
            # On assume ici que self.image est déjà à la bonne taille ou que Pygame gère bien le blit.
            # Si l'image du cache est grande, on la réduit :
            if self.image.get_width() != self.rect.width:
                scaled = pygame.transform.smoothscale(self.image, (self.rect.width, self.rect.height))
                screen.blit(scaled, self.rect)
            else:
                screen.blit(self.image, self.rect)
        else:
            # Fallback gris
            pygame.draw.rect(screen, (150, 150, 150), self.rect)
            # Petit texte pour le nom
            font = pygame.font.SysFont("Arial", 10)
            txt = font.render(self.card.name[:8], True, COLOR_BLACK)
            screen.blit(txt, (self.rect.x + 2, self.rect.y + 2))

        # 2. Indication de Sélection
        if self.is_selected:
            # Bordure verte épaisse
            pygame.draw.rect(screen, COLOR_BORDER_LEGAL, self.rect, 4)
            # Petit rond de validation
            pygame.draw.circle(screen, COLOR_BORDER_LEGAL, self.rect.bottomright, 8)
        else:
            # Voile gris pour dire "pas sélectionné" (Désactivé / Grisé)
            s = pygame.Surface((self.rect.width, self.rect.height))
            s.set_alpha(100) # Transparence
            s.fill((0,0,0))  # Noir
            screen.blit(s, self.rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.is_selected = not self.is_selected
                return True
        return False
