from typing import List, Optional

class CardAbility:
    """Représente l'effet spécial d'une carte."""
    def __init__(self, code: str, target: str = "NONE", value: int = 0, condition: str = None, condition_value: int = 0):
        self.code = code                # ex: "STEAL_CREATURE"
        self.target = target            # ex: "OPP", "SELF"
        self.value = value              # ex: 1 (nombre de cartes/dégâts)
        self.condition = condition      # ex: "MAX_POWER"
        self.condition_value = condition_value # ex: 6

    def __repr__(self):
        return f"Ability({self.code}, T:{self.target}, V:{self.value})"

class Card:
    """Objet de données représentant une carte."""
    def __init__(self, id: str, name: str, power: int, keywords: List[str] = None, trigger: str = None, ability: Optional[CardAbility] = None, image_path: str = None, set_name: str = "FIRST_CONTACT"):
        self.id = id
        self.name = name
        self.power = power
        self.base_keywords = list(keywords) if keywords else [] 
        self.keywords = list(self.base_keywords)                
        self.trigger = trigger          
        self.ability = ability
        self.image_path = image_path
        self.set = set_name
        self.is_damaged = False

    def reset(self):
        self.is_damaged = False
        self.keywords = list(self.base_keywords) 

    def __repr__(self):
        dmg = "*" if self.is_damaged else ""
        return f"[{self.name}{dmg} ({self.power})]"

class Player:
    """Représente l'état d'un joueur."""
    def __init__(self, name: str):
        self.name = name
        self.hp = 3
        self.mindbugs = 2
        self.deck: List[Card] = []
        self.hand: List[Card] = []
        self.board: List[Card] = []
        self.discard: List[Card] = []

    def __repr__(self):
        return f"Player({self.name}, HP:{self.hp}, MB:{self.mindbugs})"
