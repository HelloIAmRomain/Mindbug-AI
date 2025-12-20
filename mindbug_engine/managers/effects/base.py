from abc import ABC, abstractmethod
from typing import Any, Dict

class EffectAction(ABC):
    @abstractmethod
    def execute(self, target: Any, params: Dict, source: Any, owner: Any, opponent: Any):
        """Logique d'exécution spécifique au verbe (STEAL, DESTROY, etc.)"""
        pass