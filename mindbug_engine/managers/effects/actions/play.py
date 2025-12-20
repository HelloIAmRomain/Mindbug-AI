from typing import Any, Dict
from mindbug_engine.managers.effects.base import EffectAction
from mindbug_engine.core.models import Card
from mindbug_engine.utils.logger import log_info

class PlayAction(EffectAction):
    def __init__(self, game):
        self.game = game

    def execute(self, target: Any, params: Dict, source: Any, owner: Any, opponent: Any):
        if not isinstance(target, Card):
            return

        card_owner = self.game.effect_manager._get_owner(target)

        # On retire la carte de sa zone actuelle (souvent la défausse)
        if target in card_owner.discard:
            card_owner.discard.remove(target)
        
        # On la place sur le plateau de celui qui a activé l'effet
        # put_card_on_board gère automatiquement les triggers ON_PLAY
        self.game.put_card_on_board(owner, target)
        target.reset()
        log_info(f"   -> {target.name} est jouée depuis la défausse")
