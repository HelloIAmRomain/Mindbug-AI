from typing import Any, Dict
from mindbug_engine.managers.effects.base import EffectAction
# AJOUT de l'import pour les logs
from mindbug_engine.utils.logger import log_info


class DiscardAction(EffectAction):
    def __init__(self, turn_manager):
        self.tm = turn_manager

    def execute(self, target: Any, params: Dict, source: Any, owner: Any, opponent: Any):
        # On identifie le propriétaire de la carte (généralement l'adversaire de celui qui joue l'effet)
        # target est l'objet Card à défausser
        from mindbug_engine.core.models import Player

        # On cherche à qui appartient la main contenant la cible
        card_owner = opponent if target in opponent.hand else owner

        if target in card_owner.hand:
            card_owner.hand.remove(target)
            card_owner.discard.append(target)

            log_info(f"   -> 🗑️ {card_owner.name} discards {target.name}")

            # Règle Mindbug : piocher pour compléter la main après une défausse forcée
            # C'est ce qui rend l'effet "invisible" si on ne loggue pas l'action avant
            self.tm.refill_hand(card_owner)