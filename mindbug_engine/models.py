import json
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class CardAbility:
    """Structure machine-readable d'une capacité"""
    code: str              # Ex: "DESTROY_CREATURE"
    target: str            # Ex: "OPP", "SELF"
    value: int = 0         # Valeur numérique (Ex: 1 carte, 3 dégâts)
    
    # --- NOUVEAUX CHAMPS (Conditions dynamiques) ---
    condition: str = "ALWAYS"  # Type (MIN_POWER, MAX_POWER, CHOICE_USER...)
    condition_value: int = 0   # Seuil (Ex: 6 pour "Puissance >= 6")
    # -----------------------------------------------

    keyword: str = ""      # Pour GIVE_KEYWORD

@dataclass
class Card:
    id: str
    name: str
    power: int
    keywords: List[str] = field(default_factory=list)
    
    trigger: Optional[str] = None      
    ability: Optional[CardAbility] = None 
    
    text: str = "" 
    image_path: str = "" # Lien vers l'image
    
    # États dynamiques
    is_damaged: bool = False
    
    def __post_init__(self):
        self.keywords = [k.upper() for k in self.keywords]

    def copy(self):
        return Card(
            id=self.id,
            name=self.name,
            power=self.power,
            keywords=list(self.keywords),
            trigger=self.trigger,
            ability=self.ability, 
            text=self.text,
            image_path=self.image_path
        )
    
    def __repr__(self):
        extras = []
        if self.keywords: extras.append(",".join(self.keywords))
        if self.trigger: extras.append(f"⚡{self.trigger}")
        status = " [🩸BLESSÉ]" if self.is_damaged else ""
        info = f" | {' '.join(extras)}" if extras else ""
        return f"[{self.name} ({self.power}){info}{status}]"

    def reset(self):
        """Réinitialise l'état de la carte (soigne les blessures)."""
        self.is_damaged = False

@dataclass
class Player:
    name: str
    is_human: bool = False
    hp: int = 3
    mindbugs: int = 2
    hand: List[Card] = field(default_factory=list)
    board: List[Card] = field(default_factory=list)
    discard: List[Card] = field(default_factory=list)
    deck: List[Card] = field(default_factory=list) # Pioche personnelle
    
    def __repr__(self):
        return f"Player {self.name} (HP:{self.hp}, MB:{self.mindbugs})"

class CardLoader:
    @staticmethod
    def load_deck(filepath: str) -> List[Card]:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Erreur chargement JSON: {e}")
            return []
        
        full_deck = []
        for entry in data:
            ability_data = entry.get("ability")
            ability_obj = None
            if ability_data:
                ability_obj = CardAbility(
                    code=ability_data.get("code", "UNKNOWN"),
                    target=ability_data.get("target", "ANY"),
                    value=ability_data.get("value", 0),
                    # Parsing des conditions
                    condition=ability_data.get("condition", "ALWAYS"),
                    condition_value=ability_data.get("condition_value", 0),
                    keyword=ability_data.get("keyword", "")
                )

            template_card = Card(
                id=entry["id"],
                name=entry["name"],
                power=entry["power"],
                keywords=entry.get("keywords", []),
                trigger=entry.get("trigger"),
                ability=ability_obj,
                text=entry.get("text", ""),
                image_path=entry.get("image", "")
            )
            
            count = entry.get("copies", 1)
            for _ in range(count):
                full_deck.append(template_card.copy())
                
        return full_deck
