from typing import Any, Dict
from mindbug_engine.managers.effects.base import EffectAction
from mindbug_engine.core.models import Card

class DestroyAction(EffectAction):
    def __init__(self, combat_manager):
        self.combat_manager = combat_manager

    def execute(self, target: Any, params: Dict, source: Any, owner: Any, opponent: Any):
        if isinstance(target, Card):
            # On réutilise la logique de mort centralisée dans le CombatManager
            # qui gère le déplacement vers la défausse et le reset
            self.combat_manager.apply_lethal_damage(target, owner if target in owner.board else opponent)
