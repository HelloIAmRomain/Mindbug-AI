import pytest
from mindbug_engine.core.models import Card
from mindbug_engine.engine import MindbugGame
# CORRECTION IMPORT : On importe le nouveau nom de classe
from mindbug_ai.agent import HeuristicAgent 

@pytest.fixture
def game_state():
    g = MindbugGame(verbose=False)
    # On configure les PV initiaux
    g.state.player2.hp = 3
    g.state.player1.hp = 3
    # On force P2 comme joueur actif (puisque c'est l'IA qu'on teste généralement)
    g.state.active_player_idx = 1
    return g

def test_ai_evaluation_hp_advantage(game_state):
    agent = HeuristicAgent()
    
    # CORRECTION SIGNATURE : _evaluate_state prend maintenant l'index (1 pour P2)
    score_even = agent._evaluate_state(game_state, player_idx=1)

    game_state.state.player2.hp = 5
    score_winning = agent._evaluate_state(game_state, player_idx=1)
    
    assert score_winning > score_even

def test_ai_evaluation_board_power(game_state):
    agent = HeuristicAgent()
    
    # On donne une créature puissante à P2
    game_state.state.player2.board = [Card("s", "Tiger", 9)]
    game_state.state.player1.board = []

    score = agent._evaluate_state(game_state, player_idx=1)
    
    # Le score doit être positif car avantage de board
    assert score > 0

def test_ai_mindbug_heuristic_decision(game_state):
    agent = HeuristicAgent()

    game_state.state.active_player_idx = 1  # P2

    # Cas 1 : Petite carte -> On passe
    game_state.state.pending_card = Card("rat", "Rat", 1)
    moves = [("PASS", -1), ("MINDBUG", -1)]
    
    # L'IA doit avoir des mindbugs pour que ce soit valide
    game_state.state.player2.mindbugs = 2 
    
    assert agent._decide_mindbug(game_state, moves) == ("PASS", -1)

    # Cas 2 : Grosse carte -> On vole
    game_state.state.pending_card = Card("drag", "Dragon", 10)
    assert agent._decide_mindbug(game_state, moves) == ("MINDBUG", -1)
    
    # Cas 3 : Grosse carte mais plus de Mindbug -> On est obligé de passer
    game_state.state.player2.mindbugs = 0
    # Note: Dans la réalité, engine ne proposerait pas ("MINDBUG", -1) dans moves,
    # mais l'agent vérifie quand même ses ressources.
    assert agent._decide_mindbug(game_state, moves) == ("PASS", -1)
