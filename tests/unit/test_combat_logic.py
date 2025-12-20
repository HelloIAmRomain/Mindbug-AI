import pytest
from unittest.mock import MagicMock
from mindbug_engine.core.models import Card, Player, CardEffect
from mindbug_engine.core.state import GameState
from mindbug_engine.managers.combat_manager import CombatManager
from mindbug_engine.core.consts import Trigger, Keyword, EffectType


class MockGame:
    """Simule la façade Engine pour les tests unitaires."""

    def __init__(self, state):
        self.state = state


@pytest.fixture
def mock_managers():
    """Crée un environnement isolé pour tester CombatManager."""
    p1 = Player("P1")
    p2 = Player("P2")
    state = GameState([], p1, p2)

    # Mock de la façade
    mock_game = MockGame(state)
    effect_manager = MagicMock()

    # On instancie avec le MockGame
    cm = CombatManager(mock_game, effect_manager)
    return cm, state, effect_manager


def test_resolve_fight_unblocked_standard(mock_managers):
    cm, state, _ = mock_managers
    attacker = Card("a", "Attacker", 5)

    # Placement sur le board pour que le manager trouve le owner
    state.player1.board = [attacker]
    state.active_player_idx = 0

    # Résolution (Attaquant P1 vs Pas de bloqueur -> P2 prend les dégâts)
    att_dead, blk_dead = cm.resolve_fight(attacker, None)

    # Par défaut, dégâts = 1 PV dans le moteur standard (ou power selon règles)
    # Le moteur actuel fait -1 HP par défaut pour unblocked
    # state.player2.hp part de 3
    assert state.player2.hp < 3
    assert not att_dead


def test_resolve_fight_unblocked_trigger(mock_managers):
    cm, state, em_mock = mock_managers

    effect = CardEffect(EffectType.MODIFY_STAT, target={"group": "OPPONENT"}, params={"amount": 1})
    attacker = Card("m", "Mosquito", 4, trigger=Trigger.ON_UNBLOCKED, effects=[effect])

    state.player1.board = [attacker]
    state.active_player_idx = 0

    cm.resolve_fight(attacker, None)

    # Vérification : L'effet doit être déclenché via l'EffectManager
    em_mock.apply_effect.assert_called_once()


def test_tough_mechanic_survival(mock_managers):
    """
    Vérifie que lors d'un combat mortel, une créature Tenace survit
    et est marquée comme endommagée.
    """
    cm, state, _ = mock_managers

    # 1. Attaquant très fort (Puissance 10)
    attacker = Card("k", "Killer", 10)
    state.player1.board = [attacker]

    # 2. Défenseur faible mais Tenace (Puissance 3)
    shield_card = Card("t", "Tank", 3, keywords=[Keyword.TOUGH])
    state.player2.board = [shield_card]

    # Simulation du combat
    # Le manager va voir que 10 > 3, donc Tank devrait mourir,
    # MAIS il va voir TOUGH et annuler la mort.
    cm.resolve_fight(attacker, shield_card)

    # VÉRIFICATIONS

    # 1. La carte est TOUJOURS sur le plateau (Sauvée par le Juge)
    assert shield_card in state.player2.board

    # 2. La carte est marquée endommagée (Le bouclier a sauté)
    assert shield_card.is_damaged is True

    # Note : Le retrait effectif du mot-clé "TOUGH" de la liste se fera
    # au prochain engine.update_board_states(), pas instantanément ici.
    # On vérifie donc surtout le flag is_damaged.