import random
import sys
import os
from typing import Optional, List, Tuple
from .models import Card, Player, CardLoader
from .rules import Phase, Keyword, CombatUtils
from .effects import EffectManager

# --- FONCTION HELPER POUR PYINSTALLER ---
def resource_path(relative_path):
    """
    Obtient le chemin absolu vers la ressource.
    Fonctionne pour le développement (local) et pour PyInstaller (exe).
    """
    try:
        # PyInstaller crée un dossier temporaire et stocke le chemin dans _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class MindbugGame:
    def __init__(self, deck_path=None):
        # Si aucun chemin n'est fourni, on utilise le chemin "intelligent"
        if deck_path is None:
            deck_path = resource_path(os.path.join("data", "cards.json"))

        # 1. Chargement du Deck
        loaded_cards = CardLoader.load_deck(deck_path)
        self.all_cards_ref = list(loaded_cards) 
        self.full_deck = list(loaded_cards)
        random.shuffle(self.full_deck)
        
        self.player1 = Player(name="P1")
        self.player2 = Player(name="P2")
        self.players = [self.player1, self.player2]
        
        self._setup_player(self.player1)
        self._setup_player(self.player2)
        
        self.active_player_idx = 0 
        self.phase = Phase.P1_MAIN
        self.turn_count = 1
        self.winner = None
        
        self.pending_card: Optional[Card] = None      
        self.pending_attacker: Optional[Card] = None 
        self.selection_context = None

        self.end_turn_pending = False       
        self.mindbug_replay_pending = False
        self.frenzy_candidate = None 
    
    def _setup_player(self, player):
        for _ in range(5):
             if self.full_deck: player.hand.append(self.full_deck.pop())
        for _ in range(5):
             if self.full_deck: player.deck.append(self.full_deck.pop())
        self.refill_hand(player)

    def refill_hand(self, player):
        while len(player.hand) < 5 and len(player.deck) > 0:
            card = player.deck.pop()
            player.hand.append(card)

    @property
    def active_player(self):
        return self.players[self.active_player_idx]

    @property
    def opponent(self):
        return self.players[1 - self.active_player_idx]

    # --- CALCUL DE PUISSANCE ---
    def calculate_real_power(self, card: Card) -> int:
        current = card.power
        turn_owner = self.active_player
        if self.phase in [Phase.BLOCK_DECISION, Phase.MINDBUG_DECISION]:
            turn_owner = self.opponent
            
        card_owner = self.player1 if card in self.player1.board else self.player2
        board = card_owner.board
        is_my_turn = (card_owner == turn_owner)

        # 1. Bonus Alliés
        for ally in board:
            if ally == card: continue
            if ally.ability and ally.trigger == "PASSIVE" and ally.ability.code == "BOOST_ALLIES":
                current += ally.ability.value

        # 2. Bonus tour
        if card.ability and card.trigger == "PASSIVE" and card.ability.code == "BOOST_IF_MY_TURN":
             if is_my_turn: current += card.ability.value

        # 3. Bonus Alliés tour (Oursins - CORRIGÉ: Exclure soi-même si demandé)
        for ally in board:
            if ally == card: continue # <--- CORRECTION BUG OURSIN (ne se buff pas lui-même)
            if ally.ability and ally.trigger == "PASSIVE" and ally.ability.code == "BOOST_ALLIES_IF_MY_TURN":
                if is_my_turn: current += ally.ability.value
        
        # 4. Yeti
        if card.ability and card.trigger == "PASSIVE" and card.ability.code == "BOOST_AND_FRENZY_IF_ALONE":
            if len(board) == 1: current += card.ability.value
        
        # 5. Debuff Ennemis
        opp_board = self.player2.board if card_owner == self.player1 else self.player1.board
        for enemy in opp_board:
            if enemy.ability and enemy.trigger == "PASSIVE" and enemy.ability.code == "DEBUFF_ENEMIES":
                current += enemy.ability.value

        return max(0, current)

    def update_board_states(self):
        for player in [self.player1, self.player2]:
            opponent = self.player2 if player == self.player1 else self.player1
            enemy_keywords = set()
            for card in opponent.board:
                enemy_keywords.update(card.keywords)
                
            for card in player.board:
                if card.ability and card.trigger == "PASSIVE" and card.ability.code == "COPY_ALL_KEYWORDS_FROM_ENEMIES":
                    target_keywords = ["HUNTER", "SNEAKY", "POISON", "FRENZY", "TOUGH"]
                    for kw in target_keywords:
                        if kw in enemy_keywords:
                            if kw not in card.keywords: card.keywords.append(kw)
                        else:
                            if kw in card.keywords: card.keywords.remove(kw)

    def get_legal_moves(self) -> List[Tuple[str, int]]:
        self.update_board_states()
        moves = []
        player = self.active_player
        
        if self.winner: return []

        if self.phase in [Phase.P1_MAIN, Phase.P2_MAIN]:
            # Si Furie active, on doit attaquer avec la carte Furie
            if self.frenzy_candidate:
                if self.frenzy_candidate in player.board:
                    idx = player.board.index(self.frenzy_candidate)
                    moves.append(("ATTACK", idx))
                # On autorise quand même de jouer une carte à la place ? 
                # Dans le doute, on laisse l'option de jouer (stratégique).
                for i in range(len(player.hand)): moves.append(("PLAY", i))
            else:
                # Cas normal
                for i in range(len(player.hand)): moves.append(("PLAY", i))
                for i in range(len(player.board)): moves.append(("ATTACK", i))

        elif self.phase == Phase.MINDBUG_DECISION:
            moves.append(("PASS", -1))
            if player.mindbugs > 0: moves.append(("MINDBUG", -1))

        elif self.phase == Phase.BLOCK_DECISION:
            moves.append(("NO_BLOCK", -1))
            attacker = self.pending_attacker
            if attacker:
                for i, blocker in enumerate(player.board):
                    if CombatUtils.can_block(attacker, blocker):
                        moves.append(("BLOCK", i))

        elif self.phase == Phase.RESOLUTION_CHOICE:
            if self.selection_context:
                candidates = self.selection_context["candidates"]
                for i, card in enumerate(self.player1.board):
                    if card in candidates: moves.append(("SELECT_BOARD_P1", i))
                for i, card in enumerate(self.player2.board):
                    if card in candidates: moves.append(("SELECT_BOARD_P2", i))
                for i, card in enumerate(self.player1.discard):
                    if card in candidates: moves.append(("SELECT_DISCARD_P1", i))
                for i, card in enumerate(self.player2.discard):
                    if card in candidates: moves.append(("SELECT_DISCARD_P2", i))

        return moves

    def step(self, action_type: str, target_idx: int = -1, target_blocker_idx: int = -1):
        if self.winner: return
        self.update_board_states()

        if self.phase in [Phase.P1_MAIN, Phase.P2_MAIN]:
            if action_type == "PLAY": self._action_play_card(target_idx)
            elif action_type == "ATTACK": self._action_declare_attack(target_idx, target_blocker_idx)
        
        elif self.phase == Phase.MINDBUG_DECISION:
            if action_type == "MINDBUG": self._action_use_mindbug()
            elif action_type == "PASS": self._action_pass_mindbug()

        elif self.phase == Phase.BLOCK_DECISION:
            if action_type == "BLOCK": self._action_block(target_idx)
            elif action_type == "NO_BLOCK": self._resolve_combat(blocker=None)

        elif self.phase == Phase.RESOLUTION_CHOICE:
            if action_type.startswith("SELECT_BOARD") or action_type.startswith("SELECT_DISCARD"):
                target_owner = self.player1 if "P1" in action_type else self.player2
                if "BOARD" in action_type:
                    if 0 <= target_idx < len(target_owner.board):
                        self._action_resolve_selection(target_owner.board[target_idx])
                elif "DISCARD" in action_type:
                    if 0 <= target_idx < len(target_owner.discard):
                        self._action_resolve_selection(target_owner.discard[target_idx])

        self._check_win_condition()
        self.refill_hand(self.player1)
        self.refill_hand(self.player2)

    def ask_for_selection(self, candidates: List[Card], effect_code: str, count: int, initiator: Player):
        if not candidates:
            print("   -> Aucune cible disponible (Sélection annulée).")
            return

        print(f"⌛ EN ATTENTE : {initiator.name} doit choisir une cible pour {effect_code}.")
        self.selection_context = {
            "candidates": candidates,
            "effect_code": effect_code,
            "count": count,
            "initiator": initiator
        }
        self.phase = Phase.RESOLUTION_CHOICE

    def _action_play_card(self, hand_idx):
        if not (0 <= hand_idx < len(self.active_player.hand)): return
        card = self.active_player.hand.pop(hand_idx)
        self.pending_card = card
        print(f"> Pose {card.name}. Mindbug ?")
        
        self.frenzy_candidate = None 
        self.refill_hand(self.active_player)
        self._switch_active_player() 
        self.phase = Phase.MINDBUG_DECISION

    def _action_use_mindbug(self):
        thief = self.active_player
        if thief.mindbugs > 0:
            thief.mindbugs -= 1
            print(f"> MINDBUG ! {thief.name} vole {self.pending_card.name} !")
            self._put_card_on_board(thief, self.pending_card)
            self.pending_card = None
            
            if self.phase == Phase.RESOLUTION_CHOICE:
                print("   -> Fin de tour Mindbug suspendue en attente de sélection...")
                self.mindbug_replay_pending = True
            else:
                self._execute_mindbug_replay()
        else:
            print("Action impossible.")

    def _execute_mindbug_replay(self):
        self._switch_active_player() 
        print(f"> Le tour revient à {self.active_player.name} (Rejoue son tour).")
        self.phase = Phase.P1_MAIN if self.active_player_idx == 0 else Phase.P2_MAIN

    def _action_pass_mindbug(self):
        print("> Refus du Mindbug.")
        self._switch_active_player()
        owner = self.active_player
        self._put_card_on_board(owner, self.pending_card)
        self.pending_card = None
        
        if self.phase == Phase.RESOLUTION_CHOICE:
            print("   -> Fin de tour suspendue en attente de sélection...")
            self.end_turn_pending = True
        else:
            self._end_turn()

    def _action_declare_attack(self, board_idx, target_blocker_idx=-1):
        if not (0 <= board_idx < len(self.active_player.board)): return
        attacker = self.active_player.board[board_idx]
        self.pending_attacker = attacker
        print(f"> Attaque avec {attacker.name} !")

        if Keyword.HUNTER.value in attacker.keywords and self.opponent.board:
            print(f"> CHASSEUR : Veuillez sélectionner la créature adverse qui doit bloquer.")
            self.ask_for_selection(self.opponent.board, "HUNTER_TARGET", 1, self.active_player)
            return

        self._switch_active_player()
        self.phase = Phase.BLOCK_DECISION

    def _action_block(self, blocker_idx):
        if not (0 <= blocker_idx < len(self.active_player.board)): return
        blocker = self.active_player.board[blocker_idx]
        attacker = self.pending_attacker
        if not CombatUtils.can_block(attacker, blocker):
            self._resolve_combat(None) 
            return
        print(f"> Bloque avec {blocker.name}.")
        self._resolve_combat(blocker)

    def _resolve_combat(self, blocker: Optional[Card]):
        attacker = self.pending_attacker
        attacker_owner = self.player1 if attacker in self.player1.board else self.player2
        defender_owner = self.player2 if attacker_owner == self.player1 else self.player1

        # 1. Calcul des puissances réelles (incluant bonus passifs)
        att_power = self.calculate_real_power(attacker)
        
        if blocker is None:
            print(f"> Pas de blocage ! {defender_owner.name} perd 1 PV.")
            defender_owner.hp -= 1
        else:
            blk_power = self.calculate_real_power(blocker)
            print(f"> Combat : {attacker.name} ({att_power}) vs {blocker.name} ({blk_power})")
            
            att_dead, blk_dead = CombatUtils.simulate_combat(attacker, blocker)
            
            # Gestion Poison (Check des keywords dynamiques si besoin, ici keywords de base)
            # Note: Si Requin Crabe a poison dynamiquement, assurez-vous que attacker.keywords est à jour
            if Keyword.POISON.value in attacker.keywords: blk_dead = True
            if Keyword.POISON.value in blocker.keywords: att_dead = True

            # Application des dégâts / Morts
            if att_dead: self._apply_lethal_damage(attacker, attacker_owner)
            if blk_dead: self._apply_lethal_damage(blocker, defender_owner)

        self.pending_attacker = None
        
        # --- CORRECTIF CRITIQUE : INTERRUPTION SUR MORT ---
        # Si un Crapaud Bombe est mort, le jeu est passé en RESOLUTION_CHOICE.
        # Il faut arrêter la fonction ICI pour ne pas écraser l'état.
        if self.phase == Phase.RESOLUTION_CHOICE:
            print("   -> Fin de combat suspendue en attente de sélection (Effet de mort)...")
            self.end_turn_pending = True
            return 
        # --------------------------------------------------

        # --- GESTION FURIE ---
        # On vérifie si l'attaquant est toujours vivant sur le plateau
        survived = (attacker in attacker_owner.board)
        has_frenzy = Keyword.FRENZY.value in attacker.keywords
        is_bonus_attack = (self.frenzy_candidate == attacker)
        
        # Reset par défaut pour ne pas bloquer les tours suivants
        self.frenzy_candidate = None
        
        if survived and has_frenzy and not is_bonus_attack:
            print(f"> FURIE ! {attacker.name} peut attaquer une seconde fois.")
            self.frenzy_candidate = attacker
            # Rendre la main a l'attaquant
            self._switch_active_player()

            # On force le maintien du tour
            if self.active_player_idx == 0: self.phase = Phase.P1_MAIN
            else: self.phase = Phase.P2_MAIN
            
            return # <-- STOP : On ne finit pas le tour !

        # Fin de tour classique
        next_player = defender_owner
        self.active_player_idx = 0 if next_player == self.player1 else 1
        self.phase = Phase.P1_MAIN if self.active_player_idx == 0 else Phase.P2_MAIN
        self.turn_count += 1
        print(f"--- Fin du tour. Au tour de {self.active_player.name} ---")

    def _action_resolve_selection(self, selected_card: Card):
        ctx = self.selection_context
        if not ctx: return

        effect = ctx["effect_code"]
        initiator = ctx["initiator"]
        print(f"> Cible choisie : {selected_card.name}")

        if effect == "DESTROY_CREATURE" or effect == "DESTROY_IF_FEWER_ALLIES":
            victim = self.player1 if selected_card in self.player1.board else self.player2
            print(f"   -> {selected_card.name} est détruit.")
            self._destroy_card(selected_card, victim)
        
        elif effect == "STEAL_CREATURE":
            victim = self.player1 if selected_card in self.player1.board else self.player2
            if selected_card in victim.board:
                victim.board.remove(selected_card)
                initiator.board.append(selected_card)
                print(f"   -> {initiator.name} vole {selected_card.name}.")
        
        elif effect == "HUNTER_TARGET":
            print(f"   -> {initiator.name} force {selected_card.name} à bloquer !")
            self.selection_context = None
            
            # --- CRITIQUE : RÉINITIALISER LA PHASE AVANT LE COMBAT ---
            # Si on laisse RESOLUTION_CHOICE, _resolve_combat va croire à une interruption
            if self.active_player_idx == 0: self.phase = Phase.P1_MAIN
            else: self.phase = Phase.P2_MAIN
            
            self._resolve_combat(selected_card)
            return

        elif effect == "RECLAIM_DISCARD":
            owner = self.player1 if selected_card in self.player1.discard else self.player2
            if selected_card in owner.discard:
                owner.discard.remove(selected_card)
                initiator.hand.append(selected_card)
                selected_card.reset()
                print(f"   -> {initiator.name} récupère {selected_card.name}.")
                
        elif effect == "PLAY_FROM_OPP_DISCARD" or effect == "PLAY_FROM_MY_DISCARD":
            owner = self.player1 if selected_card in self.player1.discard else self.player2
            if selected_card in owner.discard:
                owner.discard.remove(selected_card)
                print(f"   -> {initiator.name} joue {selected_card.name} depuis la défausse !")
                self._put_card_on_board(initiator, selected_card)
                selected_card.reset()

        ctx["count"] -= 1
        if ctx["count"] <= 0:
            print("   -> Fin de la sélection.")
            self.selection_context = None
            if self.mindbug_replay_pending:
                self.mindbug_replay_pending = False
                self._execute_mindbug_replay()
            elif self.end_turn_pending:
                self.end_turn_pending = False
                self._end_turn()
            else:
                if self.active_player_idx == 0: self.phase = Phase.P1_MAIN
                else: self.phase = Phase.P2_MAIN
        else:
            print(f"   -> Encore {ctx['count']} cible(s) à choisir...")

    def _apply_lethal_damage(self, card: Card, owner: Player):
        if Keyword.TOUGH.value in card.keywords and not card.is_damaged:
            print(f"> {card.name} est CORIACE ! Il survit.")
            card.is_damaged = True
        else:
            print(f"> {card.name} est détruit.")
            self._destroy_card(card, owner)

    def _destroy_card(self, card: Card, owner: Player):
        if card in owner.board:
            owner.board.remove(card)
            owner.discard.append(card)
            card.reset() 
            if card.trigger == "ON_DEATH":
                opponent = self.player2 if owner == self.player1 else self.player1
                EffectManager.apply_effect(self, card, owner, opponent)

    def _put_card_on_board(self, player, card):
        player.board.append(card)
        opponent = self.player2 if player == self.player1 else self.player1
        is_silenced = False
        for opp_card in opponent.board:
            if opp_card.ability and opp_card.trigger == "PASSIVE" and opp_card.ability.code == "SILENCE_ON_PLAY":
                print(f"> Effet annulé par {opp_card.name} (Silence) !")
                is_silenced = True
                break
        if not is_silenced and card.trigger == "ON_PLAY":
            EffectManager.apply_effect(self, card, player, opponent)

    def _switch_active_player(self):
        self.active_player_idx = 1 - self.active_player_idx

    def _end_turn(self):
        self.refill_hand(self.player1)
        self.refill_hand(self.player2)
        self._switch_active_player()
        self.phase = Phase.P1_MAIN if self.active_player_idx == 0 else Phase.P2_MAIN
        self.turn_count += 1
        print(f"--- Fin du tour. Au tour de {self.active_player.name} ---")

    def _check_win_condition(self):
        if self.player1.hp <= 0: self.winner = self.player2
        elif self.player2.hp <= 0: self.winner = self.player1

    def render(self): pass
