from typing import Any, Dict
from mindbug_engine.managers.effects.base import EffectAction


class DiscardAction(EffectAction):
    def __init__(self, turn_manager):
        self.tm = turn_manager

    def execute(self, target: Any, params: Dict, source: Any, owner: Any, opponent: Any):
        # On récupère l'instance du manager d'effets pour accéder au helper _get_owner
        from mindbug_engine.core.models import Player

        # Dans Mindbug, la défausse cible presque toujours une carte en main
        card_owner = opponent if owner != opponent else owner

        if target in card_owner.hand:
            card_owner.hand.remove(target)
            card_owner.discard.append(target)
            # Règle Mindbug : On complète la main après une défausse si nécessaire
            self.tm.refill_hand(card_owner)