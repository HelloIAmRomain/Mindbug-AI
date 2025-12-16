from .rules import Phase, Keyword


class Command:
    def execute(self, game):
        raise NotImplementedError


class PlayCardCommand(Command):
    def __init__(self, hand_index):
        self.index = hand_index

    def execute(self, game):
        player = game.active_player
        if not (0 <= self.index < len(player.hand)): return

        card = player.hand.pop(self.index)
        game.pending_card = card
        game.log(f"> {player.name} plays {card.name}. Mindbug check...")

        game.frenzy_candidate = None
        game.refill_hand(player)

        # On passe la main à l'adversaire pour la décision Mindbug
        game.switch_active_player()
        game.phase = Phase.MINDBUG_DECISION


class AttackCommand(Command):
    def __init__(self, board_index, target_blocker_index=-1):
        self.index = board_index
        self.target_blocker = target_blocker_index

    def execute(self, game):
        player = game.active_player
        if not (0 <= self.index < len(player.board)): return

        attacker = player.board[self.index]
        game.pending_attacker = attacker
        game.log(f"> {player.name} attacks with {attacker.name} !")

        # Règle Hunter (Chasseur)
        if Keyword.HUNTER.value in attacker.keywords and game.opponent.board:
            game.log(f"> HUNTER : Please select the opponent creature that must block.")
            game.ask_for_selection(game.opponent.board, "HUNTER_TARGET", 1, game.active_player)
            return

        # Phase de blocage normale
        game.switch_active_player()
        game.phase = Phase.BLOCK_DECISION


class BlockCommand(Command):
    def __init__(self, board_index):
        self.index = board_index

    def execute(self, game):
        player = game.active_player
        if not (0 <= self.index < len(player.board)): return

        blocker = player.board[self.index]
        game.log(f"> {player.name} blocks with {blocker.name}.")
        game.resolve_combat(blocker)


class NoBlockCommand(Command):
    def execute(self, game):
        game.log(f"> {game.active_player.name} decides not to block.")
        game.resolve_combat(None)


class MindbugCommand(Command):
    def execute(self, game):
        thief = game.active_player
        if thief.mindbugs > 0 and game.pending_card:
            thief.mindbugs -= 1
            card = game.pending_card
            game.log(f"> MINDBUG ! {thief.name} steals {card.name} !")

            # La carte est jouée chez le voleur
            game.put_card_on_board(thief, card)
            game.pending_card = None

            # Gestion des sélections (ex: Lion qui détruit une créature)
            if game.phase == Phase.RESOLUTION_CHOICE:
                game.log("   -> Turn end suspended pending selection...")
                game.mindbug_replay_pending = True
            else:
                # Si pas d'effet de sélection, on rend la main à la victime pour qu'elle rejoue
                game.execute_mindbug_replay()
        else:
            game.log("Action impossible (No Mindbugs or no pending card).")


class PassCommand(Command):
    def execute(self, game):
        game.log(f"> {game.active_player.name} declines Mindbug.")

        # On revient au joueur d'origine
        game.switch_active_player()
        owner = game.active_player
        card = game.pending_card

        if card:
            game.put_card_on_board(owner, card)
            game.pending_card = None

        if game.phase == Phase.RESOLUTION_CHOICE:
            game.log("   -> Turn end suspended pending selection...")
            game.end_turn_pending = True
        else:
            game.end_turn()


class ResolveSelectionCommand(Command):
    def __init__(self, target_type, index):
        self.target_type = target_type  # "BOARD_P1", "DISCARD_P2", etc.
        self.index = index

    def execute(self, game):
        # Récupération de la carte cible
        target_owner = game.player1 if "P1" in self.target_type else game.player2
        target_card = None

        if "BOARD" in self.target_type:
            if 0 <= self.index < len(target_owner.board):
                target_card = target_owner.board[self.index]
        elif "DISCARD" in self.target_type:
            if 0 <= self.index < len(target_owner.discard):
                target_card = target_owner.discard[self.index]
        elif "HAND" in self.target_type:
            if 0 <= self.index < len(target_owner.hand):
                target_card = target_owner.hand[self.index]

        if target_card:
            game.resolve_selection_effect(target_card)