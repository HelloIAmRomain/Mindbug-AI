import json
import os
from typing import List, Optional, Dict, Any

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
    """
    Objet de données représentant une carte.
    Contient l'état statique (stats de base) et dynamique (dégâts, keywords copiés).
    """
    # CORRECTION ICI : Ajout de set_name dans les arguments
    def __init__(self, id: str, name: str, power: int, keywords: List[str] = None, trigger: str = None, ability: Optional[CardAbility] = None, image_path: str = None, set_name: str = "FIRST_CONTACT"):
        self.id = id
        self.name = name
        self.power = power
        
        # Gestion des mots-clés dynamiques
        self.base_keywords = list(keywords) if keywords else [] # Copie immuable
        self.keywords = list(self.base_keywords)                # Liste modifiable
        
        self.trigger = trigger          # ex: "ON_PLAY", "ON_DEATH", "PASSIVE"
        self.ability = ability
        self.image_path = image_path
        
        # CORRECTION ICI : Assignation
        self.set = set_name
        
        # État en jeu
        self.is_damaged = False

    def reset(self):
        """Réinitialise la carte à son état d'origine (quand elle quitte le jeu)."""
        self.is_damaged = False
        self.keywords = list(self.base_keywords) # On retire les mots-clés volés (Requin)

    def __repr__(self):
        # Affichage compact pour le debug console
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

class CardLoader:
    """Service de chargement des données depuis le JSON."""
    
    @staticmethod
    def load_deck(file_path: str) -> List[Card]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Fichier de cartes introuvable : {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"ERREUR CRITIQUE : JSON malformé ({file_path}) : {e}")
            return []

        cards = []
        for entry in data:
            # Parsing de l'abilité
            ability = None
            if "ability" in entry and entry["ability"]:
                ab_data = entry["ability"]
                ability = CardAbility(
                    code=ab_data.get("code"),
                    target=ab_data.get("target", "NONE"),
                    value=ab_data.get("value", 0),
                    condition=ab_data.get("condition"),
                    condition_value=ab_data.get("condition_value", 0)
                )

            # Création de la Carte
            card = Card(
                id=str(entry.get("id")), # Force string ID
                name=entry.get("name", "Unknown"),
                power=entry.get("power", 0),
                keywords=entry.get("keywords", []),
                trigger=entry.get("trigger"),
                ability=ability,
                set_name=entry.get("set", "FIRST_CONTACT"), 
                image_path=entry.get("image")
            )
            cards.append(card)
            
        return cards

    @staticmethod
    def get_available_sets(file_path: str) -> List[str]:
        """Scanne le JSON pour trouver tous les noms de sets uniques."""
        if not os.path.exists(file_path): return []
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # On utilise un set python pour avoir des valeurs uniques, puis on trie
                unique_sets = set()
                for entry in data:
                    s = entry.get("set", "FIRST_CONTACT") # Valeur par défaut si manquant
                    unique_sets.add(s)
                return sorted(list(unique_sets))
        except:
            return ["FIRST_CONTACT"] # Fallback en cas d'erreur
