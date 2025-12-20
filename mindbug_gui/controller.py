from mindbug_engine.core.consts import Phase


class InputHandler:
    """
    Transforme une intention utilisateur (clic sur un objet) en commande moteur.
    Aucune notion de pixels ici.
    """

    @staticmethod
    def handle_card_click(game, card, is_ai_turn=False):
        """
        Retourne le tuple (Action, Index) ou None si le clic est invalide.
        """
        # 1. Sécurité
        if is_ai_turn:
            return None

        # 2. Phase de Sélection (Effets V2)
        if game.state.phase == Phase.RESOLUTION_CHOICE:
            # Ici on retourne l'objet directement car l'Engine V2 le gère
            # On encapsule ça dans une commande spéciale pour l'UI
            return ("RESOLVE_SELECTION", card)

        legal_moves = game.get_legal_moves()

        # 3. Logique de mapping (Carte -> Index)

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