from mindbug_engine.core.consts import Difficulty
from .interface import AgentInterface
from .mcts.agent import MCTSAgent


class AgentFactory:
    @staticmethod
    def create_agent(difficulty: Difficulty, strategy: str = "HEURISTIC") -> AgentInterface:
        """
        Crée l'agent.
        Args:
            difficulty: Enum Difficulty (EASY, MEDIUM, HARD) ou str compatible.
            strategy: "MCTS".
        """
        if isinstance(difficulty, str):
            try:
                difficulty = Difficulty(difficulty)
            except ValueError:
                raise ValueError(f"❌ Difficulté inconnue : {difficulty}")

        # Sélection de la stratégie
        if strategy == "MCTS":
            # On adapte le temps de réflexion selon la difficulté
            time_budget = 0.5  # Easy
            if difficulty == Difficulty.MEDIUM:
                time_budget = 1.5
            if difficulty == Difficulty.HARD:
                time_budget = 3.0
            if difficulty == Difficulty.EXTREME:
                time_budget = 6.0

            return MCTSAgent(simulation_time=time_budget)

        else:
            raise ValueError(f"❌ Stratégie inconnue : {strategy}")
