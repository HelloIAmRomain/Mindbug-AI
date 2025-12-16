import pytest
from unittest.mock import MagicMock
from mindbug_engine.models import Card, Player, CardAbility
from mindbug_engine.combat import CombatManager
from mindbug_engine.rules import Keyword


@pytest.fixture
def mock_game():
    """Mock minimal du jeu pour le CombatManager."""
    game = MagicMock()
    game.player1 = Player("P1")
    game.player2 = Player("P2")
    # Par défaut P1 actif
    game.active_player = game.player1
    game.opponent = game.player2
    return game


def test_resolve_fight_unblocked_standard(mock_game):
    """Test dégâts normaux (-1 PV)."""
    cm = CombatManager(mock_game)
    attacker = Card("a", "Attacker", 5)
    mock_game.player1.board = [attacker]

    # Mock calcul puissance
    cm.calculate_real_power = MagicMock(return_value=5)

    # Pas de bloqueur
    cm.resolve_fight(attacker, None)

    # Vérif
    assert mock_game.player2.hp == 2  # 3 - 1
    # On vérifie que apply_effect n'a PAS été appelé
    mock_game.effect_manager.apply_effect.assert_not_called()


def test_resolve_fight_unblocked_trigger(mock_game):
    """Test Turboustique : Trigger ON_ATTACK_UNBLOCKED."""
    cm = CombatManager(mock_game)

    # Carte avec trigger spécial
    attacker = Card("m", "Mosquito", 4, trigger="ON_ATTACK_UNBLOCKED",
                    ability=CardAbility("SET_OPPONENT_HP_TO_ONE", "OPP", 1))
    mock_game.player1.board = [attacker]

    cm.calculate_real_power = MagicMock(return_value=4)

    # Action : Pas de bloqueur
    cm.resolve_fight(attacker, None)

    # Vérif : Pas de dégâts standards (-1 PV) immédiats si l'effet prend le relais
    # (Note : Dans votre implémentation, vous déléguerez à l'EffectManager)
    mock_game.effect_manager.apply_effect.assert_called_once_with(
        mock_game, attacker, mock_game.player1, mock_game.player2
    )
    # Les PV ne doivent pas descendre via la logique standard (c'est l'effet qui le fera)
    assert mock_game.player2.hp == 3


def test_apply_lethal_damage_tough(mock_game):
    """Test Tenace (Tough) : survit à la première mort."""
    cm = CombatManager(mock_game)
    shield_card = Card("t", "Tank", 3, keywords=["TOUGH"])

    # 1ère mort (bouclier)
    cm.apply_lethal_damage(shield_card, mock_game.player1)

    assert shield_card.is_damaged is True
    # destroy_card ne doit PAS être appelé
    assert len(mock_game.player1.discard) == 0

    # 2ème mort (plus de bouclier)
    # On doit mocker destroy_card ou vérifier qu'elle est appelée
    # Ici testons la logique interne de apply_lethal_damage qui appelle self.destroy_card

    # On mock destroy_card pour vérifier l'appel
    cm.destroy_card = MagicMock()

    cm.apply_lethal_damage(shield_card, mock_game.player1)
    cm.destroy_card.assert_called_once_with(shield_card, mock_game.player1)