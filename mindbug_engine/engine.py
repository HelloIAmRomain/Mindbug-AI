import random
import sys
import os
from typing import Optional, List, Tuple
from .models import Card, Player
from .loaders import CardLoader
from .rules import Phase, Keyword, CombatUtils
from .effects import EffectManager
from constants import PATH_DATA

# NOUVEAUX IMPORTS
from .combat import CombatManager
from .commands import (
    PlayCardCommand, AttackCommand, BlockCommand, NoBlockCommand, 
    MindbugCommand, PassCommand, ResolveSelectionCommand
)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class MindbugGame:
    def __init__(self, deck_path=None, active_card_ids=None, active_sets=None):
        
        if deck_path is None:
            deck_path = PATH_DATA if os.path.exists(PATH_DATA) else resource_path(os.path.join("data", "cards.json"))
            
        # 1. Loading
        all_cards_loaded = CardLoader.load_deck(deck_path)
        
        # Filtre Sets
        if active_sets:
            all_cards = [c for c in all_cards_loaded if getattr(c, 'set', 'FIRST_CONTACT') in active_sets]
            if not all_cards: all_cards = all_cards_loaded
        else:
            all_cards = all_cards_loaded
        
        # Filtre DeckBuilder
        if active_card_ids:
            self.full_deck = [c for c in all_cards if c.id in active_card_ids]
            current_count = len(self.full_deck)
            if current_count < 20:
                selected_ids = set(c.id for c in self.full_deck)
                available_pool = [c for c in all_cards if c.id not in selected_ids]
                missing = 20 - current_count
                if len(available_pool) >= missing:
                    self.full_deck.extend(random.sample(available_pool, missing))
                else:
                    self.full_deck.extend(available_pool)
        else:
            self.full_deck = list(all_cards)
            
        self.all_cards_ref = list(all_cards)
        random.shuffle(self.full_deck)
        
        # 2. Players
        self.player1 = Player(name="P1")
        self.player2 = Player(name="P2")
        self.players = [self.player1, self.player2]
        self._setup_player(self.player1)
        self._setup_player(self.player2)
        
        # 3. State
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

        # 4. Managers (Combat & Effects)
        self.effect_manager = EffectManager()
        self.combat_manager = CombatManager(self) # <--- Nouveau
    
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
    def active_player(self): return self.players[self.active_player_idx]

    @property
    def opponent(self): return self.players[1 - self.active_player_idx]

    # --- PONT VERS COMBAT MANAGER ---
    def calculate_real_power(self, card: Card) -> int:
        return self.combat_manager.calculate_real_power(card, self.active_player, self.opponent)

    def resolve_combat(self, blocker: Optional[Card]):
        """
        Orchestre la résolution d'un combat.
        Délègue les calculs au CombatManager et la gestion de flux aux helpers.
        """
        # 1. Identification des acteurs
        attacker = self.pending_attacker
        attacker_owner = self.opponent 
        
        # 2. Résolution mathématique (Dégâts, Morts, Effets)
        att_dead, blk_dead = self.combat_manager.resolve_fight(attacker, blocker)
        
        # Nettoyage état temporaire
        self.pending_attacker = None
        
        # 3. Interruption ? (Ex: Effet de mort nécessitant un choix)
        if self.phase == Phase.RESOLUTION_CHOICE:
            print("   -> Combat interrupted (Selection required).")
            self.end_turn_pending = True
            return 

        # 4. Vérification Furie (Frenzy)
        if self._try_activate_frenzy(attacker, attacker_owner, att_dead):
            return # On stop ici, le tour continue pour l'attaquant

        # 5. Fin de tour standard
        # IMPORTANT : En ce moment, le joueur actif est le DÉFENSEUR.
        # Si on appelle end_turn() directement, il va switch vers l'ATTAQUANT (P1).
        # On veut que le prochain tour soit celui du DÉFENSEUR (P2).
        # Donc, on remet l'attaquant actif pour que end_turn() fasse la passe correctement.
        self.switch_active_player()
        
        self.end_turn()

    def _check_frenzy_continuation(self):
        # Logique simplifiée pour la fin de tour
        # Si on avait un frenzy candidate et qu'il vient d'attaquer pour la 2eme fois, c'est fini
        if self.frenzy_candidate:
             # C'était la 2eme attaque ?
             # Pour l'instant on finit le tour sauf si on implémente la double attaque
             pass
        
        self.end_turn()

    # --- MAIN LOOP STEP (ADAPTÉE POUR COMMANDES) ---
    def step(self, action_type: str, target_idx: int = -1, target_blocker_idx: int = -1):
        """
        Point d'entrée principal. Convertit les strings (UI) en Commandes.
        """
        if self.winner: return
        
        # Mise à jour des mots-clés passifs avant toute action
        self.update_board_states()

        command = None

        # Factory simple (Switch case)
        if action_type == "PLAY":
            command = PlayCardCommand(target_idx)
        elif action_type == "ATTACK":
            command = AttackCommand(target_idx, target_blocker_idx)
        elif action_type == "BLOCK":
            command = BlockCommand(target_idx)
        elif action_type == "NO_BLOCK":
            command = NoBlockCommand()
        elif action_type == "MINDBUG":
            command = MindbugCommand()
        elif action_type == "PASS":
            command = PassCommand()
        elif action_type.startswith("SELECT_"):
            # Ex: SELECT_BOARD_P1
            parts = action_type.split("_", 1) # ["SELECT", "BOARD_P1"]
            if len(parts) > 1:
                command = ResolveSelectionCommand(parts[1], target_idx)

        # Exécution
        if command:
            command.execute(self)
            
        self._check_win_condition()
        self.refill_hand(self.player1)
        self.refill_hand(self.player2)

    # --- MÉTHODES UTILITAIRES POUR LES COMMANDES ---
    # Ces méthodes sont appelées par les objets Command
    
    def switch_active_player(self):
        self.active_player_idx = 1 - self.active_player_idx

    def end_turn(self):
        self.refill_hand(self.player1)
        self.refill_hand(self.player2)
        self.switch_active_player()
        self.phase = Phase.P1_MAIN if self.active_player_idx == 0 else Phase.P2_MAIN
        self.turn_count += 1
        print(f"--- Turn end. Turn of {self.active_player.name} ---")

    def execute_mindbug_replay(self):
        self.switch_active_player() 
        print(f"> Turn returns to {self.active_player.name} (Replays turn).")
        self.phase = Phase.P1_MAIN if self.active_player_idx == 0 else Phase.P2_MAIN

    def put_card_on_board(self, player, card):
        player.board.append(card)
        opponent = self.player2 if player == self.player1 else self.player1
        
        # Check Silence
        is_silenced = False
        for opp_card in opponent.board:
            if opp_card.ability and opp_card.trigger == "PASSIVE" and opp_card.ability.code == "SILENCE_ON_PLAY":
                print(f"> Effect cancelled by {opp_card.name} (Silence) !")
                is_silenced = True
                break
                
        if not is_silenced and card.trigger == "ON_PLAY":
            self.effect_manager.apply_effect(self, card, player, opponent)

    def resolve_selection_effect(self, selected_card: Card):
        # Cette méthode est appelée par ResolveSelectionCommand
        # Elle contient la logique des effets ciblés (Steal, Destroy...)
        # Pour ne pas dupliquer le code de engine.py précédent, on le remet ici
        # (Dans une version future, cela pourrait aller dans effect_manager)
        ctx = self.selection_context
        if not ctx: return

        effect = ctx["effect_code"]
        initiator = ctx["initiator"]
        print(f"> Target chosen : {selected_card.name}")

        if effect == "DESTROY_CREATURE" or effect == "DESTROY_IF_FEWER_ALLIES":
            victim = self.player1 if selected_card in self.player1.board else self.player2
            self.combat_manager.destroy_card(selected_card, victim)
        
        elif effect == "STEAL_CREATURE":
            victim = self.player1 if selected_card in self.player1.board else self.player2
            if selected_card in victim.board:
                victim.board.remove(selected_card)
                initiator.board.append(selected_card)
        
        elif effect == "HUNTER_TARGET":
            print(f"   -> {initiator.name} forces {selected_card.name} to block !")
            self.selection_context = None
            if self.active_player_idx == 0: self.phase = Phase.P1_MAIN
            else: self.phase = Phase.P2_MAIN
            self.resolve_combat(selected_card)
            return

        elif effect == "RECLAIM_DISCARD":
            owner = self.player1 if selected_card in self.player1.discard else self.player2
            if selected_card in owner.discard:
                owner.discard.remove(selected_card)
                initiator.hand.append(selected_card)
                selected_card.reset()

        elif effect == "PLAY_FROM_OPP_DISCARD" or effect == "PLAY_FROM_MY_DISCARD":
            owner = self.player1 if selected_card in self.player1.discard else self.player2
            if selected_card in owner.discard:
                owner.discard.remove(selected_card)
                self.put_card_on_board(initiator, selected_card)
                selected_card.reset()

        ctx["count"] -= 1
        if ctx["count"] <= 0:
            print("   -> Selection end.")
            self.selection_context = None
            if self.mindbug_replay_pending:
                self.mindbug_replay_pending = False
                self.execute_mindbug_replay()
            elif self.end_turn_pending:
                self.end_turn_pending = False
                self.end_turn()
            else:
                if self.active_player_idx == 0: self.phase = Phase.P1_MAIN
                else: self.phase = Phase.P2_MAIN
        else:
            print(f"   -> Still {ctx['count']} target(s) to choose...")

    def update_board_states(self):
        # Cette logique peut rester ici ou aller dans un RuleManager
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
        # La logique de génération des coups reste identique pour l'instant
        self.update_board_states()
        moves = []
        player = self.active_player
        if self.winner: return []

        if self.phase in [Phase.P1_MAIN, Phase.P2_MAIN]:
            if self.frenzy_candidate:
                if self.frenzy_candidate in player.board:
                    idx = player.board.index(self.frenzy_candidate)
                    moves.append(("ATTACK", idx))
                for i in range(len(player.hand)): moves.append(("PLAY", i))
            else:
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

    def _check_win_condition(self):
        if self.player1.hp <= 0: self.winner = self.player2
        elif self.player2.hp <= 0: self.winner = self.player1

    def _try_activate_frenzy(self, attacker: Card, owner: Player, is_dead: bool) -> bool:
        """
        Vérifie et applique la règle FRENZY (Furie).
        Retourne True si une nouvelle attaque est déclenchée, False sinon.
        """
        # Conditions :
        # 1. La créature n'est pas morte (et est toujours sur le plateau)
        survived = (not is_dead) and (attacker in owner.board)
        # 2. Elle possède le mot-clé FRENZY
        has_frenzy = Keyword.FRENZY.value in attacker.keywords
        # 3. Ce n'était pas déjà l'attaque bonus (on ne peut pas enchaîner à l'infini)
        is_bonus_attack = (self.frenzy_candidate == attacker)
        
        # On reset le candidat par défaut (sera réactivé si conditions remplies)
        self.frenzy_candidate = None
        
        if survived and has_frenzy and not is_bonus_attack:
            print(f"> FRENZY ! {attacker.name} can attack a second time.")
            
            # Stockage de l'état
            self.frenzy_candidate = attacker
            
            # Transfert de la main au joueur attaquant
            self.switch_active_player()

            # Mise à jour de la Phase
            if self.active_player_idx == 0: 
                self.phase = Phase.P1_MAIN
            else: 
                self.phase = Phase.P2_MAIN
            
            return True
            
        return False

    def render(self): pass
