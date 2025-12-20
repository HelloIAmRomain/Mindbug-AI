from typing import Any, Dict
from mindbug_engine.managers.effects.base import EffectAction

class CopyKeywordsAction(EffectAction):
    def __init__(self, effect_manager):
        self.em = effect_manager

    def execute(self, target: Any, params: Dict, source: Any, owner: Any, opponent: Any):
        source_group = params.get("source")
        if not source_group: return

        # On simule un effet temporaire pour réutiliser la logique de ciblage du manager
        from mindbug_engine.core.models import CardEffect
        fake_effect = CardEffect("COPY", target={"group": source_group})
        sources = self.em._get_candidates(fake_effect, source, owner, opponent)

        for src in sources:
            if hasattr(src, 'keywords'):
                for kw in src.keywords:
                    if kw not in target.keywords:
                        target.keywords.append(kw)