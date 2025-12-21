import pygame
from typing import Tuple, Optional, Any, Dict

from mindbug_engine.utils.logger import log_error
# --- CORE & WIDGETS ---
from mindbug_gui.widgets.buttons import UIWidget
from mindbug_gui.core.resource_manager import ResourceManager
from mindbug_engine.core.models import Card
from mindbug_engine.core.consts import Keyword

# --- STYLING ---
from mindbug_gui.core.colors import (
    TEXT_PRIMARY, TEXT_SECONDARY,
    BTN_SURFACE, BTN_BORDER,
    STATUS_OK, STATUS_CRIT, ACCENT,
    HIGHLIGHT_GOLD
)


class CardView(UIWidget):
    """
    Widget représentant une carte.
    Gère l'affichage, les indicateurs d'état et désormais le Drag & Drop.
    """

    def __init__(self, card: Card, x: int, y: int, w: int, h: int, is_hidden: bool = False):
        # Initialisation du parent (UIWidget)
        super().__init__(x, y, w, h, action="CLICK_CARD")

        self.card = card
        self.is_hidden = is_hidden
        self.visible = True

        self.metadata: Dict[str, Any] = {}

        # --- ÉTATS DRAG & DROP (NOUVEAU) ---
        self.is_dragging = False
        self.origin_pos = (x, y)  # Position de retour si le drop échoue
        # Écart souris/coin pour un déplacement fluide
        self.drag_offset = (0, 0)

        # États visuels (Pilotés par GameScreen)
        self.is_highlighted = False  # Coup légal / Jouable
        self.is_attacking = False  # En train d'attaquer
        self.is_selected = False  # Sélectionnée (Zoom ou Cible)

        # Gestion des Ressources
        self.res_manager = ResourceManager()
        self._cached_image = None

        # Préparation des Polices (Optimisation)
        self.font_title = pygame.font.SysFont("Arial", int(h * 0.1), bold=True)
        self.font_kw = pygame.font.SysFont("Arial", int(h * 0.08))
        self.font_power = pygame.font.Font(None, int(w * 0.3))

        # Chargement initial de l'image
        self._refresh_image()

    def _refresh_image(self):
        """Charge et redimensionne l'image une seule fois."""
        try:
            raw_img = self.res_manager.get_card_image(self.card)
            if raw_img:
                self._cached_image = pygame.transform.smoothscale(
                    raw_img, (self.rect.width, self.rect.height))
        except Exception as e:
            log_error(f"⚠️ Erreur chargement image {self.card.name}: {e}")
            self._cached_image = None

    # =========================================================================
    #  LOGIQUE DRAG & DROP
    # =========================================================================

    def start_drag(self, mouse_pos: Tuple[int, int]):
        """Commence le déplacement de la carte."""
        if self.is_hidden:
            # On ne peut pas déplacer une carte cachée (ex: main adverse)
            return

        self.is_dragging = True
        # On sauvegarde la position actuelle pour pouvoir y revenir (snap back)
        self.origin_pos = (self.rect.x, self.rect.y)
        # On calcule le décalage pour que la carte ne "saute" pas au centre de la souris
        self.drag_offset = (
            self.rect.x - mouse_pos[0], self.rect.y - mouse_pos[1])

    def update_drag_position(self, mouse_pos: Tuple[int, int]):
        """Met à jour la position pendant le mouvement."""
        if self.is_dragging:
            new_x = mouse_pos[0] + self.drag_offset[0]
            new_y = mouse_pos[1] + self.drag_offset[1]
            self.rect.topleft = (new_x, new_y)

    def stop_drag(self):
        """Termine le déplacement et remet la carte à sa place d'origine."""
        self.is_dragging = False
        # Retour élastique à la position d'origine (le GameScreen changera cette position si le coup est valide)
        self.rect.topleft = self.origin_pos

    # =========================================================================
    #  MÉTHODES STANDARD UIWIDGET
    # =========================================================================

    def update(self, dt: float, mouse_pos: Tuple[int, int]):
        """Met à jour le survol."""
        if mouse_pos:
            self.is_hovered = self.rect.collidepoint(mouse_pos)
        else:
            self.is_hovered = False

    def handle_event(self, event: pygame.event.Event) -> Optional[Tuple[str, Card]]:
        """
        Gère les clics (Zoom, etc.).
        Note: Le Drag & Drop est géré par le GameScreen, mais on garde le clic droit ici.
        """
        if not self.visible:
            return None

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.is_hovered:
                # Clic Droit : Zoom
                if event.button == 3:
                    return ("ZOOM_CARD", self.card)
                # Clic Gauche : On laisse le GameScreen gérer le Drag via start_drag()

        return None

    def draw(self, surface: pygame.Surface, override_power: Optional[int] = None):
        """Rendu complet de la carte."""
        if not self.visible:
            return

        # --- 1. DOS DE CARTE (Si cachée) ---
        if self.is_hidden:
            self._draw_hidden(surface)
            return

        # --- 2. FACE DE CARTE ---
        if self._cached_image:
            self._draw_image(surface)
        else:
            self._draw_fallback_text(surface)

        # --- 3. BORDURES (Indicateurs d'état) ---
        self._draw_borders(surface)

        # --- 4. BULLE DE PUISSANCE ---
        self._draw_power_bubble(surface, override_power)

    # =========================================================================
    #  MÉTHODES DE DESSIN INTERNES (Helpers)
    # =========================================================================

    def _draw_hidden(self, surface):
        """Dessine le dos de la carte."""
        pygame.draw.rect(surface, BTN_SURFACE, self.rect, border_radius=8)
        pygame.draw.rect(surface, BTN_BORDER, self.rect, 2, border_radius=8)

        cx, cy = self.rect.center
        pygame.draw.circle(surface, (60, 70, 90), (cx, cy), 15)
        pygame.draw.circle(surface, BTN_BORDER, (cx, cy), 15, width=2)

    def _draw_image(self, surface):
        """Affiche l'image mise en cache."""
        surface.blit(self._cached_image, self.rect)

    def _draw_fallback_text(self, surface):
        """Affiche un design généré si l'image manque."""
        pygame.draw.rect(surface, (30, 35, 45), self.rect, border_radius=8)

        name_txt = self.card.name
        if len(name_txt) > 12:
            name_txt = name_txt[:10] + ".."

        txt_surf = self.font_title.render(name_txt, True, TEXT_PRIMARY)
        txt_rect = txt_surf.get_rect(
            midtop=(self.rect.centerx, self.rect.y + 10))
        surface.blit(txt_surf, txt_rect)

        if self.card.keywords:
            kw_list = []
            for k in self.card.keywords:
                val = k.value if hasattr(k, 'value') else str(k)
                kw_list.append(val[0].upper())

            k_str = " ".join(kw_list)
            k_surf = self.font_kw.render(k_str, True, TEXT_SECONDARY)
            k_rect = k_surf.get_rect(midbottom=(
                self.rect.centerx, self.rect.bottom - 25))
            surface.blit(k_surf, k_rect)

    def _draw_borders(self, surface):
        """Dessine la bordure colorée selon l'état."""
        border_col = BTN_BORDER
        width = 1

        if self.is_attacking:
            border_col = STATUS_CRIT
            width = 4
        elif self.is_selected:
            border_col = ACCENT
            width = 3
        elif self.is_highlighted:
            border_col = HIGHLIGHT_GOLD
            width = 3
        elif self.is_hovered:
            border_col = TEXT_PRIMARY
            width = 2

        pygame.draw.rect(surface, border_col, self.rect,
                         width, border_radius=8)

    def _draw_power_bubble(self, surface, override_power):
        """Affiche la puissance dans un cercle en bas à droite."""
        val = override_power if override_power is not None else self.card.power

        txt_color = (20, 20, 20)
        bg_circle = TEXT_PRIMARY

        has_poison = False
        for k in self.card.keywords:
            if "POISON" in str(k).upper():
                has_poison = True
                break

        if has_poison:
            txt_color = STATUS_OK
            bg_circle = (20, 40, 20)
        elif val > self.card.power:
            txt_color = STATUS_OK
        elif val < self.card.power:
            txt_color = STATUS_CRIT

        radius = int(self.rect.width * 0.18)
        cx = self.rect.right - radius - 5
        cy = self.rect.bottom - radius - 5

        pygame.draw.circle(surface, bg_circle, (cx, cy), radius)
        pygame.draw.circle(surface, (0, 0, 0), (cx, cy), radius, width=2)

        val_str = str(val)
        txt_surf = self.font_power.render(val_str, True, txt_color)
        txt_rect = txt_surf.get_rect(center=(cx, cy))
        surface.blit(txt_surf, txt_rect)
