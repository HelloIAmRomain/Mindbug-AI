import pygame
from typing import Tuple, Optional

# --- CORE & WIDGETS ---
from mindbug_gui.widgets.buttons import UIWidget
from mindbug_gui.core.resource_manager import ResourceManager
from mindbug_engine.core.models import Card
from mindbug_engine.core.consts import Keyword

# --- STYLING ---
from mindbug_gui.core.colors import (
    TEXT_PRIMARY, TEXT_SECONDARY,
    BTN_SURFACE, BTN_BORDER,
    STATUS_OK, STATUS_WARN, STATUS_CRIT, ACCENT,
    HIGHLIGHT_GOLD
)


class CardView(UIWidget):
    """
    Widget représentant une carte.
    Gère l'affichage (Image ou Fallback Texte), le dos de carte,
    et les indicateurs d'état (Attaque, Sélection, Puissance).
    """

    def __init__(self, card: Card, x: int, y: int, w: int, h: int, is_hidden: bool = False):
        # Initialisation du parent (UIWidget)
        super().__init__(x, y, w, h, action="CLICK_CARD")

        self.card = card
        self.is_hidden = is_hidden
        self.visible = True

        # États visuels (Pilotés par GameScreen)
        self.is_highlighted = False  # Coup légal / Jouable
        self.is_attacking = False  # En train d'attaquer
        self.is_selected = False  # Sélectionnée (Zoom ou Cible)

        # Gestion des Ressources
        self.res_manager = ResourceManager()
        self._cached_image = None

        # Préparation des Polices (Optimisation : instanciées une seule fois)
        self.font_title = pygame.font.SysFont("Arial", int(h * 0.1), bold=True)
        self.font_kw = pygame.font.SysFont("Arial", int(h * 0.08))

        # Font pour la bulle de puissance (approx 30% de la largeur)
        self.font_power = pygame.font.Font(None, int(w * 0.3))

        # Chargement initial de l'image
        self._refresh_image()

    def _refresh_image(self):
        """Charge et redimensionne l'image une seule fois."""
        try:
            raw_img = self.res_manager.get_card_image(self.card)
            if raw_img:
                self._cached_image = pygame.transform.smoothscale(raw_img, (self.rect.width, self.rect.height))
        except Exception as e:
            print(f"⚠️ Erreur chargement image {self.card.name}: {e}")
            self._cached_image = None

    def update(self, dt: float, mouse_pos: Tuple[int, int]):
        """Met à jour le survol."""
        if mouse_pos:
            self.is_hovered = self.rect.collidepoint(mouse_pos)
        else:
            self.is_hovered = False

    def handle_event(self, event: pygame.event.Event) -> Optional[Tuple[str, Card]]:
        """
        Gère les clics.
        Retourne un tuple (TYPE_EVENT, CARD_OBJ) pour que le GameScreen sache quoi faire.
        """
        if not self.visible: return None

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.is_hovered:
                # Clic Gauche : Interaction Jeu
                if event.button == 1:
                    return ("CLICK_CARD", self.card)
                # Clic Droit : Zoom
                elif event.button == 3:
                    return ("ZOOM_CARD", self.card)
        return None

    def draw(self, surface: pygame.Surface, override_power: Optional[int] = None):
        """Rendu complet de la carte."""
        if not self.visible: return

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

        # Décoration simple (Cercle central)
        cx, cy = self.rect.center
        pygame.draw.circle(surface, (60, 70, 90), (cx, cy), 15)
        pygame.draw.circle(surface, BTN_BORDER, (cx, cy), 15, width=2)

    def _draw_image(self, surface):
        """Affiche l'image mise en cache."""
        surface.blit(self._cached_image, self.rect)

    def _draw_fallback_text(self, surface):
        """Affiche un design généré si l'image manque."""
        # Fond sombre
        pygame.draw.rect(surface, (30, 35, 45), self.rect, border_radius=8)

        # Nom de la carte (Troncation si > 12 chars)
        name_txt = self.card.name
        if len(name_txt) > 12: name_txt = name_txt[:10] + ".."

        txt_surf = self.font_title.render(name_txt, True, TEXT_PRIMARY)
        # Centré en haut avec une marge
        txt_rect = txt_surf.get_rect(midtop=(self.rect.centerx, self.rect.y + 10))
        surface.blit(txt_surf, txt_rect)

        # Mots-clés en bas
        if self.card.keywords:
            # On prend la première lettre (ex: P, F, H)
            kw_list = []
            for k in self.card.keywords:
                # Gestion robuste (Enum vs String)
                val = k.value if hasattr(k, 'value') else str(k)
                kw_list.append(val[0].upper())

            k_str = " ".join(kw_list)
            k_surf = self.font_kw.render(k_str, True, TEXT_SECONDARY)
            k_rect = k_surf.get_rect(midbottom=(self.rect.centerx, self.rect.bottom - 25))
            surface.blit(k_surf, k_rect)

    def _draw_borders(self, surface):
        """Dessine la bordure colorée selon l'état."""
        border_col = BTN_BORDER
        width = 1

        # Ordre de priorité des bordures :

        # 1. Attaque (Le plus important, rouge danger)
        if self.is_attacking:
            border_col = STATUS_CRIT
            width = 4

        # 2. Sélectionné (Cible d'un effet ou Zoom)
        elif self.is_selected:
            border_col = ACCENT
            width = 3

        # 3. Surlignage (Coup légal / Jouable) -> C'est ici qu'on change !
        elif self.is_highlighted:
            border_col = HIGHLIGHT_GOLD
            width = 3  # Bordure épaisse pour bien voir que c'est jouable

        # 4. Survol souris (Hover simple)
        elif self.is_hovered:
            border_col = TEXT_PRIMARY
            width = 2

        pygame.draw.rect(surface, border_col, self.rect, width, border_radius=8)

    def _draw_power_bubble(self, surface, override_power):
        """Affiche la puissance dans un cercle en bas à droite."""
        val = override_power if override_power is not None else self.card.power

        # Couleurs contextuelles
        txt_color = (20, 20, 20)  # Noir
        bg_circle = TEXT_PRIMARY  # Blanc

        # Gestion Poison / Buff / Debuff
        has_poison = False
        for k in self.card.keywords:
            k_str = str(k).upper()
            if "POISON" in k_str:
                has_poison = True
                break

        if has_poison:
            txt_color = STATUS_OK  # Vert fluo
            bg_circle = (20, 40, 20)  # Vert sombre
        elif val > self.card.power:
            txt_color = STATUS_OK  # Vert (Buff)
        elif val < self.card.power:
            txt_color = STATUS_CRIT  # Rouge (Debuff)

        # Géométrie
        radius = int(self.rect.width * 0.18)
        cx = self.rect.right - radius - 5
        cy = self.rect.bottom - radius - 5

        # Dessin du cercle
        pygame.draw.circle(surface, bg_circle, (cx, cy), radius)
        pygame.draw.circle(surface, (0, 0, 0), (cx, cy), radius, width=2)

        # Dessin du texte
        val_str = str(val)
        txt_surf = self.font_power.render(val_str, True, txt_color)
        txt_rect = txt_surf.get_rect(center=(cx, cy))
        surface.blit(txt_surf, txt_rect)