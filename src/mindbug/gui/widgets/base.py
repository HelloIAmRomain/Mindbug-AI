import pygame

class BaseWidget:
    """
    Classe de base pour tous les éléments graphiques.
    Gère la position (rect), la visibilité et l'état de survol.
    """
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
        self.visible = True
        self.hovered = False
        self.enabled = True

    def update(self, dt, mouse_pos):
        """Met à jour l'état interne (survol, animation)."""
        if not self.visible: return
        
        # Détection simple du survol
        self.hovered = self.rect.collidepoint(mouse_pos)

    def handle_event(self, event):
        """Retourne une action (str) ou None."""
        return None

    def draw(self, surface):
        """À surcharger par les enfants."""
        pass
