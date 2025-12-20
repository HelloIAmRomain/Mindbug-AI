from typing import Any, Dict
from mindbug_engine.managers.effects.base import EffectAction
from mindbug_engine.utils.logger import log_info

class ModifyStatAction(EffectAction):
    def execute(self, target: Any, params: Dict, source: Any, owner: Any, opponent: Any):
        stat = params.get("stat", "HP")
        op = params.get("operation", "SUB")
        val = params.get("amount", 0)

        current_val = 0
        is_hp = (stat == "HP" and hasattr(target, "hp"))
        is_power = (stat == "POWER" and hasattr(target, "power"))

        if not (is_hp or is_power):
            return

        current_val = target.hp if is_hp else target.power

        # Gestion de la Sirène Mystérieuse (COPY)
        if op == "COPY":
            src_str = params.get("source")
            if src_str == "OPPONENT":
                opp_player = opponent if target == owner else owner
                val = opp_player.hp
                op = "SET"

        # Calcul de la nouvelle valeur
        new_val = current_val
        if op == "ADD": new_val += val
        elif op == "SUB": new_val -= val
        elif op == "SET": new_val = val

        # Application
        if is_hp:
            target.hp = max(0, new_val)
            log_info(f"   -> {getattr(target, 'name', 'Player')} HP : {target.hp}")
        elif is_power:
            target.power = max(0, new_val)
