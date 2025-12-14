import pytest
import pygame
import os
from unittest.mock import MagicMock, Mock, patch
from mindbug_gui.window import MindbugGUI
from mindbug_engine.rules import Phase
from contextlib import contextmanager

# Configuration "Headless"
os.environ["SDL_VIDEODRIVER"] = "dummy"

@pytest.fixture
def gui(game):
    """
    Fixture qui crée une interface graphique (GUI) mockée pour tester les clics.
    """
    pygame.init()
    
    screen = pygame.display.set_mode((800, 600))
    
    # Mock Config
    mock_config = Mock()
    mock_config.game_mode = "SOLO"
    mock_config.debug_mode = False
    mock_config.active_sets = ["FIRST_CONTACT"]
    mock_config.active_card_ids = []
    # IMPORTANT : On définit la résolution car window.py fait "w, h = config.settings.resolution"
    mock_config.settings.resolution = (800, 600)
    
    # IMPORTANT : On patche ResourceManager via unittest.mock.patch
    with patch('mindbug_gui.window.ResourceManager') as MockResManager:
        # On instancie la GUI
        app = MindbugGUI(mock_config, screen=screen)
        
    # On remplace le moteur interne par notre fixture 'game'
    app.game = game
    
    # On espionne la méthode step
    app.game.step = MagicMock()
    
    # On vide les zones de clic par défaut
    app.renderer.click_zones = []
    
    return app

# --- TESTS ---

def test_regression_click_opponent_hand_does_nothing(gui, game):
    """
    TEST DE NON-RÉGRESSION CRITIQUE.
    Vérifie que cliquer sur la main de l'adversaire pendant MON tour ne fait RIEN.
    """
    # Contexte : Tour de P1
    game.phase = Phase.P1_MAIN
    game.active_player_idx = 0 
    
    # Simulation : Zone de clic sur main P2
    fake_rect = pygame.Rect(10, 10, 100, 150)
    gui.renderer.click_zones = [
        {"type": "HAND_P2", "index": 0, "rect": fake_rect}
    ]
    
    # Action : P1 clique sur la main de P2
    gui._handle_left_click((50, 50)) 
    
    # Vérification : Aucune action envoyée
    gui.game.step.assert_not_called()

def test_click_my_hand_plays_card(gui, game):
    """Vérifie que cliquer sur MA main envoie bien l'ordre PLAY."""
    game.phase = Phase.P1_MAIN
    game.active_player_idx = 0
    
    fake_rect = pygame.Rect(100, 500, 100, 150)
    gui.renderer.click_zones = [
        {"type": "HAND_P1", "index": 0, "rect": fake_rect}
    ]
    
    with list_legal_moves(game, [("PLAY", 0)]):
        gui._handle_left_click((150, 550))
    
    gui.game.step.assert_called_with("PLAY", 0)

def test_click_selection_opponent_valid(gui, game):
    """Vérifie qu'en phase de sélection, on peut cliquer chez l'adversaire."""
    game.phase = Phase.RESOLUTION_CHOICE
    game.active_player_idx = 0
    
    fake_rect = pygame.Rect(200, 100, 100, 150)
    gui.renderer.click_zones = [
        {"type": "BOARD_P2", "index": 1, "rect": fake_rect}
    ]
    
    with list_legal_moves(game, [("SELECT_BOARD_P2", 1)]):
        gui._handle_left_click((250, 150))
        
    gui.game.step.assert_called_with("SELECT_BOARD_P2", 1)

def test_click_buttons(gui, game):
    """Vérifie que les boutons d'interface fonctionnent."""
    game.phase = Phase.MINDBUG_DECISION
    
    fake_rect = pygame.Rect(700, 300, 100, 50)
    gui.renderer.click_zones = [
        {"type": "BTN_PASS", "index": -1, "rect": fake_rect}
    ]
    
    with list_legal_moves(game, [("PASS", -1)]):
        gui._handle_left_click((710, 310))
        
    gui.game.step.assert_called_with("PASS", -1)

# --- UTILITAIRE ---

@contextmanager
def list_legal_moves(game, moves):
    """Context manager pour mocker get_legal_moves."""
    original_method = game.get_legal_moves
    game.get_legal_moves = MagicMock(return_value=moves)
    try:
        yield
    finally:
        game.get_legal_moves = original_method
