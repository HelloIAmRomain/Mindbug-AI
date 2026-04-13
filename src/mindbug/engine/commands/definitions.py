from dataclasses import dataclass
from typing import Any
from functools import partial
from mindbug.engine.commands.command import Command
from mindbug.engine.core.consts import Phase, Trigger, Keyword
from mindbug.engine.utils.logger import log_info, log_error


class ConfirmInitiativeCommand(Command):
    """
    Commande déclenchée par le joueur pour passer à l'étape suivante 
    de la bataille d'initiative (Résolution ou Re-pioche).
    """

    def execute(self, game):
        game.resolve_initiative_step()


class PlayCardCommand(Command):
    """
    Joue une carte de la main.
    Initie la phase de Mindbug.
    """

    def __init__(self, card_index: int):
        self.card_index = card_index

    def execute(self, game):
        player = game.state.active_player

        # Validation
        if not (0 <= self.card_index < len(player.hand)):
            log_error(f"❌ Invalid card index: {self.card_index}")
            return

        # 1. On retire la carte
        card = player.hand.pop(self.card_index)
        game.state.pending_card = card

        log_info(f"> {player.name} plays {card.name}. Mindbug check...")

        # Reset états
        game.state.frenzy_candidate = None
        game.state.pending_attacker = None

        # 2. Transition Mindbug
        if game.state.opponent.mindbugs > 0:
            # Cas normal : On donne la main à l'adversaire pour qu'il décide
            game.turn_manager.switch_active_player()
            game.state.phase = Phase.MINDBUG_DECISION
        else:
            # Cas "Auto-Pass" (0 Mindbugs restants)
            game.turn_manager.switch_active_player()
            pass_cmd = PassCommand()
            pass_cmd.execute(game)


@dataclass
class AttackCommand(Command):
    attacker_index: int

    def execute(self, game):
        ap = game.state.active_player
        opp = game.state.player2 if ap == game.state.player1 else game.state.player1

        if not (0 <= self.attacker_index < len(ap.board)):
            log_error(f"❌ Invalid attacker index {self.attacker_index}")
            return

        attacker = ap.board[self.attacker_index]
        game.state.pending_attacker = attacker

        log_info(f"> ⚔️ {ap.name} declares attack with {attacker.name} !")

        # 2. Trigger ON_ATTACK
        if attacker.trigger == Trigger.ON_ATTACK:
            log_info(f"⚡ Trigger ON_ATTACK activated for {attacker.name}")
            game.effect_manager.apply_effect(attacker, ap, opp)
            if game.state.phase == Phase.RESOLUTION_CHOICE:
                # Si l'attaquant a aussi HUNTER, il devra se déclencher après la sélection
                if Keyword.HUNTER in attacker.keywords and len(opp.board) > 0:
                    game.state.hunter_pending = True
                return

        # 3. Gestion HUNTER (Chasseur)
        has_targets = len(opp.board) > 0
        if Keyword.HUNTER in attacker.keywords and has_targets:
            log_info(f"> 🏹 HUNTER triggers : {ap.name} chooses the blocker.")

            # Utilisation de partial et méthode statique pour être "Picklable"
            callback = partial(self._on_hunter_target_selected, game)

            # On injecte l'option spéciale "NO_HUNT" dans les choix possibles
            candidates = list(opp.board)
            candidates.append("NO_HUNT")

            game.ask_for_selection(
                candidates=candidates,
                reason="HUNTER_TARGET",
                count=1,
                selector=ap,
                callback=callback
            )
            return

        # 4. Transition standard
        game.state.phase = Phase.BLOCK_DECISION
        game.turn_manager.switch_active_player()

    @staticmethod
    def _on_hunter_target_selected(game, selection):
        """Callback exécuté quand le joueur a choisi sa cible Hunter."""
        target = selection[0]

        # OPTION A : Le joueur a cliqué "Attaque Normale" (Skip Hunter)
        if target == "NO_HUNT":
            log_info("   -> Hunter ability skipped (Standard Attack).")
            game.state.phase = Phase.BLOCK_DECISION
            game.turn_manager.switch_active_player()
            return

        # OPTION B : Le joueur a choisi une cible
        log_info(f"   -> Hunter targeted {target.name}")

        # On switch manuellement vers le défenseur AVANT de résoudre le combat.
        game.turn_manager.switch_active_player()

        # On force la phase pour sortir de RESOLUTION_CHOICE
        game.state.phase = Phase.BLOCK_DECISION

        # Résolution immédiate
        game.resolve_combat(blocker=target)


class BlockCommand(Command):
    """
    Déclare un bloqueur en réponse à une attaque.
    """

    def __init__(self, blocker_index: int):
        self.blocker_index = blocker_index

    def execute(self, game):
        player = game.state.active_player

        if not (0 <= self.blocker_index < len(player.board)):
            log_error(f"❌ Invalid blocker index {self.blocker_index}")
            return

        blocker = player.board[self.blocker_index]
        log_info(f"> {player.name} blocks with {blocker.name}.")

        # Délégation au moteur de combat
        game.resolve_combat(blocker)


class NoBlockCommand(Command):
    """
    Refuse de bloquer (encaisse les dégâts).
    """

    def execute(self, game):
        log_info(f"> {game.state.active_player.name} decides not to block.")
        # Combat contre "Rien" (Attaque directe)
        game.resolve_combat(None)


class MindbugCommand(Command):
    """
    Utilise un Mindbug pour voler la carte jouée.
    """

    def execute(self, game):
        # C'est celui qui joue le Mindbug (donc l'adversaire de celui qui a posé)
        thief = game.state.active_player

        if thief.mindbugs > 0 and game.state.pending_card:
            thief.mindbugs -= 1
            card = game.state.pending_card

            log_info(f"> MINDBUG ! {thief.name} steals {card.name} !")

            # 1. Le voleur pose la carte chez lui (Trigger ON_PLAY activés pour le voleur)
            game.put_card_on_board(thief, card)
            game.state.pending_card = None

            # 2. Gestion du "Replay" (Le joueur initial rejoue un tour complet)
            if game.state.phase == Phase.RESOLUTION_CHOICE:
                log_info("   -> Turn end suspended pending selection...")
                game.state.mindbug_replay_pending = True
            else:
                game.execute_mindbug_replay()
        else:
            log_error("❌ Illegal Mindbug attempt")


class PassCommand(Command):
    """
    Refuse d'utiliser un Mindbug. La carte revient à son propriétaire initial.
    """

    def execute(self, game):
        log_info(f"> {game.state.active_player.name} declines Mindbug.")

        # On redonne la main au joueur initial (celui qui a joué la carte)
        game.turn_manager.switch_active_player()

        original_owner = game.state.active_player
        card = game.state.pending_card

        if card:
            # La carte arrive enfin sur le plateau du propriétaire
            game.put_card_on_board(original_owner, card)
            game.state.pending_card = None

        # Gestion fin de tour
        if game.state.phase == Phase.RESOLUTION_CHOICE:
            log_info("   -> Turn end suspended pending selection...")
            game.state.end_turn_pending = True
        else:
            game.turn_manager.end_turn()


class ResolveSelectionCommand(Command):
    """
    Commande spéciale générée par l'UI quand un joueur clique sur une cible.
    """

    def __init__(self, selected_object: Any, **kwargs):
        self.selected_object = selected_object

    def execute(self, game):
        game.resolve_selection_effect(self.selected_object)
