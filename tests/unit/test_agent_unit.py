import pytest
from unittest.mock import MagicMock
from mindbug_engine.core.models import Card
from mindbug_engine.engine import MindbugGame
from mindbug_ai.agent import HeuristicAgent


@pytest.fixture
def game_state():
    """
    Fixture locale pour configurer un état de jeu propice aux tests d'IA.
    """
    # 1. On mock la configuration pour satisfaire le constructeur de MindbugGame
    mock_config = MagicMock()
    mock_config.debug_mode = False
    mock_config.active_sets = ["FIRST_CONTACT"]
    mock_config.ai_difficulty.value = "MEDIUM"

    # 2. Instanciation avec la config (Fix du TypeError)
    g = MindbugGame(config=mock_config)

    # 3. Configuration de l'état initial
    g.state.player2.hp = 3
    g.state.player1.hp = 3

    # On force P2 comme joueur actif (l'IA)
    g.state.active_player_idx = 1

    # Initialisation des zones vides pour éviter les erreurs d'index
    g.state.player1.hand = []
    g.state.player1.board = []
    g.state.player2.hand = []
    g.state.player2.board = []

    return g


def test_ai_evaluation_hp_advantage(game_state):
    agent = HeuristicAgent()

    # Score à égalité (3 PV chacun)
    score_even = agent._evaluate_state(game_state, player_idx=1)

    # Scénario : P2 (l'IA) a l'avantage (5 PV)
    game_state.state.player2.hp = 5
    score_winning = agent._evaluate_state(game_state, player_idx=1)

    assert score_winning > score_even


def test_ai_evaluation_board_power(game_state):
    agent = HeuristicAgent()

    # Scénario : P2 a une créature puissante sur le plateau
    game_state.state.player2.board = [Card("s", "Tiger", 9)]
    game_state.state.player1.board = []

    score = agent._evaluate_state(game_state, player_idx=1)

    # Le score doit être positif (avantage significatif)
    assert score > 0


def test_ai_mindbug_heuristic_decision(game_state):
    agent = HeuristicAgent()

    game_state.state.active_player_idx = 1  # Tour de P2

    # --- Cas 1 : Carte faible jouée par l'adversaire ---
    game_state.state.pending_card = Card("rat", "Rat", 1)
    # L'IA a encore des Mindbugs
    game_state.state.player2.mindbugs = 2
    # Les coups possibles incluent le Mindbug
    moves = [("PASS", -1), ("MINDBUG", -1)]

    # L'IA devrait choisir de PASSER
    assert agent._decide_mindbug(game_state, moves) == ("PASS", -1)

    # --- Cas 2 : Carte très puissante jouée par l'adversaire ---
    game_state.state.pending_card = Card("drag", "Dragon", 10)
    # L'IA devrait choisir de VOLER (MINDBUG)
    assert agent._decide_mindbug(game_state, moves) == ("MINDBUG", -1)

    # --- Cas 3 : Carte puissante mais plus de Mindbugs ---
    game_state.state.player2.mindbugs = 0
    # Même si le coup est théoriquement proposé (ou si l'IA vérifie par sécurité)
    assert agent._decide_mindbug(game_state, moves) == ("PASS", -1)