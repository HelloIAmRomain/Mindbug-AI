from typing import Any, Dict
from mindbug_engine.managers.effects.base import EffectAction


class MoveAction(EffectAction):
    def execute(self, target: Any, params: Dict, source: Any, owner: Any, opponent: Any):
        dest = params.get("destination")

        if dest == "HAND":
            # On cherche la carte dans les défausses
            for p in [owner, opponent]:
                if target in p.discard:
                    p.discard.remove(target)
                    target.reset()  # La carte redevient "neuve" en retournant en main
                    p.hand.append(target)
                    break