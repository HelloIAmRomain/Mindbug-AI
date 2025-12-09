import pytest
import json
from unittest.mock import patch, mock_open
from mindbug_engine.models import Card, Player, CardLoader, CardAbility

# --- TESTS : CLASSE PLAYER ---

def test_player_initialization():
    """Vérifie qu'un joueur démarre avec les bonnes stats."""
    p = Player("TestUser")
    assert p.name == "TestUser"
    assert p.hp == 3
    assert p.mindbugs == 2
    assert p.hand == []
    assert p.board == []
    assert p.discard == []

# --- TESTS : CLASSE CARD ---

def test_card_initialization_defaults():
    """Vérifie les valeurs par défaut d'une carte."""
    c = Card(id="01", name="Rat", power=2)
    assert c.keywords == []
    assert c.trigger is None
    assert c.is_damaged is False

def test_card_copy_independence():
    """
    CRITIQUE : Vérifie que modifier une copie n'affecte pas l'original.
    Essentiel pour le Deck Building (on copie les templates).
    """
    original = Card(id="01", name="Rat", power=2)
    copy = original.copy()
    
    # On modifie la copie (ex: elle prend des dégâts)
    copy.is_damaged = True
    copy.power = 0 # Imaginons un debuff
    
    # L'original doit rester intact
    assert original.is_damaged is False
    assert original.power == 2
    
    # Ce sont deux objets différents en mémoire
    assert original is not copy

def test_card_reset():
    """Vérifie que reset() soigne bien la carte."""
    c = Card(id="01", name="Rat", power=2)
    c.is_damaged = True
    
    c.reset()
    
    assert c.is_damaged is False

# --- TESTS : CARD LOADER (Avec Mocking) ---

def test_loader_simple_json():
    """Vérifie le chargement d'un JSON simple."""
    # On simule un contenu de fichier JSON
    fake_json = json.dumps([
        {"id": "c1", "name": "TestCard", "power": 5, "copies": 1}
    ])
    
    # On 'patch' la fonction open() pour qu'elle lise notre fake_json
    with patch("builtins.open", mock_open(read_data=fake_json)):
        deck = CardLoader.load_deck("dummy_path.json")
        
        assert len(deck) == 1
        assert deck[0].name == "TestCard"
        assert deck[0].power == 5

def test_loader_handles_copies():
    """Vérifie que 'copies': 2 génère bien deux instances."""
    fake_json = json.dumps([
        {"id": "c1", "name": "TwinRat", "power": 2, "copies": 2}
    ])
    
    with patch("builtins.open", mock_open(read_data=fake_json)):
        deck = CardLoader.load_deck("dummy_path.json")
        
        assert len(deck) == 2
        assert deck[0].name == "TwinRat"
        assert deck[1].name == "TwinRat"
        
        # Vérification cruciale : Ce doivent être deux objets distincts
        assert deck[0] is not deck[1]

def test_loader_parses_ability():
    """Vérifie que la structure complexe 'ability' est bien lue."""
    fake_json = json.dumps([
        {
            "id": "c1", "name": "Mage", "power": 1, "copies": 1,
            "ability": {
                "code": "FIREBALL",
                "target": "OPP",
                "value": 3,
                "condition": "NONE"
            }
        }
    ])
