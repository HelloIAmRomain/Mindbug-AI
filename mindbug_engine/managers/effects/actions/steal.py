from typing import Any, Dict
from mindbug_engine.managers.effects.base import EffectAction
from mindbug_engine.core.models import Card
from mindbug_engine.utils.logger import log_info

class StealAction(EffectAction):
    def __init__(self, effect_manager):
        self.em = effect_manager

    def execute(self, target: Any, params: Dict, source: Any, owner: Any, opponent: Any):
        # Le voleur est celui qui a déclenché l'effet (owner)
        thief = owner
        victim = self.em._get_owner(target)

        if not victim or thief == victim:
            return 

        # Cas 1 : Vol sur le plateau (Board)
        if target in victim.board:
            victim.board.remove(target)
            thief.board.append(target)
            log_info(f"   -> {thief.name} vole {target.name} (Plateau)")

        # Cas 2 : Vol dans la main (Hand)
        elif target in victim.hand:
            victim.hand.remove(target)
            thief.hand.append(target)
            # On demande au TurnManager de compléter la main de la victime si besoin
            self.em.turn_manager.refill_hand(victim)
            log_info(f"   -> {thief.name} vole une carte dans la main")
