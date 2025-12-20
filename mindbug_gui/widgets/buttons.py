import pygame
from abc import ABC, abstractmethod
from typing import Optional, Tuple, Any

from mindbug_gui.core.colors import (
    BTN_SURFACE, BTN_HOVER, BTN_BORDER,
    TEXT_PRIMARY, STATUS_OK, BG_COLOR
)


class UIWidget(ABC):
    """
    Classe de base abstraite pour tous les éléments interactifs.
    Garantit que chaque widget respecte le contrat d'interface.
    """

    def __init__(self, x: int, y: int, width: int, height: int, action: Optional[str] = None):
        self.rect = pygame.Rect(x, y, width, height)
        self.action = action  # L'identifiant renvoyé lors d'une interaction (ex: "PLAY")
        self.is_hovered = False

    @abstractmethod
    def update(self, dt: float, mouse_pos: Tuple[int, int]):
        """Met à jour l'état interne (survol, animation)."""
        pass

    @abstractmethod
    def draw(self, surface: pygame.Surface):
        """Dessine le widget sur la surface donnée."""
        pass

    @abstractmethod
    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        """Gère les entrées. Retourne self.action si déclenché, sinon None."""
        pass


class Button(UIWidget):
    """
    Bouton rectangulaire standard avec texte et gestion de survol.
    """

    def __init__(self,
                 x: int, y: int, width: int, height: int,
                 text: str,
                 font: pygame.font.Font,
                 action: str,
                 bg_color: Tuple[int, int, int] = BTN_SURFACE,
                 text_color: Tuple[int, int, int] = TEXT_PRIMARY,
                 hover_color: Tuple[int, int, int] = BTN_HOVER):

        super().__init__(x, y, width, height, action)
        self.text = text
        self.font = font

        # Style
        self.bg_color = bg_color
        self.text_color = text_color
        self.hover_color = hover_color
        self.border_radius = 8

    def update(self, dt: float, mouse_pos: Tuple[int, int]):
        if mouse_pos:
            self.is_hovered = self.rect.collidepoint(mouse_pos)
        else:
            self.is_hovered = False

    def draw(self, surface: pygame.Surface):
        # 1. Couleur de fond dynamique
        color = self.hover_color if self.is_hovered else self.bg_color
        pygame.draw.rect(surface, color, self.rect, border_radius=self.border_radius)

        # 2. Bordure (blanche si survolée, sinon standard)
        border_col = (255, 255, 255) if self.is_hovered else BTN_BORDER
        pygame.draw.rect(surface, border_col, self.rect, 2, border_radius=self.border_radius)

        # 3. Texte centré
        if self.text:
            txt_surf = self.font.render(self.text, True, self.text_color)
            txt_rect = txt_surf.get_rect(center=self.rect.center)
            surface.blit(txt_surf, txt_rect)

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                return self.action
        return None


class Toggle(UIWidget):
    """
    Switch ON/OFF (Checkbox stylisée).
    """

    def __init__(self,
                 cx: int, y: int,
                 label_text: str,
                 font: pygame.font.Font,
                 initial_value: bool = False,
                 action: Optional[str] = None):

        # Dimensions fixes pour le toggle
        w, h = 60, 30
        # On centre le rect sur cx
        super().__init__(cx - w // 2, y, w, h, action)

        self.label_text = label_text
        self.font = font
        self.value = initial_value

    def update(self, dt: float, mouse_pos: Tuple[int, int]):
        self.is_hovered = self.rect.collidepoint(mouse_pos)

    def draw(self, surface: pygame.Surface):
        # 1. Label à gauche du toggle
        if self.label_text:
            label_surf = self.font.render(self.label_text, True, TEXT_PRIMARY)
            # Positionné à gauche avec une marge de 20px
            label_rect = label_surf.get_rect(midright=(self.rect.left - 20, self.rect.centery))
            surface.blit(label_surf, label_rect)

        # 2. Fond du switch (Vert si ON, Gris si OFF)
        bg_color = STATUS_OK if self.value else BTN_SURFACE
        pygame.draw.rect(surface, bg_color, self.rect, border_radius=15)

        # 3. Bordure
        border_col = (255, 255, 255) if self.is_hovered else BTN_BORDER
        pygame.draw.rect(surface, border_col, self.rect, 2, border_radius=15)

        # 4. Curseur (Rond)
        # Si ON -> à droite, Si OFF -> à gauche
        circle_x = self.rect.right - 15 if self.value else self.rect.left + 15
        cursor_col = (255, 255, 255) if self.is_hovered else BTN_BORDER
        pygame.draw.circle(surface, cursor_col, (circle_x, self.rect.centery), 11)

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                self.value = not self.value
                return self.action  # Peut retourner None si c'est juste visuel
        return None