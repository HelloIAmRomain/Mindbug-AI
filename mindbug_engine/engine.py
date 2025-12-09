import random
from typing import Optional
from .models import Card, Player, CardLoader
from .effects import EffectManager
from .rules import Phase, Keyword, CombatUtils, TriggerType

class MindbugGame:
    def __init__(self, deck_path="data/cards.json"):
        # 1. Chargement
        self.full_deck = CardLoader.load_deck(deck_path)
        random.shuffle(self.full_deck)
        
        # 2. Setup Joueurs
        self.player1 = Player(name="P1")
        self.player2 = Player(name="P2")
        self.players = [self.player1, self.player2]
        
        # Distribution (10 cartes chacun : 5 main, 5 pioche perso)
        self._setup_player(self.player1)
        self._setup_player(self.player2)
        
        # 3. État Initial
        self.active_player_idx = 0 
        self.phase = Phase.P1_MAIN
        self.turn_count = 1
        self.winner = None
        
        # Mémoire tampon pour les interactions
        self.pending_card: Optional[Card] = None      
        self.pending_attacker: Optional[Card] = None 
    
    def _setup_player(self, player):
        for _ in range(5):
            if self.full_deck: player.hand.append(self.full_deck.pop())
        # Note: La pioche perso n'est pas implémentée ici pour simplifier, 
        # on considère qu'ils jouent avec ce qu'ils ont.

    @property
    def active_player(self):
        return self.players[self.active_player_idx]

    @property
    def opponent(self):
        return self.players[1 - self.active_player_idx]

    # --- BOUCLE PRINCIPALE (STEP) ---

    def step(self, action_type: str, target_idx: int = -1, target_blocker_idx: int = -1):
        """
        Entrée principale pour faire avancer le jeu.
        """
        if self.winner:
            print(f"Jeu terminé. Vainqueur: {self.winner.name}")
            return

        # Affichage Debug
        target_str = f"-> {target_idx}" if target_idx != -1 else ""
        print(f"\n[Turn {self.turn_count}] {self.active_player.name} ({self.phase.name}): {action_type} {target_str}")

        # DISPATCHER SELON LA PHASE
        if self.phase in [Phase.P1_MAIN, Phase.P2_MAIN]:
            if action_type == "PLAY":
                self._action_play_card(target_idx)
            elif action_type == "ATTACK":
                self._action_declare_attack(target_idx, target_blocker_idx)
        
        elif self.phase == Phase.MINDBUG_DECISION:
            if action_type == "MINDBUG":
                self._action_use_mindbug()
            elif action_type == "PASS":
                self._action_pass_mindbug()

        elif self.phase == Phase.BLOCK_DECISION:
            if action_type == "BLOCK":
                self._action_block(target_idx)
            elif action_type == "NO_BLOCK":
                self._resolve_combat(blocker=None)

        self._check_win_condition()

    # --- ACTIONS DE JEU ---

    def _action_play_card(self, hand_idx):
        if not (0 <= hand_idx < len(self.active_player.hand)):
            print("ERREUR: Indice de carte invalide.")
            return

        card = self.active_player.hand.pop(hand_idx)
        self.pending_card = card
        print(f"> Pose {card.name}. Mindbug ?")
        
        # On passe la main à l'adversaire pour la décision
        self._switch_active_player() 
        self.phase = Phase.MINDBUG_DECISION

    def _action_use_mindbug(self):
        thief = self.active_player          # Celui qui décide (P2)
        victim = self.opponent              # Celui qui a posé la carte (P1)
        
        if thief.mindbugs > 0:
            thief.mindbugs -= 1
            print(f"> MINDBUG ! {thief.name} vole {self.pending_card.name} !")
            
            # La carte arrive chez le voleur (et déclenche ses effets pour le voleur)
            self._put_card_on_board(thief, self.pending_card)
            self.pending_card = None
            
            # --- CORRECTION RÈGLE ---
            # Une fois le vol résolu, c'est TOUJOURS au joueur initial (la victime) de rejouer.
            # Actuellement, active_player est le Voleur (car on a switché pour la décision).
            # Donc on doit switcher ENCORE une fois pour revenir à la victime.
            
            self._switch_active_player() # On rend la main à la victime
            print(f"> Le tour revient à {self.active_player.name} (Rejoue son tour).")
            
            # On remet la phase en MAIN
            self.phase = Phase.P1_MAIN if self.active_player_idx == 0 else Phase.P2_MAIN
            
        else:
            print("Action impossible : Plus de Mindbugs.")



    def _action_pass_mindbug(self):
        print("> Refus du Mindbug.")
        # On rend la main au joueur d'origine
        self._switch_active_player()
        owner = self.active_player
        
        self._put_card_on_board(owner, self.pending_card)
        self.pending_card = None
        self._end_turn()

    def _action_declare_attack(self, board_idx, target_blocker_idx=-1):
        attacker = self.active_player.board[board_idx]
        self.pending_attacker = attacker
        print(f"> Attaque avec {attacker.name} !")

        # GESTION HUNTER (Chasseur)
        if Keyword.HUNTER.value in attacker.keywords:
            opponent = self.opponent
            # Si cible choisie et valide
            if 0 <= target_blocker_idx < len(opponent.board):
                blocker = opponent.board[target_blocker_idx]
                print(f"> CHASSEUR : Force {blocker.name} à bloquer.")
                self._resolve_combat(blocker)
            else:
                # Si pas de cible ou cible invalide -> Attaque directe ou auto-select ?
                # Pour simplifier ici : Si board vide -> direct, sinon -> erreur/default
                if not opponent.board:
                     self._resolve_combat(None)
                else:
                    print("> CHASSEUR (Auto) : Attaque la première créature.")
                    self._resolve_combat(opponent.board[0])
        else:
            # Cas normal : l'adversaire doit choisir
            self._switch_active_player()
            self.phase = Phase.BLOCK_DECISION

    def _action_block(self, blocker_idx):
        blocker = self.active_player.board[blocker_idx]
        attacker = self.pending_attacker
        
        # GESTION SNEAKY (Furtif)
        if not CombatUtils.can_block(attacker, blocker):
            print(f"> BLOCAGE ILLÉGAL : {attacker.name} est Furtif !")
            # On considère comme un "No Block" pour éviter le crash, 
            # mais l'IA devra être empêchée de faire ce choix.
            self._resolve_combat(None) 
            return

        print(f"> Bloque avec {blocker.name}.")
        self._resolve_combat(blocker)

    # --- RÉSOLUTION DU COMBAT (Le Coeur Logique) ---

    def _resolve_combat(self, blocker: Optional[Card]):
        attacker = self.pending_attacker
        
        # Identification des propriétaires
        # Si on est en phase BLOCK_DECISION, l'active_player est le défenseur.
        # Si on vient d'un HUNTER, l'active_player est l'attaquant.
        # Le plus sûr est de chercher la carte dans les boards.
        attacker_owner = self.player1 if attacker in self.player1.board else self.player2
        defender_owner = self.player2 if attacker_owner == self.player1 else self.player1

        if blocker is None:
            print(f"> Pas de blocage ! {defender_owner.name} perd 1 PV.")
            defender_owner.hp -= 1
        else:
            print(f"> Combat : {attacker.name} ({attacker.power}) vs {blocker.name} ({blocker.power})")
            
            # 1. Qui "devrait" mourir selon les règles ? (Rules Pure)
            att_dead_theoretical, blk_dead_theoretical = CombatUtils.simulate_combat(attacker, blocker)
            
            # 2. Application des dégâts (avec gestion Coriace/Tough)
            if att_dead_theoretical:
                self._apply_lethal_damage(attacker, attacker_owner)
            
            if blk_dead_theoretical:
                self._apply_lethal_damage(blocker, defender_owner)

        # Nettoyage et fin de tour
        self.pending_attacker = None
        
        # Le tour passe toujours à celui qui défendait
        next_player = defender_owner
        self.active_player_idx = 0 if next_player == self.player1 else 1
        self.phase = Phase.P1_MAIN if self.active_player_idx == 0 else Phase.P2_MAIN
        self.turn_count += 1
        print(f"--- Fin du tour. Au tour de {self.active_player.name} ---")

    def _apply_lethal_damage(self, card: Card, owner: Player):
        """
        Applique la tentative de destruction.
        Gère centralement le mot-clé TOUGH (Coriace).
        """
        # Vérification du CORIACE
        if Keyword.TOUGH.value in card.keywords and not card.is_damaged:
            print(f"> {card.name} est CORIACE ! Il survit et devient blessé.")
            card.is_damaged = True
        else:
            print(f"> {card.name} est détruit.")
            self._destroy_card(card, owner)

    def _destroy_card(self, card: Card, owner: Player):
        if card in owner.board:
            owner.board.remove(card)
            owner.discard.append(card)
            card.is_damaged = False 
            
            # Vérification du Trigger ON_DEATH
            if card.trigger == "ON_DEATH":
                opponent = self.player2 if owner == self.player1 else self.player1
                EffectManager.apply_effect(self, card, owner, opponent)

    def _put_card_on_board(self, player, card):
        player.board.append(card)
        
        # Vérification du Trigger ON_PLAY
        if card.trigger == "ON_PLAY":
            # On détermine l'adversaire
            opponent = self.player2 if player == self.player1 else self.player1
            EffectManager.apply_effect(self, card, player, opponent)

    def _switch_active_player(self):
        self.active_player_idx = 1 - self.active_player_idx

    def _end_turn(self):
        self._switch_active_player()
        self.phase = Phase.P1_MAIN if self.active_player_idx == 0 else Phase.P2_MAIN
        self.turn_count += 1
        print(f"--- Fin du tour. Au tour de {self.active_player.name} ---")

    def _check_win_condition(self):
        if self.player1.hp <= 0:
            self.winner = self.player2
        elif self.player2.hp <= 0:
            self.winner = self.player1

    def render(self):
        """Affichage simple pour debug"""
        print("\n" + "="*40)
        p2 = self.player2
        print(f"J2: {p2.name} [HP:{p2.hp} MB:{p2.mindbugs}] Hand:{len(p2.hand)}")
        print(f"    Board: {p2.board}")
        print("-" * 40)
        print(f"    Board: {self.player1.board}")
        p1 = self.player1
        print(f"J1: {p1.name} [HP:{p1.hp} MB:{p1.mindbugs}] Hand:{len(p1.hand)}")
        print("="*40 + "\n")
