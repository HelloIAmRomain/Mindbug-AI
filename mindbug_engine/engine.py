import random
import sys
import os
from typing import Optional, List, Tuple
from .models import Card, Player, CardLoader
from .rules import Phase, Keyword, CombatUtils
from .effects import EffectManager
from constants import PATH_DATA

# --- HELPER FUNCTION FOR PYINSTALLER ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class MindbugGame:
    # --- MODIFICATION ICI : active_sets est bien présent pour corriger le crash ---
    def __init__(self, deck_path=None, active_card_ids=None, active_sets=None):
        
        if deck_path is None:
            deck_path = PATH_DATA if os.path.exists(PATH_DATA) else resource_path(os.path.join("data", "cards.json"))
            
        # 1. Loading ALL available cards (The "Pack")
        all_cards_loaded = CardLoader.load_deck(deck_path)
        
        # --- FILTRAGE PAR SET ---
        if active_sets:
            # On ne garde que les cartes dont le set est dans la liste active
            # getattr securise l'accès si une carte n'a pas l'attribut 'set'
            all_cards = [c for c in all_cards_loaded if getattr(c, 'set', 'FIRST_CONTACT') in active_sets]
            
            # Sécurité : Si le filtre vide tout, on garde tout le monde
            if not all_cards:
                print(f"[Engine] Attention : Aucun set correspondant à {active_sets}. Chargement de tout le deck.")
                all_cards = all_cards_loaded
        else:
            all_cards = all_cards_loaded
        # ------------------------
        
        # 2. Filtering & Completion (Card IDs from Deck Builder)
        if active_card_ids:
            # A. First take those specifically chosen by the player
            self.full_deck = [c for c in all_cards if c.id in active_card_ids]
            
            # B. Vital Minimum Verification (20 cards : 10 per player)
            current_count = len(self.full_deck)
            min_required = 20
            
            if current_count < min_required:
                missing = min_required - current_count
                print(f"[Engine] Selected deck too small ({current_count}). Adding {missing} random cards...")
                
                # Identify cards NOT already selected
                selected_ids = set(c.id for c in self.full_deck)
                available_pool = [c for c in all_cards if c.id not in selected_ids]
                
                # Complete with random cards
                if len(available_pool) >= missing:
                    fillers = random.sample(available_pool, missing)
                    self.full_deck.extend(fillers)
                else:
                    # Extreme case: Even with everything else, not enough for 20 cards
                    print("[Engine] Warning: Not enough cards in database to reach 20!")
                    self.full_deck.extend(available_pool)
        else:
            # No selection: Take the whole pack (filtered by set)
            self.full_deck = list(all_cards)
            
        # 3. UI Reference and Shuffle
        self.all_cards_ref = list(all_cards) # UI needs to know all possible images
        random.shuffle(self.full_deck)
        
        # 4. Player Setup
        self.player1 = Player(name="P1")
        self.player2 = Player(name="P2")
        self.players = [self.player1, self.player2]
        
        # Distribution (5 hand + 5 deck = 10 per player)
        self._setup_player(self.player1)
        self._setup_player(self.player2)
        
        # 5. Initial State
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

        # 6. Effect Manager Instantiation
        self.effect_manager = EffectManager()
    
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

    # --- POWER CALCULATION ---
    def calculate_real_power(self, card: Card) -> int:
        current = card.power
        turn_owner = self.active_player
        if self.phase in [Phase.BLOCK_DECISION, Phase.MINDBUG_DECISION]:
            turn_owner = self.opponent
            
        card_owner = self.player1 if card in self.player1.board else self.player2
        board = card_owner.board
        is_my_turn = (card_owner == turn_owner)

        # 1. Ally Bonus
        for ally in board:
            if ally == card: continue
            if ally.ability and ally.trigger == "PASSIVE" and ally.ability.code == "BOOST_ALLIES":
                current += ally.ability.value

        # 2. Turn Bonus
        if card.ability and card.trigger == "PASSIVE" and card.ability.code == "BOOST_IF_MY_TURN":
             if is_my_turn: current += card.ability.value

        # 3. Ally Turn Bonus
        for ally in board:
            if ally == card: continue 
            if ally.ability and ally.trigger == "PASSIVE" and ally.ability.code == "BOOST_ALLIES_IF_MY_TURN":
                if is_my_turn: current += ally.ability.value
        
        # 4. Yeti
        if card.ability and card.trigger == "PASSIVE" and card.ability.code == "BOOST_AND_FRENZY_IF_ALONE":
            if len(board) == 1: current += card.ability.value
        
        # 5. Enemy Debuff
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
            # If Frenzy active, must attack with Frenzy card
            if self.frenzy_candidate:
                if self.frenzy_candidate in player.board:
                    idx = player.board.index(self.frenzy_candidate)
                    moves.append(("ATTACK", idx))
                # Still allow playing a card? 
                for i in range(len(player.hand)): moves.append(("PLAY", i))
            else:
                # Normal case
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
            print("   -> No target available (Selection cancelled).")
            return

        print(f"⌛ WAITING : {initiator.name} must choose a target for {effect_code}.")
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
        print(f"> Plays {card.name}. Mindbug ?")
        
        self.frenzy_candidate = None 
        self.refill_hand(self.active_player)
        self._switch_active_player() 
        self.phase = Phase.MINDBUG_DECISION

    def _action_use_mindbug(self):
        thief = self.active_player
        if thief.mindbugs > 0:
            thief.mindbugs -= 1
            print(f"> MINDBUG ! {thief.name} steals {self.pending_card.name} !")
            self._put_card_on_board(thief, self.pending_card)
            self.pending_card = None
            
            if self.phase == Phase.RESOLUTION_CHOICE:
                print("   -> Mindbug turn end suspended pending selection...")
                self.mindbug_replay_pending = True
            else:
                self._execute_mindbug_replay()
        else:
            print("Action impossible.")

    def _execute_mindbug_replay(self):
        self._switch_active_player() 
        print(f"> Turn returns to {self.active_player.name} (Replays turn).")
        self.phase = Phase.P1_MAIN if self.active_player_idx == 0 else Phase.P2_MAIN

    def _action_pass_mindbug(self):
        print("> Mindbug refused.")
        self._switch_active_player()
        owner = self.active_player
        self._put_card_on_board(owner, self.pending_card)
        self.pending_card = None
        
        if self.phase == Phase.RESOLUTION_CHOICE:
            print("   -> Turn end suspended pending selection...")
            self.end_turn_pending = True
        else:
            self._end_turn()

    def _action_declare_attack(self, board_idx, target_blocker_idx=-1):
        if not (0 <= board_idx < len(self.active_player.board)): return
        attacker = self.active_player.board[board_idx]
        self.pending_attacker = attacker
        print(f"> Attack with {attacker.name} !")

        if Keyword.HUNTER.value in attacker.keywords and self.opponent.board:
            print(f"> HUNTER : Please select the opponent creature that must block.")
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
        print(f"> Blocks with {blocker.name}.")
        self._resolve_combat(blocker)

    def _resolve_combat(self, blocker: Optional[Card]):
        attacker = self.pending_attacker
        attacker_owner = self.player1 if attacker in self.player1.board else self.player2
        defender_owner = self.player2 if attacker_owner == self.player1 else self.player1

        # 1. Real power calculation (including passive bonuses)
        att_power = self.calculate_real_power(attacker)
        
        if blocker is None:
            print(f"> No block ! {defender_owner.name} loses 1 HP.")
            defender_owner.hp -= 1
        else:
            blk_power = self.calculate_real_power(blocker)
            print(f"> Combat : {attacker.name} ({att_power}) vs {blocker.name} ({blk_power})")
            
            att_dead, blk_dead = CombatUtils.simulate_combat(attacker, blocker)
            
            if Keyword.POISON.value in attacker.keywords: blk_dead = True
            if Keyword.POISON.value in blocker.keywords: att_dead = True

            if att_dead: self._apply_lethal_damage(attacker, attacker_owner)
            if blk_dead: self._apply_lethal_damage(blocker, defender_owner)

        self.pending_attacker = None
        
        if self.phase == Phase.RESOLUTION_CHOICE:
            print("   -> Combat end suspended pending selection (Death effect)...")
            self.end_turn_pending = True
            return 

        # --- FRENZY MANAGEMENT ---
        survived = (attacker in attacker_owner.board)
        has_frenzy = Keyword.FRENZY.value in attacker.keywords
        is_bonus_attack = (self.frenzy_candidate == attacker)
        
        self.frenzy_candidate = None
        
        if survived and has_frenzy and not is_bonus_attack:
            print(f"> FRENZY ! {attacker.name} can attack a second time.")
            self.frenzy_candidate = attacker
            self._switch_active_player()

            if self.active_player_idx == 0: self.phase = Phase.P1_MAIN
            else: self.phase = Phase.P2_MAIN
            
            return # <-- STOP : Do not end turn !

        # Standard turn end
        next_player = defender_owner
        self.active_player_idx = 0 if next_player == self.player1 else 1
        self.phase = Phase.P1_MAIN if self.active_player_idx == 0 else Phase.P2_MAIN
        self.turn_count += 1
        print(f"--- Turn end. Turn of {self.active_player.name} ---")

    def _action_resolve_selection(self, selected_card: Card):
        ctx = self.selection_context
        if not ctx: return

        effect = ctx["effect_code"]
        initiator = ctx["initiator"]
        print(f"> Target chosen : {selected_card.name}")

        if effect == "DESTROY_CREATURE" or effect == "DESTROY_IF_FEWER_ALLIES":
            victim = self.player1 if selected_card in self.player1.board else self.player2
            print(f"   -> {selected_card.name} is destroyed.")
            self._destroy_card(selected_card, victim)
        
        elif effect == "STEAL_CREATURE":
            victim = self.player1 if selected_card in self.player1.board else self.player2
            if selected_card in victim.board:
                victim.board.remove(selected_card)
                initiator.board.append(selected_card)
                print(f"   -> {initiator.name} steals {selected_card.name}.")
        
        elif effect == "HUNTER_TARGET":
            print(f"   -> {initiator.name} forces {selected_card.name} to block !")
            self.selection_context = None
            
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
                print(f"   -> {initiator.name} reclaims {selected_card.name}.")
                
        elif effect == "PLAY_FROM_OPP_DISCARD" or effect == "PLAY_FROM_MY_DISCARD":
            owner = self.player1 if selected_card in self.player1.discard else self.player2
            if selected_card in owner.discard:
                owner.discard.remove(selected_card)
                print(f"   -> {initiator.name} plays {selected_card.name} from discard !")
                self._put_card_on_board(initiator, selected_card)
                selected_card.reset()

        ctx["count"] -= 1
        if ctx["count"] <= 0:
            print("   -> Selection end.")
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
            print(f"   -> Still {ctx['count']} target(s) to choose...")

    def _apply_lethal_damage(self, card: Card, owner: Player):
        if Keyword.TOUGH.value in card.keywords and not card.is_damaged:
            print(f"> {card.name} is TOUGH ! Survives.")
            card.is_damaged = True
        else:
            print(f"> {card.name} is destroyed.")
            self._destroy_card(card, owner)

    def _destroy_card(self, card: Card, owner: Player):
        if card in owner.board:
            owner.board.remove(card)
            owner.discard.append(card)
            card.reset() 
            if card.trigger == "ON_DEATH":
                opponent = self.player2 if owner == self.player1 else self.player1
                self.effect_manager.apply_effect(self, card, owner, opponent)

    def _put_card_on_board(self, player, card):
        player.board.append(card)
        opponent = self.player2 if player == self.player1 else self.player1
        is_silenced = False
        for opp_card in opponent.board:
            if opp_card.ability and opp_card.trigger == "PASSIVE" and opp_card.ability.code == "SILENCE_ON_PLAY":
                print(f"> Effect cancelled by {opp_card.name} (Silence) !")
                is_silenced = True
                break
        if not is_silenced and card.trigger == "ON_PLAY":
            self.effect_manager.apply_effect(self, card, player, opponent)

    def _switch_active_player(self):
        self.active_player_idx = 1 - self.active_player_idx

    def _end_turn(self):
        self.refill_hand(self.player1)
        self.refill_hand(self.player2)
        self._switch_active_player()
        self.phase = Phase.P1_MAIN if self.active_player_idx == 0 else Phase.P2_MAIN
        self.turn_count += 1
        print(f"--- Turn end. Turn of {self.active_player.name} ---")

    def _check_win_condition(self):
        if self.player1.hp <= 0: self.winner = self.player2
        elif self.player2.hp <= 0: self.winner = self.player1

    def render(self): pass
