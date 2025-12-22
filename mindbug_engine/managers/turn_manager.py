from mindbug_engine.core.consts import Phase
from mindbug_engine.utils.logger import log_info, log_debug


class TurnManager:
    """
    Gère le flux temporel du jeu : Tours, Phases, Conditions de victoire.
    Aligné Architecture V3 (Reçoit 'game' en dépendance).
    """

    def __init__(self, game):
        # On accepte 'game' (la façade), pas juste 'state'.
        self.game = game
        self.state = game.state

    def start_turn(self):
        """
        Initialise le premier tour.
        Appelé par MindbugGame.start_game().
        """
        self.state.turn_count = 1
        self.state.phase = Phase.P1_MAIN
        # Note : La distribution initiale des cartes est faite par l'Engine avant cet appel.

    def switch_active_player(self):
        """Bascule le joueur actif (0 <-> 1)."""
        old_name = self.state.active_player.name
        self.state.active_player_idx = 1 - self.state.active_player_idx
        log_info(
            f"🔄 Switch Player : {old_name} -> {self.state.active_player.name}")

    def refill_hand(self, player):
        """
        Complète la main du joueur jusqu'à 5 cartes en piochant dans SA pioche.
        """
        while len(player.hand) < 5 and len(player.deck) > 0:
            card = player.deck.pop()
            player.hand.append(card)
            # log_debug(f"   -> {player.name} draws a card.")

    def end_turn(self):
        """
        Gère la fin de tour standard :
        1. Vérification victoire
        2. Pioche (Refill)
        3. Changement de joueur
        4. Changement de phase
        """
        # 1. Victoire
        self.check_win_condition()
        if self.state.winner:
            return

        # 2. Pioche
        self.refill_hand(self.state.player1)
        self.refill_hand(self.state.player2)

        # 3. Changement Joueur
        self.switch_active_player()

        # 4. Mise à jour de la phase pour le nouveau joueur
        # Si c'était P1, c'est maintenant P2 -> P2_MAIN
        new_phase = Phase.P1_MAIN if self.state.active_player_idx == 0 else Phase.P2_MAIN
        self.state.phase = new_phase

        # Incrément du compteur global (Optionnel, ou tous les 2 tours)
        self.state.turn_count += 1

        log_info(f"--- Turn end. Turn of {self.state.active_player.name} ---")

    def check_win_condition(self):
        """Vérifie si un joueur a perdu (PV <= 0)."""
        if self.state.winner:
            return  # Déjà gagné

        if self.state.player1.hp <= 0:
            self.state.winner = self.state.player2
            self.state.phase = Phase.GAME_OVER
            log_info(
                f"🏆 VICTOIRE : {self.state.player2.name} gagne la partie !")

        elif self.state.player2.hp <= 0:
            self.state.winner = self.state.player1
            self.state.phase = Phase.GAME_OVER
            log_info(
                f"🏆 VICTOIRE : {self.state.player1.name} gagne la partie !")
