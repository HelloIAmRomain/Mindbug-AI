import pytest
from unittest.mock import MagicMock
from mindbug.engine.managers.effect_manager import EffectManager
from mindbug.engine.core.models import Card, Player, CardEffect
from mindbug.engine.core.consts import EffectType

def test_apply_effect_no_effects(game):
    """Couvre la ligne 43 (retour rapide si pas d'effets)"""
    # game est disponible via conftest
    em = game.effect_manager
    p1 = game.state.player1
    p2 = game.state.player2
    card = Card("1", "Aucun", 1)  # pas d'effet
    # Ne doit pas planter ni rien faire
    em.apply_effect(card, p1, p2)

def test_process_single_effect_fallback_select(game):
    """Couvre la sélection NON GÉRÉE (ex: NONE ou malformée) (ligne 113)"""
    em = game.effect_manager
    p1 = game.state.player1
    p2 = game.state.player2
    card = Card("1", "C1", 1)
    # L'effet a un select inconnu
    effect = CardEffect(effect_type=EffectType.MODIFY_STAT, params={"stat": "HP", "value": 1}, target={"group": "ALLIES", "select": "UNKNOWN_SELECT"})
    p1.board = [card]
    
    # Doit retomber sur le fallback et appeler le callback pour all_targets
    em._process_single_effect(effect, card, p1, p2)
    # Sachant que stats hp ne crashe pas si c'est appliqué, cela permet
    # d'aller jusqu'au bout.

def test_dispatch_verb_exception(game):
    """Couvre les lignes 130-131 (Exceptions pendant exécution)"""
    em = game.effect_manager
    p1 = game.state.player1
    p2 = game.state.player2
    card = Card("1", "C1", 1)
    effect = CardEffect(effect_type=EffectType.DESTROY, params={}, target={"group": "ALLIES"})
    
    # On mock l'action handler pour forcer une exception
    mock_handler = MagicMock()
    mock_handler.execute.side_effect = Exception("Crash volontaire")
    em._actions[EffectType.DESTROY] = mock_handler
    
    # Ne doit pas lever l'exception car elle est catchée
    em._dispatch_verb(effect, card, card, p1, p2)

def test_dispatch_verb_unhandled(game):
    """Couvre la ligne 133 (Action non enregistrée)"""
    em = game.effect_manager
    p1 = game.state.player1
    p2 = game.state.player2
    card = Card("1", "C1", 1)
    effect = CardEffect(effect_type=1000, params={}, target={"group": "ALLIES"})  # un type invalide
    
    em._dispatch_verb(effect, card, card, p1, p2)

def test_get_candidates_blocker(game):
    """Couvre les lignes 162-164 (group='BLOCKER')"""
    em = game.effect_manager
    p1 = game.state.player1
    p2 = game.state.player2
    card = Card("1", "C1", 1)
    effect = CardEffect(effect_type=EffectType.DESTROY, params={}, target={"group": "BLOCKER"})
    res = em._get_candidates(effect, card, p1, p2)
    assert res == []  # Le code actuel renvoie une liste vide par la collection

def test_check_global_conditions_fallback(game):
    """Couvre la ligne 188"""
    em = game.effect_manager
    p1 = game.state.player1
    p2 = game.state.player2
    res = em._check_global_conditions({"context": "UNHANDLED_CONTEXT"}, p1, p2)
    assert res is True

def test_compare_gt_lt_fallback(game):
    """Couvre les lignes 222, 224, 225"""
    em = game.effect_manager
    assert em._compare(5, "GT", 3) is True
    assert em._compare(3, "LT", 5) is True
    assert em._compare(5, "INVALID", 3) is False

def test_get_owner(game):
    """Couvre la ligne 230"""
    em = game.effect_manager
    p1 = game.state.player1
    assert em._get_owner(p1) == p1
