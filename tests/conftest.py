import pytest
import sys
import os

# Ajout du dossier racine au path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mindbug_engine.engine import MindbugGame
from mindbug_engine.core.models import Card, Player, CardEffect
from mindbug_engine.core.consts import Trigger, EffectType


@pytest.fixture
def game():
    """Fixture STANDARD : Jeu démarré."""
    g = MindbugGame(verbose=False)
    g.start_game()
    return g


@pytest.fixture
def game_empty():
    """Fixture SPÉCIFIQUE : Vrai Engine mais sans cartes distribuées."""
    # On initialise normalement (crée les managers corrects)
    g = MindbugGame(verbose=False)
    g.state.deck = []
    g.state.player1.hand = []
    g.state.player1.board = []
    g.state.player1.discard = []
    g.state.player2.hand = []
    g.state.player2.board = []
    g.state.player2.discard = []
    g.state.player1.hp = 3
    g.state.player2.hp = 3
    return g


@pytest.fixture
def create_card():
    """
    Factory Helper pour créer des cartes.
    CORRIGÉ : Utilise 'set_id' au lieu de 'set'.
    """
    def _builder(name="TestCard", power=1, keywords=None, trigger=None,
                 effect_type=None, effect_target=None, effect_params=None,
                 effect_condition=None, effects=None, set_id="FIRST_CONTACT"):

        final_effects = []

        # A. Injection directe
        if effects:
            final_effects = effects
        # B. Construction via arguments
        elif effect_type:
            tgt = {"group": effect_target} if isinstance(effect_target, str) else (effect_target or {})
            prm = effect_params or {}
            cnd = effect_condition or {}

            final_effects.append(CardEffect(
                effect_type=effect_type,
                target=tgt,
                params=prm,
                condition=cnd
            ))

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