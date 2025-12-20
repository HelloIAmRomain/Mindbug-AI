import random
import traceback
import copy
from typing import Optional, List, Tuple, Any

from mindbug_engine.utils.logger import log_info, log_debug, log_error

# --- IMPORTS CORE ---
from mindbug_engine.core.models import Card, Player, SelectionRequest
from mindbug_engine.core.state import GameState
from mindbug_engine.core.consts import Phase, Trigger, Keyword

# --- IMPORTS INFRASTRUCTURE ---
from mindbug_engine.infrastructure.deck_factory import DeckFactory
from constants import PATH_DATA

# --- IMPORTS MANAGERS (V3 ARCHITECTURE) ---
from mindbug_engine.managers.turn_manager import TurnManager
from mindbug_engine.managers.combat_manager import CombatManager
from mindbug_engine.managers.effect_manager import EffectManager
from mindbug_engine.managers.query_manager import QueryManager

# --- IMPORTS COMMANDS ---
from mindbug_engine.commands.command_factory import CommandFactory


class MindbugGame:
    """
    Façade principale du moteur de jeu.
    Point d'entrée unique pour l'Interface Graphique (GUI) et l'IA.

    Responsabilités :
    1. Initialiser la partie via l'Infrastructure (DeckFactory).
    2. Orchestrer la boucle de jeu (Step).
    3. Déléguer la logique métier aux Managers.
    4. Exposer une API stable pour les Commandes et l'UI.
    """

    def __init__(self,
                 active_card_ids: Optional[List[str]] = None,
                 active_sets: Optional[List[str]] = None,
                 verbose: bool = True,
                 deck_path: Optional[str] = None):

        self.verbose = verbose
        if self.verbose:
            log_info("=== INITIALISATION DU MOTEUR ===")

        # 1. SETUP INFRASTRUCTURE & STATE
        path = deck_path if deck_path else PATH_DATA
        self.deck_factory = DeckFactory(path)

        # Création du deck et récupération des références
        game_deck, all_cards_ref, used_sets = self.deck_factory.create_deck(
            active_sets=active_sets,
            active_card_ids=active_card_ids
        )
        self.used_sets = used_sets

        # Initialisation de l'état (State)
        p1 = Player(name="P1")
        p2 = Player(name="P2")
        self.state = GameState(game_deck, p1, p2)
        self.state.all_cards_ref = all_cards_ref

        # 2. INITIALISATION MANAGERS (Injection de dépendances)
        # On passe 'self' (l'instance du jeu) aux managers qui ont besoin d'accéder
        # à l'état global ou aux autres managers via la façade.

        self.turn_manager = TurnManager(self)
        self.query_manager = QueryManager(self)
        self.combat_manager = CombatManager(self)  # Combat a besoin de l'Engine (self)
        self.effect_manager = EffectManager(self)  # Effect a besoin de l'Engine (self)

        # Injection croisée : Le CombatManager doit pouvoir déclencher des effets
        self.combat_manager.effect_manager = self.effect_manager

    def start_game(self):
        """
        Démarre la partie : Mélange, Distribution et Reset.
        """
        if not self.state.deck:
            raise ValueError("Impossible de démarrer : Deck vide.")

        if self.verbose:
            log_info(f"🎲 START GAME... Deck: {len(self.state.deck)} cartes.")

        random.shuffle(self.state.deck)

        # Reset des mains (Sécurité pour restart)
        self.state.player1.hand = []
        self.state.player2.hand = []

        # Distribution : 5 cartes chacun
        for _ in range(5):
            if self.state.deck: self.state.player1.hand.append(self.state.deck.pop())
            if self.state.deck: self.state.player2.hand.append(self.state.deck.pop())

        # Setup initial
        self.state.turn_count = 1
        self.state.active_player_idx = 0
        self.state.phase = Phase.P1_MAIN

        # Stats
        self.state.player1.hp = 3
        self.state.player2.hp = 3
        self.state.player1.mindbugs = 2
        self.state.player2.mindbugs = 2

    # =========================================================================
    #  GAME LOOP (STEP & MOVES)
    # =========================================================================

    def step(self, action_type: str, index: int = -1):
        """
        Exécute une action atomique.
        Utilise la CommandFactory pour découpler l'intention de l'exécution.
        """
        if self.state.winner:
            log_info("⚠️ Action ignorée : Partie terminée.")
            return

        if self.verbose:
            log_info(f"▶ STEP : {action_type} (idx={index})")

        # 1. Mise à jour des états passifs avant action (Auras)
        self.update_board_states()

        # 2. Création et Exécution de la commande
        try:
            command = CommandFactory.create(action_type, index, self)
            if command:
                command.execute(self)
            else:
                log_debug(f"❌ Commande inconnue ou invalide : {action_type}")
        except Exception as e:
            log_error(f"❌ CRASH EXECUTION : {e}")
            if self.verbose:
                traceback.print_exc()
            return

        # 3. Post-Action : Vérifications système
        self.turn_manager.check_win_condition()

        # Note : Le remplissage de main est souvent géré par le TurnManager en fin de tour,
        # mais on pourrait le forcer ici si besoin.

    def get_legal_moves(self) -> List[Tuple[str, int]]:
        """
        Retourne la liste des coups légaux pour l'UI/IA.
        """
        # 1. Mise à jour des passifs (Crucial pour calculer les blocages légaux : Furtif, etc.)
        self.update_board_states()

        if self.state.winner:
            return []

        moves = []
        ap = self.state.active_player
        phase = self.state.phase

        # --- A. FUREUR (Priorité absolue) ---
        # Si une créature est en fureur, elle DOIT attaquer immédiatement.
        if self.state.frenzy_candidate:
            if self.state.frenzy_candidate in ap.board:
                idx = ap.board.index(self.state.frenzy_candidate)
                return [("ATTACK", idx)]
            else:
                # La créature n'est plus sur le plateau (tuée par un effet ?), on annule la fureur.
                self.state.frenzy_candidate = None

        # --- B. PHASES PRINCIPALES (Action) ---
        if phase in [Phase.P1_MAIN, Phase.P2_MAIN]:
            # Jouer une carte de la main
            moves.extend([("PLAY", i) for i in range(len(ap.hand))])
            # Attaquer avec une créature
            moves.extend([("ATTACK", i) for i in range(len(ap.board))])

        # --- C. MINDBUG (Décision) ---
        elif phase == Phase.MINDBUG_DECISION:
            # On peut toujours refuser (Passer)
            moves.append(("PASS", -1))
            # On ne peut Mindbug que si on a des charges
            if ap.mindbugs > 0:
                moves.append(("MINDBUG", -1))

        # --- D. BLOCAGE (Défense) ---
        elif phase == Phase.BLOCK_DECISION:
            # On peut toujours choisir de ne pas bloquer (prendre les dégâts)
            moves.append(("NO_BLOCK", -1))

            attacker = self.state.pending_attacker
            if attacker:
                from mindbug_engine.utils.combat_utils import CombatUtils
                # On liste uniquement les créatures capables de bloquer l'attaquant
                for i, blocker in enumerate(ap.board):
                    if CombatUtils.can_block(attacker, blocker):
                        moves.append(("BLOCK", i))

        # E. SÉLECTION (Targeting)
        elif phase == Phase.RESOLUTION_CHOICE:
            req = self.state.active_request
            if req and req.candidates:
                # Le référentiel est le SELECTOR
                selector = req.selector
                opp_selector = self.state.player2 if selector == self.state.player1 else self.state.player1

                # -- ZONES DU SÉLECTEUR (Moi / SELECT_...) --
                for i, c in enumerate(selector.hand):
                    if c in req.candidates: moves.append(("SELECT_HAND", i))
                for i, c in enumerate(selector.board):
                    if c in req.candidates: moves.append(("SELECT_BOARD", i))
                for i, c in enumerate(selector.discard):
                    if c in req.candidates: moves.append(("SELECT_DISCARD", i))

                # -- ZONES DE L'ADVERSAIRE DU SÉLECTEUR (Lui / SELECT_OPP_...) --
                for i, c in enumerate(opp_selector.hand):
                    if c in req.candidates: moves.append(("SELECT_OPP_HAND", i))
                for i, c in enumerate(opp_selector.board):
                    if c in req.candidates: moves.append(("SELECT_OPP_BOARD", i))
                for i, c in enumerate(opp_selector.discard):
                    if c in req.candidates: moves.append(("SELECT_OPP_DISCARD", i))

        return moves


    # =========================================================================
    #  API PUBLIQUE (Façade pour Commandes & Effets)
    # =========================================================================

    def ask_for_selection(self, candidates: List[Any], reason: str, count: int, selector: Player, callback=None):
        """
        Délègue la demande de sélection au QueryManager.
        Appelé par les Commandes (ex: Hunter) ou les Effets.
        """
        self.query_manager.start_selection_request(candidates, reason, count, selector, callback)

    def execute_mindbug_replay(self):
        """
        Active la mécanique de 'Replay' après un Mindbug.
        """
        log_info("🔄 REPLAY ! The original player draws and plays again.")

        # 1. Changement de joueur (Le voleur P2 -> La victime P1)
        self.turn_manager.switch_active_player()

        # 2. FIX PIOCHE : La victime doit refaire sa main à 5 cartes AVANT de rejouer
        self.turn_manager.refill_hand(self.state.active_player)

        # 3. Reset phase
        self.state.phase = Phase.P1_MAIN if self.state.active_player_idx == 0 else Phase.P2_MAIN

    def resolve_selection_effect(self, selected_object: Any):
        """
        Point d'entrée de la commande 'ResolveSelectionCommand'.
        Gère la sélection et la REPRISE DU FLUX (Resume).
        """
        # 1. Délégation au Manager
        is_completed = self.query_manager.resolve_selection([selected_object])

        # 2. Logique de Reprise
        if is_completed and self.state.phase == Phase.RESOLUTION_CHOICE:
            log_info("▶️ Resuming flow after selection.")

            # CAS 1 : REPLAY EN ATTENTE (Mindbug utilisé + Effet avec sélection)
            if getattr(self.state, "mindbug_replay_pending", False):
                self.state.mindbug_replay_pending = False
                self.execute_mindbug_replay()
                return

            # CAS 2 : FIN DE TOUR STANDARD
            # (Ou Fin de tour en attente via PassCommand)

            # Correction de la synchronisation du joueur actif
            if self.state.active_player_idx == 0 and self.state.active_player != self.state.player1:
                self.turn_manager.switch_active_player()
            elif self.state.active_player_idx == 1 and self.state.active_player != self.state.player2:
                self.turn_manager.switch_active_player()

            # On nettoie le flag si présent (optionnel mais propre)
            if getattr(self.state, "end_turn_pending", False):
                self.state.end_turn_pending = False

            self.turn_manager.end_turn()

    def resolve_combat(self, blocker: Optional[Card]):
        """
        Orchestre la résolution complète d'un combat.

        Étapes :
        1. Résolution mathématique (Dégâts, Morts, Effets) via CombatManager.
        2. Mise à jour immédiate des états (ex: Retrait du mot-clé TOUGH si endommagé).
        3. Gestion de la Fureur (Nouvelle attaque) OU Fin de tour.
        """
        attacker = self.state.pending_attacker
        if not attacker:
            return

        # 1. RÉSOLUTION PHYSIQUE DU COMBAT
        self.combat_manager.resolve_fight(attacker, blocker)

        # si la carte a été marquée 'is_damaged' pendant le combat.
        self.update_board_states()

        # Si un effet (ex: ON_DEATH) a déclenché une demande de sélection,
        # on doit suspendre la résolution du combat et rendre la main au joueur.
        if self.state.phase == Phase.RESOLUTION_CHOICE:
            log_info("⏸️ Combat resolution paused for Selection.")
            return

        # Nettoyage de l'état temporaire
        self.state.pending_attacker = None

        # 2. VÉRIFICATION FUREUR (FRENZY)
        # On vérifie si l'attaquant est toujours vivant et possède le mot-clé
        att_owner = self.state.player1 if attacker in self.state.player1.board else self.state.player2
        is_alive = attacker in att_owner.board
        has_frenzy = Keyword.FRENZY in attacker.keywords

        # Condition : Vivant + Fureur + C'est sa première attaque ce tour-ci
        if is_alive and has_frenzy and self.state.frenzy_candidate != attacker:
            log_info(f"🔥 FRENZY ! {attacker.name} prepares to attack again.")

            # On mémorise que cet attaquant a déjà utilisé sa Fureur (pour ne pas boucler)
            self.state.frenzy_candidate = attacker

            # [FIX ETAT] Nous sommes en phase de Blocage (Joueur Actif = Défenseur).
            # Pour la nouvelle attaque, il faut REDONNER la main à l'ATTAQUANT.
            self.turn_manager.switch_active_player()

            # On remet la phase principale appropriée pour permettre la commande ATTACK
            self.state.phase = Phase.P1_MAIN if self.state.active_player_idx == 0 else Phase.P2_MAIN

            # On quitte ici pour ne PAS finir le tour
            return

        # 3. FIN DE TOUR STANDARD
        self.state.frenzy_candidate = None

        # [FIX FIN DE TOUR]
        # Actuellement, le joueur actif est le DÉFENSEUR (car nous étions en phase de blocage).
        # Si on appelle end_turn() maintenant, il va passer la main à l'autre joueur (l'Attaquant).
        # Or, on veut que le tour finisse et que ce soit au DÉFENSEUR de commencer SON tour.
        #
        # Solution : On switch manuellement vers l'ATTAQUANT maintenant...
        self.turn_manager.switch_active_player()

        # ... pour que end_turn() effectue le changement de tour correct vers le DÉFENSEUR (Next Player).
        self.turn_manager.end_turn()

    def check_game_over(self):
        """
        Vérifie les conditions de victoire basées sur les PV.
        """
        if self.state.player1.hp <= 0:
            self.state.winner = self.state.player2
            log_info(f"🏆 VICTOIRE : {self.state.player2.name} gagne la partie !")
        elif self.state.player2.hp <= 0:
            self.state.winner = self.state.player1
            log_info(f"🏆 VICTOIRE : {self.state.player1.name} gagne la partie !")

    def put_card_on_board(self, player: Player, card: Card):
        """
        Place une carte sur le plateau et gère les triggers OnPlay / Silence.
        Méthode helper pour PlayCommand et EffectManager (ex: Rez).
        """
        # Note: Cette logique pourrait être dans TurnManager ou EffectManager,
        # mais elle est souvent centrale. Ici on utilise l'EffectManager.

        # 1. Pose physique
        player.board.append(card)

        # 2. Trigger On Play
        # On délègue la vérification "Silence" (Ban) à l'EffectManager
        # (Ou on le fait ici si EffectManager n'a pas de méthode 'check_silence')
        # Pour simplifier, on suppose que l'effet manager gère ça ou on le fait manuellement:

        opponent = self.state.player2 if player == self.state.player1 else self.state.player1
        is_silenced = False
        # (Logique de silence simplifiée)
        from mindbug_engine.core.consts import EffectType
        for opp_card in opponent.board:
            if opp_card.trigger == Trigger.PASSIVE:
                for eff in opp_card.effects:
                    if eff.type == EffectType.BAN and eff.params.get("action") == "TRIGGER_ON_PLAY":
                        is_silenced = True
                        break

        if not is_silenced and card.trigger == Trigger.ON_PLAY:
            self.effect_manager.apply_effect(card, player, opponent)

    def update_board_states(self):
        """Met à jour les mots-clés (Passifs)."""
        # Reset keywords de base
        for p in self.state.players:
            for c in p.board:
                c.refresh_state()

        # Applique les effets continus
        self.effect_manager.apply_passive_effects()

    # =========================================================================
    #  UTILS & IA
    # =========================================================================

    def clone(self):
        """Copie profonde pour l'IA (Simulation)."""
        new_game = MindbugGame.__new__(MindbugGame)
        new_game.verbose = False
        new_game.deck_factory = self.deck_factory  # Stateless
        new_game.state = copy.deepcopy(self.state)

        # Reconstruction des managers liés au nouvel état
        new_game.turn_manager = TurnManager(new_game)
        new_game.query_manager = QueryManager(new_game)
        new_game.combat_manager = CombatManager(new_game)
        new_game.effect_manager = EffectManager(new_game)
        new_game.combat_manager.effect_manager = new_game.effect_manager

        return new_game