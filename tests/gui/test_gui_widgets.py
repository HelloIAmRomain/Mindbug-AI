from mindbug_gui.widgets.card_view import CardView
from mindbug_gui.widgets.buttons import Button
from mindbug_engine.core.models import Card
from unittest.mock import Mock, patch
import pygame
import pytest
import os

# On garde uniquement le driver VIDEO dummy pour le mode headless
os.environ["SDL_VIDEODRIVER"] = "dummy"


@pytest.fixture(scope="function")
def pygame_setup():
    """Initialisation SANS AUDIO."""
    try:
        pygame.display.init()  # Uniquement Vidéo
        pygame.font.init()  # Uniquement Font
        pygame.display.set_mode((800, 600))
        yield
    finally:
        pygame.quit()


@pytest.fixture
def mock_resource_manager():
    with patch('mindbug_gui.widgets.card_view.ResourceManager') as MockClass:
        instance = MockClass.return_value
        instance.get_card_image.return_value = pygame.Surface((100, 140))
        instance.get_font.return_value = pygame.font.SysFont("Arial", 12)
        yield instance


# --- TESTS ---

def test_button_interaction(pygame_setup):
    # Arguments w->width, h->height, action_id->action
    btn = Button(
        x=0, y=0, width=100, height=50,
        text="Test",
        font=Mock(),
        action="CLICKED"
    )

    event = Mock()
    event.type = pygame.MOUSEBUTTONDOWN
    event.button = 1
    event.pos = (10, 10)

    btn.update(0, (10, 10))
    assert btn.handle_event(event) == "CLICKED"
