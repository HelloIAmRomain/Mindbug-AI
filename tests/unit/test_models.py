import pytest
import json
import os
from unittest.mock import patch, mock_open
from mindbug_engine.models import Card, Player, CardAbility
from mindbug_engine.loaders import CardLoader

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

def test_player_copy():
    """Vérifie que la copie d'un joueur est profonde (deep copy)."""
    p = Player("Original")
    p.hp = 1
    c1 = Card("1", "Rat", 2)
    p.hand.append(c1)
    
    # ACTION : Clonage
    clone = p.copy()
    
    # VERIFICATION
    assert clone.name == "Original"
    assert clone.hp == 1
    assert len(clone.hand) == 1
    
    # Test d'indépendance
    clone.hand[0].power = 99
    clone.hp = 3
    
    assert p.hp == 1
    assert p.hand[0].power == 2  # L'original ne doit pas changer

# --- TESTS : CLASSE CARD ---

def test_card_initialization_defaults():
    """Vérifie les valeurs par défaut d'une carte."""
    c = Card(id="01", name="Rat", power=2)
    assert c.keywords == []
    assert c.trigger is None
    assert c.is_damaged is False
    assert c.set == "FIRST_CONTACT" # Valeur par défaut

def test_card_copy_method():
    """
    Vérifie la méthode .copy() ajoutée pour l'IA.
    """
    # Setup
    ability = CardAbility("STEAL", value=1)
    original = Card(id="01", name="Rat", power=2, keywords=["HUNTER"], ability=ability, set_id="NEW_SET")
    original.is_damaged = True
    
    # Action
    copy = original.copy()
    
    # Vérifications Base
    assert copy.id == "01"
    assert copy.name == "Rat"
    assert copy.set == "NEW_SET"
    assert copy.is_damaged is True
    assert copy.ability.code == "STEAL"
    
    # Vérification Indépendance
    copy.keywords.append("POISON")
    copy.ability.value = 5
    
    assert "POISON" not in original.keywords
    assert original.ability.value == 1 # L'original ne doit pas bouger
    assert original is not copy

def test_card_reset():
    """Vérifie que reset() soigne bien la carte et réinitialise les keywords."""
    c = Card(id="01", name="Rat", power=2, keywords=["SNEAKY"])
    
    # Simulation de vie de la carte
    c.is_damaged = True
    c.keywords.append("POISON") # Volé à un ennemi
    
    c.reset()
    
    assert c.is_damaged is False
    assert "POISON" not in c.keywords
    assert "SNEAKY" in c.keywords # Le mot-clé de base doit rester

# --- TESTS : CARD LOADER (Avec Mocking) ---

def test_loader_simple_json():
    """Vérifie le chargement d'un JSON simple."""
    fake_json = json.dumps([
        {"id": "c1", "name": "TestCard", "power": 5, "set": "BASE_SET"}
    ])
    
    with patch("builtins.open", mock_open(read_data=fake_json)):
        with patch("os.path.exists", return_value=True):
            deck = CardLoader.load_deck("dummy_path.json")
            
            assert len(deck) == 1
            assert deck[0].name == "TestCard"
            assert deck[0].power == 5
            assert deck[0].set == "BASE_SET"

def test_loader_parses_ability():
    """Vérifie que la structure complexe 'ability' est bien lue."""
    fake_json = json.dumps([
        {
            "id": "c1", "name": "Mage", "power": 1, 
            "ability": {
                "code": "FIREBALL",
                "target": "OPP",
                "value": 3,
                "condition": "NONE"
            }
        }
    ])
    
    with patch("builtins.open", mock_open(read_data=fake_json)):
        with patch("os.path.exists", return_value=True):
            deck = CardLoader.load_deck("dummy.json")
            assert deck[0].ability.code == "FIREBALL"
            assert deck[0].ability.target == "OPP"
            assert deck[0].ability.value == 3

def test_models_repr():
    """Vérifie l'affichage string des objets pour le debug."""
    c = Card("c1", "TestCard", 5, keywords=["HUNTER"])
    rep = repr(c)
    assert "TestCard" in rep
    assert "5" in rep
    
    p = Player("Toto")
    p.hp = 2
    rep_p = repr(p)
    assert "Toto" in rep_p
    assert "HP:2" in rep_p
