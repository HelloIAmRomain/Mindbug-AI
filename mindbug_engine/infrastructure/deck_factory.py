import random
from typing import List, Optional, Tuple, Dict
from mindbug_engine.core.models import Card
from mindbug_engine.infrastructure.card_loader import CardLoader
from mindbug_engine.utils.logger import log_info, log_error


class DeckFactory:
    """
    Service responsable de la création du deck de jeu.
    """

    def __init__(self, deck_path: str):
        self.deck_path = deck_path
        self.all_cards_pool = CardLoader.load_from_json(self.deck_path)

    def create_deck(self,
                    active_sets: Optional[List[str]] = None,
                    active_card_ids: Optional[List[str]] = None) -> Tuple[List[Card], List[Card], List[str]]:

        # 1. Identification des sets disponibles
        available_sets_map: Dict[str, str] = {}
        for c in self.all_cards_pool:
            if c.set:
                norm = c.set.upper().replace(" ", "_")
                if norm not in available_sets_map:
                    available_sets_map[norm] = c.set

        # 2. Détermination des sets actifs
        used_sets_norm = []
        if active_sets:
            used_sets_norm = [s.upper().replace(" ", "_") for s in active_sets]
        else:
            if available_sets_map:
                first_key = sorted(available_sets_map.keys())[0]
                used_sets_norm = [first_key]

        # 3. Filtrage
        candidates = []
        if used_sets_norm:
            for c in self.all_cards_pool:
                c_set_norm = c.set.upper().replace(" ", "_") if c.set else "NO_SET"
                if c_set_norm in used_sets_norm:
                    candidates.append(c)
        else:
            candidates = list(self.all_cards_pool)

        # Filtre ID (Mode Debug/Test)
        if active_card_ids:
            candidates = [
                c for c in self.all_cards_pool if c.id in active_card_ids]

        # 4. Validation & Coupe
        # On a besoin de 22 cartes (20 jeu + 2 décision start)
        REQUIRED_CARDS = 22

        if len(candidates) < REQUIRED_CARDS:
            # Fallback pour les tests ou petits sets : on prend tout ce qu'il y a
            log_error(
                f"DeckFactory : Pas assez de cartes ({len(candidates)}) pour la règle standard (22 requises).")
            return list(candidates), list(candidates), used_sets_norm

        game_deck = []
        if len(candidates) > REQUIRED_CARDS:
            game_deck = random.sample(candidates, REQUIRED_CARDS)
        else:
            game_deck = list(candidates)

        return game_deck, candidates, used_sets_norm
