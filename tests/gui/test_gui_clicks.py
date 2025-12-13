import pytest
import pygame
import os
from unittest.mock import MagicMock
from mindbug_gui.window import MindbugGUI
from mindbug_engine.rules import Phase
from contextlib import contextmanager

# Configuration "Headless" pour tourner sans écran physique
os.environ["SDL_VIDEODRIVER"] = "dummy"

@pytest.fixture
def gui(game):
    """
    Fixture qui crée l'interface graphique (GUI) dans un environnement de test.
    Injecte un écran virtuel et mock la méthode 'step' du moteur pour vérifier les actions.
    """
    pygame.init()
    
    # 1. CRÉATION DE L'ÉCRAN VIRTUEL (Avant d'initier la GUI)
    screen = pygame.display.set_mode((800, 600))
    
    # 2. CONFIGURATION
    # On a besoin d'une config valide, même basique
    from config import GameConfig
    cfg = GameConfig()
    cfg.game_mode = "SOLO" # Pour éviter le rideau dans les tests
    
    # 3. INSTANCIATION AVEC INJECTION DE L'ÉCRAN
    # C'est ici que ça plantait avant : on passe 'screen' explicitement
    app = MindbugGUI(cfg, screen=screen)
    
    # 4. REMPLACEMENT DU MOTEUR
    # On remplace l'instance de jeu interne par notre fixture 'game' (qui est propre et contrôlée)
    app.game = game
    
    # 5. ESPIONNAGE (SPY)
    # On remplace la méthode game.step par un Mock pour vérifier si elle est appelée
    app.game.step = MagicMock()
    
    return app

# --- TESTS ---

def test_regression_click_opponent_hand_does_nothing(gui, game):
    """
    TEST DE NON-RÉGRESSION CRITIQUE.
    Vérifie que cliquer sur la main de l'adversaire pendant MON tour ne fait RIEN.
    (Empêche le bug où je jouais ma propre carte en cliquant chez l'adversaire).
    """
    # Contexte : Tour de P1
    game.phase = Phase.P1_MAIN
    game.active_player_idx = 0 
    
    # Simulation : Le renderer a dessiné la main de P2 à ces coordonnées
    fake_rect = pygame.Rect(10, 10, 100, 150)
    gui.renderer.click_zones = [
        {"type": "HAND_P2", "index": 0, "rect": fake_rect}
    ]
    
    # Action : P1 clique sur la main de P2
    gui._handle_click((50, 50)) 
    
    # Vérification : Aucune action ne doit être envoyée au moteur
    gui.game.step.assert_not_called()

def test_click_my_hand_plays_card(gui, game):
    """
    Vérifie que cliquer sur MA main envoie bien l'ordre PLAY.
    """
    # Contexte : Tour de P1
    game.phase = Phase.P1_MAIN
    game.active_player_idx = 0
    
    # Simulation : Main de P1
    fake_rect = pygame.Rect(100, 500, 100, 150)
    gui.renderer.click_zones = [
        {"type": "HAND_P1", "index": 0, "rect": fake_rect}
    ]
    
    # On force le moteur à dire que ce coup est légal
    with list_legal_moves(game, [("PLAY", 0)]):
        gui._handle_click((150, 550)) # Clic au milieu de la carte
    
    # Vérification : L'action PLAY a bien été envoyée
    gui.game.step.assert_called_with("PLAY", 0)

def test_click_selection_opponent_valid(gui, game):
    """
    Vérifie l'exception à la règle de sécurité : 
    En phase de SÉLECTION (Ciblage), on a le droit de cliquer chez l'adversaire.
    """
    # Contexte : Phase de résolution d'effet (ex: Chasseur)
    game.phase = Phase.RESOLUTION_CHOICE
    game.active_player_idx = 0
    
    # Simulation : Plateau de P2
    fake_rect = pygame.Rect(200, 100, 100, 150)
    gui.renderer.click_zones = [
        {"type": "BOARD_P2", "index": 1, "rect": fake_rect}
    ]
    
    # Le moteur attend qu'on choisisse une cible chez P2
    with list_legal_moves(game, [("SELECT_BOARD_P2", 1)]):
        gui._handle_click((250, 150))
        
    # Vérification : L'action de sélection est envoyée
    gui.game.step.assert_called_with("SELECT_BOARD_P2", 1)

def test_click_buttons(gui, game):
    """
    Vérifie que les boutons d'interface (ex: PASSER) fonctionnent.
    """
    game.phase = Phase.MINDBUG_DECISION
    
    # Simulation : Bouton affiché à l'écran
    fake_rect = pygame.Rect(700, 300, 100, 50)
    gui.renderer.click_zones = [
        {"type": "BTN_PASS", "index": -1, "rect": fake_rect}
    ]
    
    with list_legal_moves(game, [("PASS", -1)]):
        gui._handle_click((710, 310))
        
    gui.game.step.assert_called_with("PASS", -1)

# --- UTILITAIRE ---

@contextmanager
def list_legal_moves(game, moves):
    """
    Context manager utilitaire pour mocker temporairement 'get_legal_moves'.
    Permet de dire au test "Fais comme si l'engine autorisait ces coups".
    """
    original_method = game.get_legal_moves
    # On remplace la méthode par un Mock qui retourne notre liste 'moves'
    game.get_legal_moves = MagicMock(return_value=moves)
    try:
        yield
    finally:
        # On remet la méthode originale après le test
        game.get_legal_moves = original_method
