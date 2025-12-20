import pytest
from mindbug_engine.engine import MindbugGame
from mindbug_engine.core.models import Card
from mindbug_ai.agent import HeuristicAgent

@pytest.fixture
def ai_game():
    """Un jeu vide prêt pour le test."""
    g = MindbugGame(verbose=False)
    # Reset complet
    g.state.player1.board = []
    g.state.player1.hand = []
    g.state.player2.board = []
    g.state.player2.hand = []
    return g

def test_heuristic_prefers_winning(ai_game):
    agent = HeuristicAgent()
    
    # Cas 1 : P2 (l'IA) a gagné
    ai_game.state.winner = ai_game.state.player2
    score_win = agent._evaluate_state(ai_game, player_idx=1)
    
    # Cas 2 : P2 a perdu
    ai_game.state.winner = ai_game.state.player1
    score_loss = agent._evaluate_state(ai_game, player_idx=1)
    
    assert score_win > 0
    assert score_loss < 0
    assert score_win > score_loss

def test_heuristic_prefers_hp_advantage(ai_game):
    agent = HeuristicAgent()
    
    # Scénario A : Égalité PV
    ai_game.state.player2.hp = 3
    ai_game.state.player1.hp = 3
    score_even = agent._evaluate_state(ai_game, player_idx=1)
    
    # Scénario B : Avantage PV
    ai_game.state.player2.hp = 5
    score_advantage = agent._evaluate_state(ai_game, player_idx=1)
    
    assert score_advantage > score_even

def test_heuristic_prefers_board_presence(ai_game):
    agent = HeuristicAgent()
    
    # Scénario A : Board vide
    score_empty = agent._evaluate_state(ai_game, player_idx=1)
    
    # Scénario B : Une créature puissante
    strong_creature = Card("lion", "Lion", 8)
    ai_game.state.player2.board.append(strong_creature)
    score_with_unit = agent._evaluate_state(ai_game, player_idx=1)
    
    assert score_with_unit > score_empty
