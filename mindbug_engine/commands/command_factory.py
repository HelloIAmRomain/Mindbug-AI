from typing import Optional
from mindbug_engine.commands.definitions import (
    PlayCardCommand, AttackCommand, BlockCommand,
    NoBlockCommand, MindbugCommand, PassCommand, ResolveSelectionCommand
)
from mindbug_engine.core.consts import Phase
from mindbug_engine.utils.logger import log_error


class CommandFactory:
    """
    Factory Pattern Stricte.
    Ne gère que les actions définies par engine.get_legal_moves().
    """

    @staticmethod
    def create(action_type: str, index: int, game) -> Optional[object]:

        if action_type == "PLAY":
            return PlayCardCommand(card_index=index)

        elif action_type == "ATTACK":
            return AttackCommand(attacker_index=index)

        elif action_type == "BLOCK":
            return BlockCommand(blocker_index=index)

        elif action_type == "NO_BLOCK":
            return NoBlockCommand()

        elif action_type == "MINDBUG":
            return MindbugCommand()

        elif action_type == "PASS":
            return PassCommand()

        elif action_type == "CONFIRM_INITIATIVE":
            from mindbug_engine.commands.definitions import ConfirmInitiativeCommand
            return ConfirmInitiativeCommand()

        # Commandes de sélection
        if action_type.startswith("SELECT_"):
            target = CommandFactory._resolve_target(action_type, index, game)
            if target:
                from mindbug_engine.commands.definitions import ResolveSelectionCommand
                return ResolveSelectionCommand(selected_object=target)
            else:
                log_error(
                    f"❌ Factory: Target not found for {action_type} [{index}]")
                return None
        return None

    @staticmethod
    def _resolve_target(action_type: str, index: int, game):
        """Résolution des cibles relatives au SÉLECTEUR."""

        # 1. DÉFINITION DU POINT DE VUE (Qui clique ?)
        if game.state.phase == Phase.RESOLUTION_CHOICE and game.state.active_request:
            # En phase de sélection, le référentiel est celui qui doit choisir
            me = game.state.active_request.selector
        else:
            # Sinon, c'est le joueur actif
            me = game.state.active_player

        # Déduction de l'adversaire relatif
        opp = game.state.player2 if me == game.state.player1 else game.state.player1

        try:
            # 2. RÉSOLUTION RELATIVE
            # "Mon" jeu
            if action_type == "SELECT_HAND":
                return me.hand[index]
            if action_type == "SELECT_BOARD":
                return me.board[index]
            if action_type == "SELECT_DISCARD":
                return me.discard[index]

            # Jeu "Adverse"
            if action_type == "SELECT_OPP_HAND":
                return opp.hand[index]
            if action_type == "SELECT_OPP_BOARD":
                return opp.board[index]
            if action_type == "SELECT_OPP_DISCARD":
                return opp.discard[index]

        except IndexError:
            return None
        return None
