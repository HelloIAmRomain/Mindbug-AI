from __future__ import annotations
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass, field

# =============================================================================
#  OBJETS DE DONNÉES (MODELS)
# =============================================================================

@dataclass
class SelectionRequest:
    """
    Objet encapsulant une demande de sélection à l'interface/joueur.
    Stocké dans game.state.active_request.
    """
    candidates: List[Any]
    count: int
    reason: str
    selector: Any
    callback: Optional[Callable] = None
    current_selection: List[Any] = field(default_factory=list)

    def __repr__(self):
        return f"SelectionRequest(Reason={self.reason}, Count={self.count}, Selector={self.selector.name})"


class CardEffect:
    """Représentation générique d'un effet."""
    def __init__(self, effect_type: str, target: Dict[str, Any] = None, condition: Dict[str, Any] = None,
                 params: Dict[str, Any] = None):
        self.type = effect_type
        self.target = target or {}
        self.condition = condition or {}
        self.params = params or {}

    def __repr__(self):
        return f"Effect({self.type}, T:{self.target})"

    def copy(self):
        return CardEffect(self.type, self.target.copy(), self.condition.copy(), self.params.copy())


class Card:
    """Objet de données représentant une carte."""
    def __init__(self, id: str, name: str, power: int, keywords: List[str] = None,
                 trigger: str = None, effects: List[CardEffect] = None,
                 image_path: str = None, set_id: str = "FIRST_CONTACT"):
        self.id = id
        self.name = name
        self.base_power = power
        self.power = power
        self.base_keywords = list(keywords) if keywords else []
        self.keywords = list(self.base_keywords)
        self.trigger = trigger
        self.effects = effects if effects else []
        self.image_path = image_path
        self.set = set_id
        self.is_damaged = False

    @classmethod
    def from_dict(cls, data):
        raw_effects = data.get("effects", [])
        parsed_effects = [
            CardEffect(e.get("type"), e.get("target"), e.get("condition"), e.get("params"))
            for e in raw_effects
        ]
        img_file = data.get("image") or f"{data.get('id', 'unknown')}.jpg"
        return cls(
            id=data.get("id", "unknown"),
            name=data.get("name", "Unknown"),
            power=data.get("power", 0),
            keywords=data.get("keywords", []),
            trigger=data.get("trigger"),
            effects=parsed_effects,
            image_path=img_file,
            set_id=data.get("set", "FIRST_CONTACT")
        )

    def reset(self):
        self.is_damaged = False
        self.power = self.base_power
        self.keywords = list(self.base_keywords)

    def refresh_state(self):
        self.power = self.base_power
        self.keywords = list(self.base_keywords)
        if self.is_damaged and "TOUGH" in self.keywords:
            self.keywords.remove("TOUGH")

    def copy(self):
        new_c = Card(
            id=self.id,
            name=self.name,
            power=self.base_power,
            keywords=list(self.base_keywords),
            trigger=self.trigger,
            effects=[e.copy() for e in self.effects],
            image_path=self.image_path,
            set_id=self.set
        )
        new_c.power = self.power
        new_c.keywords = list(self.keywords)
        new_c.is_damaged = self.is_damaged
        return new_c

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
        return f"Player({self.name})"

    def copy(self):
        p = Player(self.name)
        p.hp = self.hp
        p.mindbugs = self.mindbugs
        p.deck = [c.copy() for c in self.deck]
        p.hand = [c.copy() for c in self.hand]
        p.board = [c.copy() for c in self.board]
        p.discard = [c.copy() for c in self.discard]
        return p
