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
    candidates: List[Any]  # Les objets éligibles (Cartes, Joueurs...)
    count: int  # Nombre d'éléments à choisir
    reason: str  # Raison technique (ex: "HUNTER_TARGET")
    selector: Any  # Qui choisit (Player)
    callback: Optional[Callable] = None  # Fonction exécutée une fois la sélection finie

    # État interne de la sélection en cours (Accumulateur)
    current_selection: List[Any] = field(default_factory=list)

    def __repr__(self):
        return f"SelectionRequest(Reason={self.reason}, Count={self.count}, Selector={self.selector.name})"


class CardEffect:
    """
    Représentation générique d'un effet (Action/Verbe).
    Agnostique des règles.
    """

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

    def __init__(self,
                 id: str,
                 name: str,
                 power: int,
                 keywords: List[str] = None,
                 trigger: str = None,
                 effects: List[CardEffect] = None,
                 image_path: str = None,
                 set_id: str = "FIRST_CONTACT"):
        self.id = id
        self.name = name

        # --- GESTION PUISSANCE (Fix V3) ---
        # On sépare la valeur imprimée sur la carte (référence) de la valeur actuelle (jeu)
        self.base_power = power
        self.power = power

        # --- GESTION MOTS-CLÉS ---
        self.base_keywords = list(keywords) if keywords else []
        self.keywords = list(self.base_keywords)

        self.trigger = trigger
        self.effects = effects if effects else []
        self.image_path = image_path
        self.set = set_id

        # État mutable
        self.is_damaged = False

    @classmethod
    def from_dict(cls, data):
        """Construction depuis le JSON."""
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
        """Reset COMPLET (Mort, Retour en main). Tout revient à neuf."""
        self.is_damaged = False
        self.power = self.base_power
        self.keywords = list(self.base_keywords)

    def refresh_state(self):
        """
        Reset PARTIEL (Recalcul des stats en début de phase).
        On garde l'état 'is_damaged' (bouclier cassé).
        """
        self.power = self.base_power
        self.keywords = list(self.base_keywords)

        # LOGIQUE TOUGH : Si la carte est endommagée, elle perd son bouclier
        if self.is_damaged and "TOUGH" in self.keywords:
            self.keywords.remove("TOUGH")

    def copy(self):
        """
        Crée une copie profonde de la carte (Snapshot de l'état actuel).
        Utilisé par l'IA pour simuler des coups sans altérer le jeu réel.
        """
        # 1. On instancie avec les valeurs de BASE (Structure)
        new_c = Card(
            id=self.id,
            name=self.name,
            power=self.base_power,  # Important : on passe le base_power au constructeur
            keywords=list(self.base_keywords),
            trigger=self.trigger,
            effects=[e.copy() for e in self.effects],
            image_path=self.image_path,
            set_id=self.set
        )

        # 2. On applique l'état COURANT (Mutation)
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


# On exporte aussi GameState ici si besoin, sinon il est dans state.py
# Pour éviter les cycles, on suppose qu'il est défini ailleurs ou ici.
@dataclass
class GameState:
    """État complet du jeu (Snapshot)."""
    player1: Player = field(default_factory=lambda: Player("P1"))
    player2: Player = field(default_factory=lambda: Player("P2"))
    active_player_idx: int = 0
    phase: Any = "SETUP"  # Typé Any pour éviter import circulaire de Phase
    deck: List[Card] = field(default_factory=list)

    # Contexte
    attacker: Optional[Card] = None
    blocker: Optional[Card] = None
    pending_card: Optional[Card] = None
    winner: Optional[Player] = None

    # Requête active (Question posée à l'UI)
    active_request: Optional[SelectionRequest] = None

    @property
    def active_player(self):
        return self.player1 if self.active_player_idx == 0 else self.player2

    @property
    def opponent(self):
        return self.player2 if self.active_player_idx == 0 else self.player1