import json
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class CardAbility:
    """Structure machine-readable d'une capacité"""
    code: str              # Ex: "STEAL_CREATURE"
    target: str            # Ex: "OPP" (Opponent), "SELF"
    value: int = 0         # Valeur numérique (Ex: 1 carte, 3 dégâts)
    condition: str = ""    # Ex: "POWER_GE_6" (Power >= 6)
    keyword: str = ""      # Pour les effets qui donnent des mots-clés

@dataclass
class Card:
    id: str
    name: str
    power: int
    keywords: List[str] = field(default_factory=list)
    
    # Gestion des Triggers et Capacités
    trigger: Optional[str] = None      # Quand ? (ON_PLAY, ON_DEATH...)
    ability: Optional[CardAbility] = None # Quoi ? (L'effet codé)
    
    text: str = "" # Texte descriptif pour l'humain
    
    # États dynamiques (Gameplay)
    is_damaged: bool = False
    
    def __post_init__(self):
        # Normalisation
        self.keywords = [k.upper() for k in self.keywords]

    def copy(self):
        """Créer une instance unique pour le jeu"""
        return Card(
            id=self.id,
            name=self.name,
            power=self.power,
            keywords=list(self.keywords),
            trigger=self.trigger,
            ability=self.ability, 
            text=self.text
        )

    def __repr__(self):
        # 1. On rassemble les mots-clés et triggers
        extras = []
        if self.keywords: extras.append(",".join(self.keywords))
        if self.trigger: extras.append(f"⚡{self.trigger}")
        
        # 2. On gère l'affichage des dégâts (C'est l'ajout demandé)
        status = ""
        if self.is_damaged:
            status = " [🩸BLESSÉ]" # Icône goutte de sang pour la visibilité
        
        # 3. On assemble le tout
        info = f" | {' '.join(extras)}" if extras else ""
        return f"[{self.name} ({self.power}){info}{status}]"

    def reset(self):
        """Réinitialise l'état de la carte (soigne les blessures)."""
        self.is_damaged = False



# --- LA CLASSE MANQUANTE A ÉTÉ RAJOUTÉE ICI ---
@dataclass
class Player:
    name: str
    is_human: bool = False
    hp: int = 3
    mindbugs: int = 2
    hand: List[Card] = field(default_factory=list)
    board: List[Card] = field(default_factory=list)
    discard: List[Card] = field(default_factory=list)
    
    def __repr__(self):
        return f"Player {self.name} (HP:{self.hp}, MB:{self.mindbugs})"
# ----------------------------------------------

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
            # 1. Parsing de l'abiltiy 
            ability_data = entry.get("ability")
            ability_obj = None
            if ability_data:
                ability_obj = CardAbility(
                    code=ability_data.get("code", "UNKNOWN"),
                    target=ability_data.get("target", "ANY"),
                    value=ability_data.get("value", 0),
                    condition=ability_data.get("condition", ""),
                    keyword=ability_data.get("keyword", "")
                )

            # 2. Création du modèle
            template_card = Card(
                id=entry["id"],
                name=entry["name"],
                power=entry["power"],
                keywords=entry.get("keywords", []),
                trigger=entry.get("trigger"),
                ability=ability_obj,
                text=entry.get("text", "")
            )
            
            # 3. Duplication selon le nombre de copies
            count = entry.get("copies", 1)
            for _ in range(count):
                full_deck.append(template_card.copy())
                
        return full_deck

if __name__ == "__main__":
    # Test de vérification
    deck = CardLoader.load_deck("../data/cards.json")
    print(f"Deck chargé : {len(deck)} cartes")
