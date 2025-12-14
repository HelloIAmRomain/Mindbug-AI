import pytest
import pygame
import os
from unittest.mock import Mock, MagicMock
from mindbug_gui.renderer import GameRenderer
from mindbug_engine.models import Card
from mindbug_engine.rules import Phase

# Configuration "Headless" (sans écran physique)
os.environ["SDL_VIDEODRIVER"] = "dummy"

@pytest.fixture
def renderer_with_spy(game):
    """
    Crée un renderer dont la méthode _draw_card est espionnée.
    Intègre les mocks pour Config et ResourceManager.
    """
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    
    # 1. Mock Config
    mock_config = Mock()
    mock_config.debug_mode = True 
    mock_config.game_mode = "DEV"
    
    # 2. Mock ResourceManager (NOUVEAU)
    mock_res = Mock()
    # On doit retourner une vraie Font Pygame ou un Mock qui se comporte comme tel
    # Ici on retourne une font système basique pour éviter le crash
    mock_res.get_font.return_value = pygame.font.SysFont("Arial", 20)
    # On retourne une surface vide pour les images
    mock_res.get_image.return_value = pygame.Surface((10, 10))

    # 3. Instanciation avec les dépendances
    renderer = GameRenderer(screen, game, config=mock_config, res_manager=mock_res)
    
    # 4. Espionnage de _draw_card
    renderer._draw_card = MagicMock()
    
    return renderer

def test_highlight_my_hand_in_main_phase(game, renderer_with_spy):
    """P1 Main Phase : Ma main doit briller, pas celle de l'adversaire."""
    game.phase = Phase.P1_MAIN
    game.active_player_idx = 0
    
    # Setup cartes
    c1 = Card("c1", "MyCard", 1)
    c2 = Card("c2", "OppCard", 1)
    game.player1.hand = [c1]
    game.player2.hand = [c2]
    
    # On lance le rendu de la main P1
    # Arguments : cards, y, zone_type, hidden, legal_moves, is_board
    renderer_with_spy._draw_card_row(game.player1.hand, 100, "HAND_P1", False, [("PLAY", 0)], False)
    
    # Vérif : _draw_card a été appelé avec highlight=True
    # Signature _draw_card : card, x, y, hidden, is_board, highlight, ...
    # highlight est le 6ème argument (index 5)
    args, _ = renderer_with_spy._draw_card.call_args
    assert args[5] is True, "La carte en main de P1 devrait être en surbrillance"

    # On lance le rendu de la main P2
    renderer_with_spy._draw_card.reset_mock()
    renderer_with_spy._draw_card_row(game.player2.hand, 10, "HAND_P2", True, [("PLAY", 0)], False)
    
    args, _ = renderer_with_spy._draw_card.call_args
    assert args[5] is False, "La carte en main de P2 NE DOIT PAS être en surbrillance"

def test_highlight_board_in_attack_phase(game, renderer_with_spy):
    """P1 Attack Phase : Mon board brille, pas ma main."""
    game.phase = Phase.P1_MAIN 
    game.active_player_idx = 0
    
    c_hand = Card("h", "Hand", 1)
    c_board = Card("b", "Board", 1)
    game.player1.hand = [c_hand]
    game.player1.board = [c_board]
    
    legal = [("ATTACK", 0), ("PLAY", 0)] 
    
    # Test du Board
    renderer_with_spy._draw_card_row(game.player1.board, 200, "BOARD_P1", False, legal, is_board=True)
    args, _ = renderer_with_spy._draw_card.call_args
    assert args[5] is True, "La créature sur le plateau devrait briller pour attaquer"

def test_highlight_selection_phase(game, renderer_with_spy):
    """Resolution Phase : On doit pouvoir illuminer le board adverse."""
    game.phase = Phase.RESOLUTION_CHOICE
    game.active_player_idx = 0
    
    target = Card("t", "Target", 1)
    game.player2.board = [target]
    
    # L'engine attend une sélection chez l'adversaire
    legal = [("SELECT_BOARD_P2", 0)]
    
    renderer_with_spy._draw_card_row(game.player2.board, 50, "BOARD_P2", False, legal, is_board=True)
    
    args, _ = renderer_with_spy._draw_card.call_args
    assert args[5] is True, "La créature adverse devrait briller car c'est une cible valide"
