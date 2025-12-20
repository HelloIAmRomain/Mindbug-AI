import json
import os
from typing import List
from mindbug_engine.core.models import Card
from mindbug_engine.utils.logger import log_error


class CardLoader:
    """
    Infrastructure : Charge les données depuis le disque (JSON).
    Standard : Utilise la clé 'copies' pour définir le nombre d'instances.
    """

    @staticmethod
    def load_from_json(file_path: str) -> List[Card]:
        if not os.path.exists(file_path):
            log_error(f"Fichier introuvable : {file_path}")
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            cards = []
            for item in data:
                # STANDARDISATION : On utilise uniquement 'copies'
                # Défaut à 1 si non précisé (carte unique)
                num_copies = item.get("copies", 1)

                try:
                    num_copies = int(num_copies)
                except ValueError:
                    log_error(f"Erreur données : 'copies' invalide pour {item.get('name')}")
                    continue

                for _ in range(num_copies):
                    try:
                        # Card.from_dict s'occupe du reste (id, name, effects...)
                        card = Card.from_dict(item)
                        cards.append(card)
                    except Exception as e_card:
                        log_error(f"Erreur instanciation carte {item.get('name', '?')} : {e_card}")

            return cards

        except Exception as e:
            log_error(f"Erreur globale parsing JSON {file_path} : {e}")
            return []