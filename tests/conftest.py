import pytest
import sys
import os

# Ajout du dossier racine au path pour que les tests trouvent le code source
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mindbug_engine.engine import MindbugGame
from mindbug_engine.models import Card, CardAbility, Player

@pytest.fixture
def game():
    """Crée une instance de jeu vierge pour chaque test."""
    # On passe une liste vide pour éviter de charger le vrai JSON et avoir un deck vide/contrôlé
    g = MindbugGame(active_card_ids=["dummy"], verbose=False) 
    # On vide les mains/decks pour les tests manuels
    g.player1.hand = []
    g.player1.board = []
    g.player1.discard = []
    g.player2.hand = []
    g.player2.board = []
    g.player2.discard = []
    return g

@pytest.fixture
def player1(game):
    return game.player1

@pytest.fixture
def player2(game):
    return game.player2

@pytest.fixture
def create_card():
    """Factory pour créer des cartes rapidement dans les tests."""
    def _builder(name="TestCard", power=1, keywords=None, ability_code=None, ability_val=0, ability_target="NONE", set_id="FIRST_CONTACT"):
        ability = None
        if ability_code:
            ability = CardAbility(code=ability_code, value=ability_val, target=ability_target)
        
        return Card(
            id="test_id", 
            name=name, 
            power=power, 
            keywords=keywords if keywords else [], 
            ability=ability,
            set_id=set_id
        )
    return _builder
