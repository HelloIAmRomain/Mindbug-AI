import pytest
from unittest.mock import MagicMock
from mindbug_ai.mcts.node import MCTSNode


def test_mcts_node_initialization():
    node = MCTSNode(move=("PLAY", 0))
    assert node.visits == 0
    assert node.wins == 0.0
    assert node.children == []


def test_mcts_node_update_backpropagation():
    node = MCTSNode()
    # 1ère visite : Victoire
    node.update(1)
    assert node.visits == 1
    assert node.wins == 1.0

    # 2ème visite : Défaite
    node.update(0)
    assert node.visits == 2
    assert node.wins == 1.0  # Toujours 1 victoire au total


def test_mcts_node_add_child():
    parent = MCTSNode()

    # Mock de l'état du jeu
    mock_state = MagicMock()
    mock_state.get_legal_moves.return_value = [("ATTACK", 0)]
    mock_state.state.active_player_idx = 1

    child = parent.add_child(
        move=("PLAY", 0), state=mock_state, player_index=0)

    assert child in parent.children
    assert child.parent == parent
    assert child.move == ("PLAY", 0)

    # On vérifie que l'index a bien été enregistré
    assert child.player_just_moved == 0
    assert child.untried_moves == [("ATTACK", 0)]


def test_mcts_node_uct_selection():
    root = MCTSNode()
    root.visits = 10

    # Enfant A : 100% winrate mais peu visité
    child_a = MCTSNode(parent=root)
    child_a.visits = 2
    child_a.wins = 2.0

    # Enfant B : 0% winrate mais plus visité
    child_b = MCTSNode(parent=root)
    child_b.visits = 5
    child_b.wins = 0.0

    root.children = [child_a, child_b]

    # UCB doit favoriser A (Exploitation) ici
    selected = root.uct_select_child()
    assert selected == child_a
