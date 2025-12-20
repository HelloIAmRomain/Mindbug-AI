import pygame
from typing import List, Tuple, Dict, Any, Optional
from mindbug_gui.core import layout_config as layout


class GameZone:
    """
    Représente une zone logique sur le plateau.
    Gère le layout dynamique avec support de "Ghost Card" (prévisualisation du drop).
    """

    def __init__(self, zone_id: str, rect: pygame.Rect, layout_mode: str = "HORIZONTAL"):
        self.id = zone_id
        self.rect = rect
        self.layout_mode = layout_mode
        self.cards: List[Any] = []

        # --- NOUVEAU : Gestion Drag & Drop ---
        self.ghost_card: Optional[Any] = None  # Carte virtuelle ajoutée (placeholder)
        self.ignored_card: Optional[Any] = None  # Carte réelle masquée (celle qu'on drag)

    def set_cards(self, cards: List[Any]):
        self.cards = cards if cards else []

    def set_ghost(self, card):
        """Définit une carte fantôme qui prend de la place dans le layout."""
        self.ghost_card = card

    def clear_ghost(self):
        """Retire la carte fantôme."""
        self.ghost_card = None

    def ignore_card(self, card):
        """Empêche une carte d'être incluse dans le calcul (ex: carte en main qu'on déplace)."""
        self.ignored_card = card

    def unignore_cards(self):
        self.ignored_card = None

    def get_card_rects(self) -> List[Tuple[Any, pygame.Rect]]:
        """
        Calcule la position de chaque carte, y compris le fantôme.
        """
        # 1. Construction de la liste effective à afficher
        # On prend les cartes réelles, moins celle qu'on drag (ignored)
        effective_cards = [c for c in self.cards if c != self.ignored_card]

        # On ajoute le fantôme s'il est défini (et pas déjà présent par erreur)
        if self.ghost_card and self.ghost_card not in effective_cards:
            # Pour l'instant on l'ajoute à la fin.
            # (Amélioration future : l'insérer à l'index correspondant à la souris)
            effective_cards.append(self.ghost_card)

        if not effective_cards:
            return []

        # 2. Paramètres de dimension
        card_h = int(self.rect.height * 0.9)
        card_w = int(card_h * layout.CARD_ASPECT_RATIO)

        center_y = self.rect.centery
        start_y = center_y - card_h // 2

        results = []
        count = len(effective_cards)

        # 3. Calcul du Layout
        if self.layout_mode == "STACK":
            offset = 2
            for i, card in enumerate(effective_cards):
                current_offset = min(i, 5) * offset
                r = pygame.Rect(self.rect.x + current_offset, start_y - current_offset, card_w, card_h)
                results.append((card, r))

        elif self.layout_mode == "HORIZONTAL":
            gap = int(self.rect.width * 0.02)
            total_w = count * card_w + (count - 1) * gap

            # Gestion du débordement (Overlap)
            if total_w > self.rect.width:
                overlap = (total_w - self.rect.width) // (count - 1) if count > 1 else 0
                gap -= overlap
                total_w = self.rect.width

            start_x = self.rect.centerx - total_w // 2

            for i, card in enumerate(effective_cards):
                x = start_x + i * (card_w + gap)
                r = pygame.Rect(x, start_y, card_w, card_h)
                results.append((card, r))

        return results

    def get_ghost_rect(self) -> Optional[pygame.Rect]:
        """
        Récupère le rect spécifique du fantôme après calcul du layout.
        """
        # On recalcule tout (ou on pourrait cacher le résultat précédent)
        layout = self.get_card_rects()
        for card, rect in layout:
            if card == self.ghost_card:
                return rect
        return None


class ZoneManager:
    # ... (Le reste de la classe reste inchangé, gardez votre méthode create_zones actuelle) ...
    @staticmethod
    def create_zones(screen_w: int, screen_h: int) -> Dict[str, GameZone]:
        zones = {}
        zone_h = int(screen_h * 0.22)
        margin_x = int(screen_w * 0.02)
        playable_w = screen_w - 2 * margin_x

        y_hand_p2 = int(screen_h * layout.P2_HAND_Y_PERCENT) - 10
        zones["HAND_P2"] = GameZone("HAND_P2", pygame.Rect(margin_x, y_hand_p2, playable_w, zone_h))

        y_board_p2 = int(screen_h * layout.P2_BOARD_Y_PERCENT)
        zones["BOARD_P2"] = GameZone("BOARD_P2", pygame.Rect(margin_x, y_board_p2, playable_w, zone_h))

        y_board_p1 = int(screen_h * layout.P1_BOARD_Y_PERCENT)
        zones["BOARD_P1"] = GameZone("BOARD_P1", pygame.Rect(margin_x, y_board_p1, playable_w, zone_h))

        y_hand_p1 = int(screen_h * layout.P1_HAND_Y_PERCENT)
        zones["HAND_P1"] = GameZone("HAND_P1", pygame.Rect(margin_x, y_hand_p1, playable_w, zone_h))

        pile_w = int(zone_h * layout.CARD_ASPECT_RATIO * 1.2)
        zones["DISCARD_P1"] = GameZone("DISCARD_P1", pygame.Rect(margin_x, y_hand_p1 - 20, pile_w, zone_h), "STACK")
        zones["DECK_P1"] = GameZone("DECK_P1",
                                    pygame.Rect(screen_w - margin_x - pile_w, y_hand_p1 - 20, pile_w, zone_h), "STACK")
        zones["DISCARD_P2"] = GameZone("DISCARD_P2", pygame.Rect(margin_x, y_hand_p2, pile_w, zone_h), "STACK")
        zones["DECK_P2"] = GameZone("DECK_P2", pygame.Rect(screen_w - margin_x - pile_w, y_hand_p2, pile_w, zone_h),
                                    "STACK")

        play_y = y_board_p2 + zone_h
        play_h = max(1, y_board_p1 - play_y)
        zones["PLAY_AREA"] = GameZone("PLAY_AREA", pygame.Rect(margin_x, play_y, playable_w, play_h))

        return zones