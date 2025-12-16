import pytest
from mindbug_engine.models import Card, Player
from mindbug_engine.engine import MindbugGame
from mindbug_engine.rules import Phase
from mindbug_ai.agent import MindbugAgent


@pytest.fixture
def game_state():
    """Crée un état de jeu artificiel pour tester l'évaluation."""
    g = MindbugGame()
    # P2 est l'IA
    g.player2.hp = 3
    g.player1.hp = 3
    return g


def test_ai_evaluation_hp_advantage(game_state):
    """L'IA doit préférer avoir plus de PV."""
    agent = MindbugAgent()

    # Cas 1 : Égalité
    score_even = agent._evaluate_state(game_state, game_state.player2)

    # Cas 2 : IA a l'avantage
    game_state.player2.hp = 5
    score_winning = agent._evaluate_state(game_state, game_state.player2)

    assert score_winning > score_even


def test_ai_evaluation_board_power(game_state):
    """L'IA doit préférer avoir des créatures fortes."""
    agent = MindbugAgent()

    # P2 a une créature forte, P1 rien
    game_state.player2.board = [Card("strong", "Tiger", 9)]
    game_state.player1.board = []

    score = agent._evaluate_state(game_state, game_state.player2)
    assert score > 0  # Score positif attendu


def test_ai_unknown_cards_filtering(game_state):
    """L'IA ne doit pas compter les cartes qu'elle voit comme 'inconnues'."""
    agent = MindbugAgent()

    c1 = Card("c1", "C1", 1)
    c2 = Card("c2", "C2", 2)
    c3 = Card("c3", "C3", 3)
    game_state.full_deck = [c1, c2, c3]
    game_state.all_cards_ref = [c1, c2, c3]  # Important pour la référence

    # Une carte dans la main de l'IA
    visible_card = game_state.full_deck[0]
    game_state.player2.hand = [visible_card]

    # Une carte dans la défausse adverse (donc visible car jouée)
    discarded_card = game_state.full_deck[1]
    game_state.player1.discard = [discarded_card]

    unknowns = agent._get_unknown_cards(game_state)

    # Ces cartes ne doivent PAS être dans les inconnues
    assert visible_card not in unknowns
    assert discarded_card not in unknowns

    # Une carte dans la main adverse (cachée) DOIT être inconnue (si elle est dans all_cards_ref)
    hidden_card = game_state.full_deck[2]
    game_state.player1.hand = [hidden_card]

    # Note: Dans la logique actuelle, unknown_pool vient de all_cards_ref.
    # Si hidden_card est dans le jeu, elle est mathématiquement dans les inconnues pour l'IA.
    assert hidden_card in unknowns


def test_ai_mindbug_heuristic_decision(game_state):
    """Vérifie que l'heuristique Mindbug réagit aux créatures fortes."""
    agent = MindbugAgent()

    # Cas 1 : Créature faible (Rat, 1) -> Pass
    game_state.pending_card = Card("rat", "Rat", 1)
    moves = [("PASS", -1), ("MINDBUG", -1)]
    decision = agent._decide_mindbug(game_state, moves)
    assert decision == ("PASS", -1)

    # Cas 2 : Créature très forte (Dragon, 10) -> Mindbug
    game_state.pending_card = Card("drag", "Dragon", 10)
    decision = agent._decide_mindbug(game_state, moves)
    assert decision == ("MINDBUG", -1)

    # Cas 3 : Créature Poison (Valeur stratégique) -> Mindbug souvent
    game_state.pending_card = Card("scorp", "Scorpion", 2, keywords=["POISON"])
    # On force un score élevé dans l'algo (Poison = +5 points) -> Total 7 -> Seuil 7
    decision = agent._decide_mindbug(game_state, moves)
    assert decision == ("MINDBUG", -1)