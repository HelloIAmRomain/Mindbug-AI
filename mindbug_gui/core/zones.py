import pygame
from typing import List, Tuple, Dict, Any, Optional
from mindbug_gui.core import layout_config as layout


class GameZone:
    def __init__(self, zone_id: str, rect: pygame.Rect, layout_mode: str = "HORIZONTAL"):
        self.id = zone_id
        self.rect = rect
        self.layout_mode = layout_mode
        self.cards: List[Any] = []

        # Gestion Drag & Drop
        self.ghost_card: Optional[Any] = None
        self.ignored_card: Optional[Any] = None

    # ... (Les méthodes set_cards, set_ghost, etc. restent identiques) ...
    def set_cards(self, cards: List[Any]):
        self.cards = cards if cards else []

    def set_ghost(self, card):
        self.ghost_card = card

    def clear_ghost(self):
        self.ghost_card = None

    def ignore_card(self, card):
        self.ignored_card = card

    def unignore_cards(self):
        self.ignored_card = None

    def get_card_rects(self) -> List[Tuple[Any, pygame.Rect]]:
        effective_cards = [c for c in self.cards if c != self.ignored_card]
        if self.ghost_card and self.ghost_card not in effective_cards:
            effective_cards.append(self.ghost_card)

        if not effective_cards:
            return []

        card_h = int(self.rect.height * 0.9)
        card_w = int(card_h * layout.CARD_ASPECT_RATIO)
        center_y = self.rect.centery
        start_y = center_y - card_h // 2

        results = []
        count = len(effective_cards)

        if self.layout_mode == "STACK":
            offset = 2
            for i, card in enumerate(effective_cards):
                current_offset = min(i, 5) * offset
                r = pygame.Rect(self.rect.x + current_offset,
                                start_y - current_offset, card_w, card_h)
                results.append((card, r))

        elif self.layout_mode == "HORIZONTAL":
            gap = int(self.rect.width * 0.02)
            total_w = count * card_w + (count - 1) * gap
            if total_w > self.rect.width:
                overlap = (total_w - self.rect.width) // (count -
                                                          1) if count > 1 else 0
                gap -= overlap
                total_w = self.rect.width

            start_x = self.rect.centerx - total_w // 2
            for i, card in enumerate(effective_cards):
                x = start_x + i * (card_w + gap)
                r = pygame.Rect(x, start_y, card_w, card_h)
                results.append((card, r))

        return results

    def get_ghost_rect(self) -> Optional[pygame.Rect]:
        layout = self.get_card_rects()
        for card, rect in layout:
            if card == self.ghost_card:
                return rect
        return None


class ZoneManager:
    @staticmethod
    def create_zones(screen_w: int, screen_h: int) -> Dict[str, GameZone]:
        zones = {}
        zone_h = int(screen_h * 0.22)
        margin_x = int(screen_w * 0.02)

        # Largeur des piles
        pile_w = int(zone_h * layout.CARD_ASPECT_RATIO * 1.2)

        # --- MAINS ---
        playable_w = screen_w - 2 * margin_x
        y_hand_p2 = int(screen_h * layout.P2_HAND_Y_PERCENT) - 10
        zones["HAND_P2"] = GameZone("HAND_P2", pygame.Rect(
            margin_x, y_hand_p2, playable_w, zone_h))

        y_hand_p1 = int(screen_h * layout.P1_HAND_Y_PERCENT)
        zones["HAND_P1"] = GameZone("HAND_P1", pygame.Rect(
            margin_x, y_hand_p1, playable_w, zone_h))

        # --- PLATEAUX & PILES ---
        y_board_p2 = int(screen_h * layout.P2_BOARD_Y_PERCENT)
        y_board_p1 = int(screen_h * layout.P1_BOARD_Y_PERCENT)

        # Calcul de la zone centrale (Board)
        board_x = margin_x + pile_w + 20
        deck_x = screen_w - margin_x - pile_w
        # Espace entre Défausse (G) et Pioche (D)
        board_w = (deck_x - 20) - board_x

        # P2 (Haut)
        zones["DISCARD_P2"] = GameZone("DISCARD_P2", pygame.Rect(
            margin_x, y_board_p2, pile_w, zone_h), "STACK")
        zones["BOARD_P2"] = GameZone("BOARD_P2",   pygame.Rect(
            board_x,  y_board_p2, board_w, zone_h))
        zones["DECK_P2"] = GameZone("DECK_P2",    pygame.Rect(
            deck_x,   y_board_p2, pile_w, zone_h), "STACK")

        # P1 (Bas)
        zones["DISCARD_P1"] = GameZone("DISCARD_P1", pygame.Rect(
            margin_x, y_board_p1, pile_w, zone_h), "STACK")
        zones["BOARD_P1"] = GameZone("BOARD_P1",   pygame.Rect(
            board_x,  y_board_p1, board_w, zone_h))
        zones["DECK_P1"] = GameZone("DECK_P1",    pygame.Rect(
            deck_x,   y_board_p1, pile_w, zone_h), "STACK")

        # --- PLAY AREA ---
        play_y = y_board_p2 + zone_h
        play_h = max(1, y_board_p1 - play_y)
        zones["PLAY_AREA"] = GameZone("PLAY_AREA", pygame.Rect(
            margin_x, play_y, playable_w, play_h))

        return zones
