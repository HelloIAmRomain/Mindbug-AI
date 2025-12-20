import pytest
import pygame
from unittest.mock import MagicMock
from mindbug_engine.core.consts import Difficulty
from mindbug_gui.screens.settings_screen import SettingsScreen


# --- STUB (Faux Objet Simple) ---
class MockApp:
    def __init__(self):
        self.screen = MagicMock()
        self.screen.get_width.return_value = 1280
        self.screen.get_height.return_value = 720

        self.width = 1280
        self.height = 720

        # Configuration Mockée
        self.config = MagicMock()
        self.config.ai_difficulty = Difficulty.MEDIUM
        self.config.debug_mode = False
        self.config.available_sets_in_db = ["First Contact", "Beyond"]
        self.config.active_sets = ["First Contact"]
        self.config.save_settings = MagicMock()

        self.res_manager = MagicMock()
        mock_font = MagicMock()
        mock_font.render.return_value = pygame.Surface((1, 1))
        self.res_manager.get_font.return_value = mock_font


@pytest.fixture
def mock_app():
    return MockApp()


@pytest.fixture
def settings_screen(mock_app):
    screen = SettingsScreen(mock_app)
    return screen


# --- TESTS ---

def test_init_displays_correct_label(mock_app):
    """Vérifie que Difficulty.MEDIUM affiche le bon label."""
    mock_app.config.ai_difficulty = Difficulty.MEDIUM
    screen = SettingsScreen(mock_app)

    # Recherche du bouton via l'action standardisée
    btn = next(w for w in screen.widgets if getattr(w, 'action', '') == "CYCLE_DIFF")

    # CORRECTION ICI : On vérifie "INTERMÉDIAIRE" au lieu de "MOYEN"
    assert "INTERMÉDIAIRE" in btn.text


def test_action_cycle_difficulty_states(mock_app, settings_screen):
    """Vérifie le cycle : MEDIUM -> HARD -> EASY -> MEDIUM."""

    # 1. Départ MEDIUM -> Clic -> HARD
    mock_app.config.ai_difficulty = Difficulty.MEDIUM
    settings_screen._cycle_difficulty()
    assert mock_app.config.ai_difficulty == Difficulty.HARD

    # 2. Clic -> EASY
    settings_screen._cycle_difficulty()
    assert mock_app.config.ai_difficulty == Difficulty.EASY

    # 3. Clic -> MEDIUM
    settings_screen._cycle_difficulty()
    assert mock_app.config.ai_difficulty == Difficulty.MEDIUM


def test_save_on_exit(mock_app, settings_screen):
    """Vérifie la sauvegarde en quittant avec ECHAP."""
    mock_app.config.save = MagicMock()  # On s'assure que c'est bien 'save' qui est mocké

    evt = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_ESCAPE})
    settings_screen.handle_events([evt])
    mock_app.config.save.assert_called_once()


def test_toggles_initial_state(mock_app):
    """Vérifie que les toggles (Debug, Sets) s'initialisent correctement."""
    mock_app.config.debug_mode = True
    screen = SettingsScreen(mock_app)

    # On cherche le toggle debug
    tg = next(w for w in screen.widgets if getattr(w, 'action', '') == "TOGGLE_DEBUG")

    assert tg.value is True