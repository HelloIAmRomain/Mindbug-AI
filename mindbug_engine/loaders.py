import json
import os
from typing import List
from .models import Card, CardAbility

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
                id=str(entry.get("id")),
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
                unique_sets = set()
                for entry in data:
                    s = entry.get("set", "FIRST_CONTACT")
                    unique_sets.add(s)
                return sorted(list(unique_sets))
        except:
            return ["FIRST_CONTACT"]
