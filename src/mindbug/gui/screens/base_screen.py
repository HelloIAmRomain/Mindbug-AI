from typing import List, Optional
import pygame


class BaseScreen:
    """
    Interface commune pour tous les écrans (Menu, Jeu, Options).
    """

    def __init__(self, app):
        self.app = app  # Référence vers MindbugApp (pour changer d'écran)
        self.width = app.screen.get_width()
        self.height = app.screen.get_height()

    def handle_events(self, events: List[pygame.event.Event]) -> Optional[str]:
        """
        Gère les événements (clics, touches).
        Retourne "QUIT" pour fermer l'app, une action string, ou None.
        """
        return None

    def update(self, dt):
        """Mise à jour logique (animations, timers)."""
        pass

    def draw(self, surface):
        """Dessin sur l'écran."""
        pass

    def on_resize(self, w, h):
        """Appelé quand la fenêtre change de taille."""
        self.width = w
        self.height = h
