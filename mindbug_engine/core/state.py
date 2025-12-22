from __future__ import annotations
from typing import TYPE_CHECKING, List, Optional, Any, Tuple

from mindbug_engine.core.consts import Phase

if TYPE_CHECKING:
    from mindbug_engine.core.models import Player, Card, SelectionRequest


class GameState:
    """
    Contient TOUTES les données mutables du jeu.
    Optimisé pour la sérialisation (Pickle) afin d'accélérer l'IA.
    """

    def __init__(self, deck: List[Card], player1: Player, player2: Player):
        # --- DONNÉES PRINCIPALES ---
        self.deck = deck
        self.player1 = player1
        self.player2 = player2

        # Référence statique lourde (exclue de la copie IA)
        self.all_cards_ref: List[Card] = []

        # --- ÉTAT DU TOUR ---
        self.turn_count = 1
        self.active_player_idx = 0
        self.phase = Phase.P1_MAIN

        self.initiative_duel: Optional[Tuple[Card, Card]] = None

        # Gagnant de la partie (None tant que la partie est en cours)
        self.winner: Any = None

        # --- ÉTATS TRANSITOIRES (Machine à états) ---
        self.pending_card: Optional[Card] = None
        self.pending_attacker: Optional[Card] = None
        self.frenzy_candidate: Optional[Card] = None

        # --- INTERRUPTIONS & FLUX ---
        self.active_request: Optional[SelectionRequest] = None
        self.mindbug_replay_pending = False
        self.end_turn_pending = False

    @property
    def active_player(self) -> Player:
        """Retourne l'objet Player dont c'est le tour."""
        return self.player1 if self.active_player_idx == 0 else self.player2

    @property
    def opponent(self) -> Player:
        """Retourne l'objet Player adverse."""
        return self.player2 if self.active_player_idx == 0 else self.player1

    @property
    def players(self) -> List[Player]:
        """Retourne la liste des deux joueurs."""
        return [self.player1, self.player2]

    def __getstate__(self):
        """
        OPTIMISATION IA : Exclut les données lourdes/inutiles lors du clonage.
        """
        state = self.__dict__.copy()
        # On supprime la référence globale aux cartes (inutile pour la simulation)
        if 'all_cards_ref' in state:
            del state['all_cards_ref']
        return state

    def __setstate__(self, state):
        """Restauration de l'état après un pickle.loads()."""
        self.__dict__.update(state)
        # On remet une liste vide par sécurité
        if not hasattr(self, 'all_cards_ref'):
            self.all_cards_ref = []

    def __repr__(self):
        return f"<GameState P{self.active_player_idx + 1} | Phase={self.phase.name} | Deck={len(self.deck)}>"
