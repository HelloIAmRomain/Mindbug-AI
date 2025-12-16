import json
import os
from .models import Card, CardAbility

class CardLoader:
    @staticmethod
    def load_deck(json_path):
        """Charge les cartes depuis le fichier JSON."""
        if not os.path.exists(json_path):
            print(f"⚠️ Erreur : Fichier introuvable {json_path}")
            return []

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                cards_data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"⚠️ Erreur JSON : {e}")
            return []

        deck = []
        for c_data in cards_data:
            # 1. Création de l'Ability
            ability = None
            if "ability" in c_data and c_data["ability"]:
                ab_data = c_data["ability"]
                ability = CardAbility(
                    code=ab_data.get("code"),
                    target=ab_data.get("target"),
                    value=ab_data.get("value", 0),
                    condition=ab_data.get("condition"),
                    condition_value=ab_data.get("condition_value", 0)
                )

            # 2. Création de la Carte
            try:
                card = Card(
                    id=c_data["id"],
                    name=c_data["name"],
                    power=c_data["power"],
                    keywords=c_data.get("keywords", []),
                    trigger=c_data.get("trigger"),
                    ability=ability,
                    image_path=c_data.get("image_path"),
                    # Utilisation correcte de set_id suite au refactoring
                    set_id=c_data.get("set", "FIRST_CONTACT") 
                )
                deck.append(card)
            except TypeError as e:
                print(f"⚠️ Erreur instanciation carte {c_data.get('name', '???')}: {e}")

        return deck

    # --- AJOUT DE LA MÉTHODE MANQUANTE ---
    @staticmethod
    def get_available_sets(json_path):
        """
        Scanne le fichier JSON pour lister les sets uniques disponibles.
        Utilisé par le menu pour afficher les options de sets.
        """
        if not os.path.exists(json_path):
            return []
            
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                cards_data = json.load(f)
                
            found_sets = set()
            for c in cards_data:
                # Récupère le set ou la valeur par défaut
                s = c.get("set", "FIRST_CONTACT")
                found_sets.add(s)
                
            return list(found_sets)
            
        except Exception as e:
            print(f"⚠️ Erreur lors du scan des sets : {e}")
            return []
