from typing import List, Optional


class CardAbility:
    """Représente l'effet spécial d'une carte."""

    def __init__(self, code: str, target: str = "NONE", value: int = 0, condition: str = None,
                 condition_value: int = 0):
        self.code = code  # ex: "STEAL_CREATURE"
        self.target = target  # ex: "OPP", "SELF"
        self.value = value  # ex: 1
        self.condition = condition  # ex: "MAX_POWER"
        self.condition_value = condition_value

    def __repr__(self):
        return f"Ability({self.code}, T:{self.target}, V:{self.value})"

    def copy(self):
        """Crée une copie indépendante de la capacité."""
        return CardAbility(
            code=self.code,
            target=self.target,
            value=self.value,
            condition=self.condition,
            condition_value=self.condition_value
        )


class Card:
    """Objet de données représentant une carte."""

    def __init__(self, id: str, name: str, power: int, keywords: List[str] = None, trigger: str = None,
                 ability: Optional[CardAbility] = None, image_path: str = None, set_id: str = "FIRST_CONTACT"):
        self.id = id
        self.name = name
        self.power = power
        self.base_keywords = list(keywords) if keywords else []
        self.keywords = list(self.base_keywords)
        self.trigger = trigger
        self.ability = ability

        # C'est ici que l'info est stockée
        self.image_path = image_path
        self.set = set_id

        # État mutable
        self.is_damaged = False

    @classmethod
    def from_dict(cls, data):
        """
        Méthode essentielle pour créer une Carte depuis le JSON.
        C'est elle qui récupère le champ 'image' du fichier de données.
        """
        # 1. Gestion de l'Abilité (si présente)
        ability_data = data.get("ability")
        ability = None
        if ability_data:
            ability = CardAbility(
                code=ability_data.get("code"),
                target=ability_data.get("target", "NONE"),
                value=ability_data.get("value", 0),
                condition=ability_data.get("condition"),
                condition_value=ability_data.get("condition_value", 0)
            )

        # 2. Gestion de l'Image (CORRECTION ICI)
        # On lit "image" dans le JSON, et on le passe à "image_path"
        img_file = data.get("image")

        # Fallback : Si pas d'image dans le JSON, on tente l'ID + .jpg
        if not img_file and "id" in data:
            img_file = f"{data['id']}.jpg"

        return cls(
            id=data["id"],
            name=data["name"],
            power=data["power"],
            keywords=data.get("keywords", []),
            trigger=data.get("trigger"),
            ability=ability,
            image_path=img_file,  # <-- Passage du nom de fichier
            set_id=data.get("set", "FIRST_CONTACT")
        )

    def reset(self):
        """Réinitialise la carte (quand elle quitte le jeu)."""
        self.is_damaged = False
        self.keywords = list(self.base_keywords)

    def __repr__(self):
        dmg = "*" if self.is_damaged else ""
        return f"[{self.name}{dmg} ({self.power})]"

    def copy(self):
        """Crée une copie profonde de la carte pour la simulation."""
        # 1. Création de la nouvelle instance avec les valeurs de base
        new_card = Card(
            id=self.id,
            name=self.name,
            power=self.power,
            keywords=list(self.base_keywords),  # Important : copie de la liste
            trigger=self.trigger,
            ability=self.ability.copy() if self.ability else None,
            image_path=self.image_path,  # On copie bien le chemin de l'image
            set_id=self.set
        )

        # 2. Copie de l'état mutable actuel
        new_card.keywords = list(self.keywords)
        new_card.is_damaged = self.is_damaged

        return new_card


class Player:
    """Représente l'état d'un joueur."""

    def __init__(self, name: str):
        self.name = name
        self.hp = 3
        self.mindbugs = 2

        # Zones de jeu (Listes de Cartes)
        self.deck: List[Card] = []
        self.hand: List[Card] = []
        self.board: List[Card] = []
        self.discard: List[Card] = []

    def __repr__(self):
        return f"Player({self.name}, HP:{self.hp}, MB:{self.mindbugs})"

    def copy(self):
        """Crée une copie profonde du joueur et de toutes ses cartes."""
        new_player = Player(self.name)

        # Copie des valeurs simples
        new_player.hp = self.hp
        new_player.mindbugs = self.mindbugs

        # Copie profonde récursive des listes de cartes
        new_player.deck = [c.copy() for c in self.deck]
        new_player.hand = [c.copy() for c in self.hand]
        new_player.board = [c.copy() for c in self.board]
        new_player.discard = [c.copy() for c in self.discard]

        return new_player