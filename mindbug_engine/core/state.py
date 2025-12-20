from typing import List, Optional, Any
from mindbug_engine.core.models import Player, Card, SelectionRequest
from mindbug_engine.core.consts import Phase


class GameState:
    """
    Contient TOUTES les données mutables du jeu.
    C'est la 'Vérité' de la partie à un instant T.
    Il ne contient aucune logique, seulement des données.
    """

    def __init__(self, deck: List[Card], player1: Player, player2: Player):
        # --- DONNÉES PRINCIPALES ---
        self.deck = deck
        self.player1 = player1
        self.player2 = player2

        # Référence de toutes les cartes possibles dans ce match (Pool complet)
        self.all_cards_ref: List[Card] = []

        # --- ÉTAT DU TOUR ---
        self.turn_count = 1
        self.active_player_idx = 0  # 0 = Player1, 1 = Player2
        self.phase = Phase.P1_MAIN

        # Gagnant de la partie (None tant que la partie est en cours)
        self.winner: Any = None

        # --- ÉTATS TRANSITOIRES (Machine à états) ---

        # Carte qui vient d'être jouée (en attente de décision Mindbug)
        # C'est cet attribut qui manquait !
        self.pending_card: Optional[Card] = None

        # Créature qui déclare une attaque (attente de blocage)
        self.pending_attacker: Optional[Card] = None

        # Créature sous effet Fureur (doit rejouer immédiatement)
        self.frenzy_candidate: Optional[Card] = None

        # --- INTERRUPTIONS & FLUX ---

        # Demande de sélection active (ex: "Choisir une carte à défausser")
        self.active_request: Optional[SelectionRequest] = None

        # Flags de contrôle de flux
        self.mindbug_replay_pending = False  # P1 doit rejouer après s'être fait voler ?
        self.end_turn_pending = False  # Fin de tour en attente de résolution ?

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

    def __repr__(self):
        return f"<GameState P{self.active_player_idx + 1} | Phase={self.phase.name} | Deck={len(self.deck)}>"