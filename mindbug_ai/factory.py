from mindbug_engine.core.consts import Difficulty
from .interface import AgentInterface
from .agent import HeuristicAgent


class AgentFactory:
    @staticmethod
    def create_agent(difficulty: Difficulty, strategy: str = "HEURISTIC") -> AgentInterface:
        """
        Crée l'agent.
        Args:
            difficulty: Enum Difficulty (EASY, MEDIUM, HARD) ou str compatible.
        """
        # Conversion robuste Str -> Enum
        if isinstance(difficulty, str):
            try:
                difficulty = Difficulty(difficulty)
            except ValueError:
                # Fallback sécurisé ou Crash (Fail Fast)
                raise ValueError(f"❌ Difficulté inconnue : {difficulty}")

        if strategy == "HEURISTIC":
            return HeuristicAgent(difficulty=difficulty)

        else:
            raise ValueError(f"❌ Stratégie inconnue : {strategy}")