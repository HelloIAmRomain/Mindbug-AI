from abc import ABC, abstractmethod
from typing import Tuple, Optional


class AgentInterface(ABC):
    """
    Interface abstraite pour tous les agents (Bots).
    Garantit que le jeu peut interagir avec n'importe quelle IA (Règles, ML, MCTS)
    sans connaître son implémentation interne.
    """

    @abstractmethod
    def get_action(self, game) -> Optional[Tuple[str, int]]:
        """
        Reçoit l'état du jeu (game) et retourne la meilleure action trouvée.

        Args:
            game (MindbugGame): Une copie (clone) de l'état du jeu.
                                L'agent peut le modifier pour simuler.

        Returns:
            Tuple (ActionType, Index) ou None si aucun coup possible.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Nom d'affichage de l'agent."""
        pass