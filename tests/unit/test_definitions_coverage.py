import pytest
from unittest.mock import MagicMock
from mindbug.engine.commands.definitions import (
    ConfirmInitiativeCommand,
    PlayCardCommand,
    AttackCommand,
    BlockCommand,
    MindbugCommand
)
from mindbug.engine.core.consts import Phase

def test_confirm_initiative_command(game):
    """Couvre la ligne 16 (ConfirmInitiativeCommand)"""
    # Just mock resolve_initiative_step to prove it was called
    game.resolve_initiative_step = MagicMock()
    cmd = ConfirmInitiativeCommand()
    cmd.execute(game)
    game.resolve_initiative_step.assert_called_once()

def test_play_card_invalid_index(game):
    """Couvre les lignes 33-34"""
    # N'a pas de log_error direct assert mais on vérifie qu'il abort
    cmd = PlayCardCommand(999)
    # L'exécution retourne immédiatement sans modifier pending_card
    game.state.pending_card = None
    cmd.execute(game)
    assert game.state.pending_card is None

def test_attack_command_invalid_index(game):
    """Couvre les lignes 67-68"""
    cmd = AttackCommand(999)
    game.state.pending_attacker = None
    cmd.execute(game)
    assert game.state.pending_attacker is None

def test_block_command_invalid_index(game):
    """Couvre les lignes 147-148"""
    cmd = BlockCommand(999)
    # Ne devrait pas crasher, mais logger une erreur.
    # Pour simuler, on vérifie que resolve_combat n'est pas appelé
    game.resolve_combat = MagicMock()
    cmd.execute(game)
    game.resolve_combat.assert_not_called()

def test_mindbug_command_replay_pending(game):
    """Couvre les lignes 189-190"""
    # Le voleur vole une carte avec effet ON_PLAY demandant sélection
    # Ce qui met self.state.phase à RESOLUTION_CHOICE avant la fin du mindbug
    p1 = game.state.player1
    p2 = game.state.player2
    p2.mindbugs = 1
    
    # Simuler le voleur comme player actif
    game.state.active_player_idx = 1
    
    # Feindre qu'une carte attendait
    from mindbug.engine.core.models import Card
    game.state.pending_card = Card("1", "C1", 2)
    
    # Hook la phase pour bloquer pdt la réception du mindbug
    game.state.phase = Phase.RESOLUTION_CHOICE
    
    cmd = MindbugCommand()
    cmd.execute(game)
    
    assert game.state.mindbug_replay_pending is True

def test_mindbug_command_illegal(game):
    """Couvre la ligne 194 (Illegal mindbug)"""
    p2 = game.state.player2
    p2.mindbugs = 0  # no mindbugs
    game.state.active_player_idx = 1
    game.state.pending_card = MagicMock()
    
    cmd = MindbugCommand()
    cmd.execute(game)
    
    # La pending card doit tjs être là, car annulée
    assert game.state.pending_card is not None
