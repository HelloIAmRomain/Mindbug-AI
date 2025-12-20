from typing import Any, Dict
from mindbug_engine.managers.effects.base import EffectAction


class MoveAction(EffectAction):
    def execute(self, target: Any, params: Dict, source: Any, owner: Any, opponent: Any):
        dest = params.get("destination")

        # On suppose que target est l'objet Card et qu'on connaît sa zone actuelle
        # Pour Giraffodile : Discard -> Hand
        if dest == "HAND":
            # On cherche dans quelle défausse se trouve la carte
            for p in [owner, opponent]:
                if target in p.discard:
                    p.discard.remove(target)
                    target.reset()  # Reset obligatoire lors d'un changement de zone
                    p.hand.append(target)
                    break