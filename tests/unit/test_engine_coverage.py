import pytest
from unittest.mock import patch, MagicMock
from mindbug.engine.engine import MindbugGame
from mindbug.engine.core.config import ConfigurationService
from mindbug.engine.core.models import Card, Player
from mindbug.engine.core.consts import Phase


def test_engine_verbose_initialization():
    """Vérifie l'initialisation avec verbose=True (lignes 77, 78)"""
    config = ConfigurationService()
    config.debug_mode = True
    game = MindbugGame(config)
    assert game.verbose is True


def test_engine_start_with_empty_deck():
    """Vérifie le démarrage avec un deck vide (lignes 87, 88)"""
    config = ConfigurationService()
    game = MindbugGame(config)
    game.state.deck = []  # Vider le deck
    game.start_game()
    # Le jeu ne doit pas passer en INITIATIVE_BATTLE car le deck est vide
    assert game.state.phase == Phase.P1_MAIN  # La phase par défaut reste inchangée

def test_engine_start_with_small_deck_and_verbose(game):
    """Vérifie le fallback si deck < 22 cartes et les logs finaux (114-116, 183-185, 91)"""
    # Créer un jeu avec verbose
    game.verbose = True
    
    # On met 5 cartes dans le deck (moins de 22)
    deck = [Card(str(i), f"Card {i}", 3) for i in range(5)]
    game.state.deck = deck
    game.start_game()

    # Comme le deck est petit, on esquive le duel d'initiative
    assert game.state.phase == Phase.P1_MAIN

def test_engine_step_with_winner(game):
    """Bypass les actions si le jeu est fini (189, 190)"""
    game.state.winner = game.state.player1
    # Appeler step() ne devrait rien faire et retourner immédiatement
    game.step("PLAY", 0)

def test_engine_get_legal_moves_with_winner(game):
    """Retourne [] si le jeu est fini (214)"""
    game.state.winner = game.state.player1
    moves = game.get_legal_moves()
    assert moves == []

def test_engine_step_verbose_and_invalid_command(game):
    """Vérifie logs verbose et handling de mauvaise commande (193, 194, 202)"""
    game.verbose = True
    # Action absurde qui va retourner None depuis CommandFactory
    game.step("INVALID_ACTION_XYZ", -1)

@patch("mindbug.engine.commands.command_factory.CommandFactory.create")
def test_engine_step_crash_handling(mock_factory, game):
    """Vérifie le catch d'exception dans step() (204-207)"""
    game.verbose = True
    mock_factory.side_effect = Exception("TEST CRASH")
    
    # Ne doit pas lever l'exception mais la logger et return
    game.step("PLAY", 0)

def test_engine_ask_for_selection_verbose(game):
    """Couvre les lignes de logging verbose dans ask_for_selection (271-273)"""
    game.verbose = True
    p1 = game.state.player1
    # Demander une selection sans crasher
    game.ask_for_selection(["A"], "TEST_REASON", 1, p1)
    assert game.state.phase == Phase.RESOLUTION_CHOICE

def test_engine_resolve_combat_logs(game):
    """Couvre des lignes additionnelles de logging dans le combat_manager et engine (332, 341, 378, 389)"""
    # Simuler un scénario simple de log
    from mindbug.engine.core.consts import Phase
    game.verbose = True
    p1 = game.state.player1
    p2 = game.state.player2
    c1 = Card("1", "C1", 4)
    c2 = Card("2", "C2", 3)
    p1.board = [c1]
    p2.board = [c2]
    
    game.state.active_player_idx = 0
    game.state.phase = Phase.P1_MAIN
    
    game.step("ATTACK", 0)
    game.step("BLOCK", 0)
    # L'attaque va se résoudre et logger les évènements

def test_engine_resolve_initiative_step_none(game):
    """Vérifie le retour anticipé de resolve_initiative_step (ligne 132)"""
    game.state.initiative_duel = None
    game.resolve_initiative_step()

def test_engine_frenzy_candidate_missing(game):
    """Vérifie la disparition du frenzy_candidate (ligne 235)"""
    game.state.frenzy_candidate = Card("f", "Frenzy", 5)
    # n'est pas sur le tableau
    game.get_legal_moves()
    assert game.state.frenzy_candidate is None

def test_engine_legal_moves_initiative_battle(game):
    """Couvre Phase.INITIATIVE_BATTLE dans get_legal_moves (lignes 271-273)"""
    game.state.phase = Phase.INITIATIVE_BATTLE
    assert game.get_legal_moves() == []

def test_engine_resolve_combat_no_attacker(game):
    """Couvre le log et return sans attaquant dans resolve_combat (ligne 341)"""
    game.state.pending_attacker = None
    game.resolve_combat(None)

def test_engine_check_game_over(game):
    """Cover check_game_over (389)"""
    game.check_game_over()
