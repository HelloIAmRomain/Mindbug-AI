from mindbug_engine.core.consts import Phase


class InputHandler:
    """
    Transforms user intent (click or drop) into engine commands.
    Stateless: It only reads the game state to determine valid actions.
    """

    @staticmethod
    def handle_card_click(game, card, is_ai_turn=False):
        """
        Returns (Action, Index) or None.
        Handles Play, Attack, Block, and Selection clicks.
        """
        if is_ai_turn:
            return None

        # Selection Phase (Effects)
        if game.state.phase == Phase.RESOLUTION_CHOICE:
            req = game.state.active_request
            if req and card in req.candidates:
                return ("RESOLVE_SELECTION", card)
            return None

        legal_moves = game.get_legal_moves()

        # Is it in my hand?
        if card in game.state.active_player.hand:
            idx = game.state.active_player.hand.index(card)
            if ("PLAY", idx) in legal_moves:
                return ("PLAY", idx)

        # Is it on my board?
        elif card in game.state.active_player.board:
            idx = game.state.active_player.board.index(card)
            if ("ATTACK", idx) in legal_moves:
                return ("ATTACK", idx)
            elif ("BLOCK", idx) in legal_moves:
                return ("BLOCK", idx)

        return None

    @staticmethod
    def handle_button_click(action_id):
        """Maps UI button IDs to engine commands."""
        mapping = {
            "CMD_PASS": ("PASS", -1),
            "CMD_MINDBUG": ("MINDBUG", -1),
            "CMD_NO_BLOCK": ("NO_BLOCK", -1)
        }
        return mapping.get(action_id, None)

    @staticmethod
    def handle_drag_drop(game, card, zone_id):
        """
        Interprets a card drop on a specific zone.
        Returns the command to execute or None.
        """
        if not zone_id:
            return None

        legal_moves = game.get_legal_moves()
        ap = game.state.active_player
        is_p1 = (ap == game.state.player1)

        # Determine logical zones relative to active player
        my_board_zone = "BOARD_P1" if is_p1 else "BOARD_P2"
        opp_board_zone = "BOARD_P2" if is_p1 else "BOARD_P1"

        # 1. PLAY Action (Hand -> Board)
        if card in ap.hand:
            try:
                idx = ap.hand.index(card)
                # Accept drop on OWN board or generic PLAY_AREA
                if zone_id in [my_board_zone, "PLAY_AREA"]:
                    if ("PLAY", idx) in legal_moves:
                        return ("PLAY", idx)
            except ValueError:
                pass

        # 2. BOARD Actions (Attack / Block)
        elif card in ap.board:
            try:
                idx = ap.board.index(card)

                # ATTACK (To enemy board or center)
                if zone_id in [opp_board_zone, "PLAY_AREA"]:
                    if ("ATTACK", idx) in legal_moves:
                        return ("ATTACK", idx)

                # BLOCK (To center)
                if zone_id == "PLAY_AREA":
                    if ("BLOCK", idx) in legal_moves:
                        return ("BLOCK", idx)
            except ValueError:
                pass

        # 3. SELECTION Action (Effects)
        if game.state.phase == Phase.RESOLUTION_CHOICE:
            # If dragging a valid candidate anywhere on the board
            if zone_id in ["BOARD_P1", "BOARD_P2", "PLAY_AREA"]:
                return ("RESOLVE_SELECTION", card)

        return None

    @staticmethod
    def get_valid_drop_zones(game, card) -> list[str]:
        """
        Returns a list of Zone IDs where the given card can be legally dropped.
        Used for visual highlighting.
        """
        valid_zones = []
        moves = game.get_legal_moves()
        ap = game.state.active_player
        is_p1 = (ap == game.state.player1)

        my_board = "BOARD_P1" if is_p1 else "BOARD_P2"
        opp_board = "BOARD_P2" if is_p1 else "BOARD_P1"

        # 1. From Hand (PLAY)
        if card in ap.hand:
            try:
                idx = ap.hand.index(card)
                if ("PLAY", idx) in moves:
                    valid_zones.append(my_board)
                    valid_zones.append("PLAY_AREA")
            except ValueError:
                pass

        # 2. From Board (ATTACK / BLOCK)
        elif card in ap.board:
            try:
                idx = ap.board.index(card)
                if ("ATTACK", idx) in moves:
                    valid_zones.append(opp_board)
                    valid_zones.append("PLAY_AREA")
                if ("BLOCK", idx) in moves:
                    valid_zones.append("PLAY_AREA")
            except ValueError:
                pass

        return list(set(valid_zones))
