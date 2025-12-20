from mindbug_engine.core.consts import Phase


class InputHandler:
    """
    Transforme une intention utilisateur (clic ou drop) en commande moteur.
    Gère dynamiquement les zones selon le joueur actif (P1 ou P2).
    """

    @staticmethod
    def handle_card_click(game, card, is_ai_turn=False):
        """
        Retourne le tuple (Action, Index) ou None si le clic est invalide.
        (Fallback pour le clic simple)
        """
        if is_ai_turn:
            return None

        # Phase de Sélection (Effets V2)
        if game.state.phase == Phase.RESOLUTION_CHOICE:
            return ("RESOLVE_SELECTION", card)

        legal_moves = game.get_legal_moves()

        # Est-ce dans ma main ?
        if card in game.state.active_player.hand:
            idx = game.state.active_player.hand.index(card)
            if ("PLAY", idx) in legal_moves:
                return ("PLAY", idx)

        # Est-ce sur mon board ?
        elif card in game.state.active_player.board:
            idx = game.state.active_player.board.index(card)
            if ("ATTACK", idx) in legal_moves:
                return ("ATTACK", idx)
            elif ("BLOCK", idx) in legal_moves:
                return ("BLOCK", idx)

        return None

    @staticmethod
    def handle_button_click(action_id):
        """Traduit les IDs de boutons en commandes moteur."""
        mapping = {
            "CMD_PASS": ("PASS", -1),
            "CMD_MINDBUG": ("MINDBUG", -1),
            "CMD_NO_BLOCK": ("NO_BLOCK", -1)
        }
        return mapping.get(action_id, None)

    @staticmethod
    def handle_drag_drop(game, card, zone_id):
        """
        Interprète un lâcher de carte sur une zone spécifique.
        Rend la logique symétrique pour P1 et P2.
        """
        if not zone_id: return None

        legal_moves = game.get_legal_moves()
        ap = game.state.active_player

        # Si c'est P1 : Son plateau = BOARD_P1, Ennemi = BOARD_P2
        # Si c'est P2 : Son plateau = BOARD_P2, Ennemi = BOARD_P1
        is_p1 = (ap == game.state.player1)

        my_board_zone = "BOARD_P1" if is_p1 else "BOARD_P2"
        opp_board_zone = "BOARD_P2" if is_p1 else "BOARD_P1"

        # 1. Action JOUER (Main -> Mon Plateau)
        if card in ap.hand:
            try:
                idx = ap.hand.index(card)
                # On accepte le drop sur SON plateau ou au milieu
                if zone_id in [my_board_zone, "PLAY_AREA"]:
                    if ("PLAY", idx) in legal_moves:
                        return ("PLAY", idx)
            except ValueError:
                pass

        # 2. Action ATTAQUER ou BLOQUER (Mon Plateau -> ...)
        elif card in ap.board:
            try:
                idx = ap.board.index(card)

                # ATTAQUER (Vers l'ennemi ou le centre)
                if zone_id in [opp_board_zone, "PLAY_AREA"]:
                    if ("ATTACK", idx) in legal_moves:
                        return ("ATTACK", idx)

                # BLOQUER (Au centre, pour intercepter)
                # Note : On autorise aussi le drop sur la zone attaquante pour être intuitif
                if zone_id == "PLAY_AREA":
                    if ("BLOCK", idx) in legal_moves:
                        return ("BLOCK", idx)
            except ValueError:
                pass

        # 4. Action SÉLECTION (Effets)
        if game.state.phase == Phase.RESOLUTION_CHOICE:
            # Si on lâche une carte valide n'importe où sur le plateau de jeu
            if zone_id in ["BOARD_P1", "BOARD_P2", "PLAY_AREA"]:
                return ("RESOLVE_SELECTION", card)

        return None