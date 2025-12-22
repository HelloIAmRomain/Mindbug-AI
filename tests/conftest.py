from mindbug_engine.core.consts import Difficulty
from mindbug_engine.core.models import Card, CardEffect
from mindbug_engine.engine import MindbugGame
import pytest
import sys
import os
from unittest.mock import MagicMock

# Ajout du dossier racine au path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class MockConfig:
    """Simulation de la configuration pour les tests."""

    def __init__(self):
        self.debug_mode = False
        self.game_mode = "HOTSEAT"
        self.ai_difficulty = Difficulty.MEDIUM
        self.active_sets = ["FIRST_CONTACT"]
        self.resolution = (1280, 720)
        self.fullscreen = False
        self.available_sets_in_db = ["FIRST_CONTACT"]

    def save(self):
        pass


@pytest.fixture
def game():
    """Fixture STANDARD : Jeu démarré."""
    cfg = MockConfig()
    g = MindbugGame(config=cfg)
    g.start_game()

    # On boucle tant que le jeu est bloqué en phase d'initiative.
    # Cela gère les cas d'égalité multiples (re-pioche) jusqu'à ce que les mains soient distribuées.
    while g.state.phase == "INITIATIVE_BATTLE":
        g.resolve_initiative_step()

    # 1. On vide TOUTES les zones de pioche pour éviter le remplissage auto pendant les tests
    g.state.deck = []
    g.state.player1.deck = []
    g.state.player2.deck = []

    # 2. On désactive les Mindbugs par défaut
    g.state.player1.mindbugs = 0
    g.state.player2.mindbugs = 0

    return g


@pytest.fixture
def game_empty():
    """Fixture SPÉCIFIQUE : Vrai Engine mais sans cartes distribuées."""
    cfg = MockConfig()
    g = MindbugGame(config=cfg)
    g.state.deck = []
    g.state.player1.hand = []
    g.state.player1.deck = []
    g.state.player1.board = []
    g.state.player1.discard = []

    g.state.player2.hand = []
    g.state.player2.deck = []
    g.state.player2.board = []
    g.state.player2.discard = []

    g.state.player1.hp = 3
    g.state.player2.hp = 3
    g.state.player1.mindbugs = 0
    g.state.player2.mindbugs = 0
    return g


@pytest.fixture
def create_card():
    """Factory Helper pour créer des cartes."""

    def _builder(name="TestCard", power=1, keywords=None, trigger=None,
                 effect_type=None, effect_target=None, effect_params=None,
                 effect_condition=None, effects=None, set_id="FIRST_CONTACT"):

        final_effects = []
        if effects:
            final_effects = effects
        elif effect_type:
            tgt = {"group": effect_target} if isinstance(
                effect_target, str) else (effect_target or {})
            prm = effect_params or {}
            cnd = effect_condition or {}
            final_effects.append(CardEffect(effect_type, tgt, cnd, prm))

        return Card(
            id=f"test_{name.lower().replace(' ', '_')}",
            name=name,
            power=power,
            keywords=keywords if keywords else [],
            trigger=trigger,
            effects=final_effects,
            set_id=set_id
        )

    return _builder
