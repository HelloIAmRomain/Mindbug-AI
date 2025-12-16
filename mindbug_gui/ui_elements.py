import pygame

class Button:
    """
    Une classe simple pour gérer les boutons rectangulaires avec texte et survol.
    """
    def __init__(self, rect, text, font, bg_color, text_color, hover_color, action=None):
        self.rect = rect
        self.text = text
        self.font = font
        self.base_color = bg_color
        self.text_color = text_color
        self.hover_color = hover_color
        self.action = action # L'identifiant de l'action (ex: "MENU", "QUIT")
        
        # On garde la couleur actuelle (utile si on veut changer la couleur dynamiquement)
        self.bg_color = self.base_color

    def draw(self, surface, mouse_pos):
        """Dessine le bouton et change la couleur si la souris est dessus."""
        # Détection survol
        current_color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.bg_color
        
        # Fond
        pygame.draw.rect(surface, current_color, self.rect, border_radius=8)
        
        # Bordure (Esthétique)
        pygame.draw.rect(surface, (200, 200, 200), self.rect, 2, border_radius=8)

        # Texte Centré
        if self.text:
            txt_surf = self.font.render(self.text, True, self.text_color)
            txt_rect = txt_surf.get_rect(center=self.rect.center)
            surface.blit(txt_surf, txt_rect)

    def is_hovered(self, pos):
        """Retourne True si la position (x,y) est dans le bouton."""
        return self.rect.collidepoint(pos)
