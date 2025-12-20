import random
import copy
from typing import List
from mindbug_engine.core.models import Card
from mindbug_engine.core.consts import CardStatus
from mindbug_engine.managers.settings_manager import SettingsManager
from mindbug_engine.utils.logger import log_info, log_error


class GameBuilder:
    """
    Responsable de la construction du Deck de jeu (20 cartes)
    en fonction des filtres (Sets) et des préférences (Selected/Banned).
    """

    def __init__(self, settings_manager: SettingsManager, all_available_cards: List[Card]):
        self.settings = settings_manager
        # 'all_available_cards' est la liste brute chargée par DeckFactory.
        # Elle contient TOUTES les instances (ex: 2 instances de Kangousaurus Rex).
        self.pool = all_available_cards
        self.DECK_SIZE = 20

    def build_deck(self) -> List[Card]:
        final_pool = []

        # 1. Filtrage par Sets actifs
        active_sets_cards = [c for c in self.pool if c.set in self.settings.active_sets]

        # 2. Groupement par ID pour gérer les exemplaires
        unique_defs = {}
        for c in active_sets_cards:
            if c.id not in unique_defs:
                unique_defs[c.id] = c

        # 3. Application des quotas configurés
        for card_id, card_def in unique_defs.items():
            count = self.settings.get_card_copies(card_id)
            for _ in range(count):
                final_pool.append(card_def)

        # 4. Ajustement à la taille du Deck (20)
        if len(final_pool) > self.DECK_SIZE:
            # Trop de cartes : sélection aléatoire parmi le pool autorisé
            final_pool = random.sample(final_pool, self.DECK_SIZE)
        elif len(final_pool) < self.DECK_SIZE and not self.settings.debug_mode:
            # Pas assez : erreur sauf si debug
            raise ValueError(f"Pas assez de cartes ({len(final_pool)}/{self.DECK_SIZE})")

        random.shuffle(final_pool)
        return copy.deepcopy(final_pool)