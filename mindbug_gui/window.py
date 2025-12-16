import pygame
import threading
import time  # <--- NÉCESSAIRE pour les délais
from constants import FPS_CAP
from mindbug_engine.rules import Phase
from mindbug_engine.logger import log_info, log_debug, log_error
from mindbug_engine.engine import MindbugGame
from .renderer import GameRenderer
from .resource_manager import ResourceManager


class MindbugGUI:
    def __init__(self, config, screen=None):
        self.config = config
        self.clock = pygame.time.Clock()

        if not pygame.get_init():
            pygame.init()

        if screen:
            self.screen = screen
        else:
            w, h = self.config.settings.resolution
            self.screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
            pygame.display.set_caption("Mindbug AI")

        self.res_manager = ResourceManager()

        # Placeholder
        self.game = None
        self.ai_agent = None
        self.renderer = None

        # États UI
        self.viewing_discard_owner = None
        self.is_paused = False
        self.show_curtain = False
        self.last_active_player = None

        # --- NOUVEAUX ÉTATS POUR L'IA & FEEDBACK ---
        self.ai_thinking = False
        self.ai_thread_result = None  # Stocke le résultat brut du thread
        self.ai_pending_move = None  # Stocke le coup en attente d'animation
        self.ai_move_timer = 0  # Timestamp : Quand jouer le coup ?

        self.notification_text = None
        self.notification_end_time = 0

    def set_game(self, game_instance, ai_agent=None):
        self.game = game_instance
        self.ai_agent = ai_agent
        self.renderer = GameRenderer(self.screen, self.game, self.config, self.res_manager)

        self.last_active_player = self.game.active_player

        # Reset complet
        self.ai_thinking = False
        self.ai_thread_result = None
        self.ai_pending_move = None
        self.notification_text = None

        self.viewing_discard_owner = None
        self.is_paused = False
        self.show_curtain = False

        if self.config.game_mode == "HOTSEAT" and not self.config.debug_mode and not self.ai_agent:
            self.show_curtain = True

    def run(self):
        """Boucle principale."""
        running = True
        log_info("--- Démarrage de la boucle graphique ---")

        while running:
            # On récupère le temps actuel pour gérer les délais
            current_time = time.time()

            # 1. Gestion Hotseat
            self._handle_hotseat_turn_change()

            # 2. Gestion des Événements
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "QUIT"
                elif event.type == pygame.VIDEORESIZE:
                    self._handle_resize(event.w, event.h)
                elif self.show_curtain:
                    if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN:
                        self.show_curtain = False
                else:
                    # Input bloqué si l'IA réfléchit OU si un coup est en attente (animation)
                    if not self.ai_thinking and not self.ai_pending_move:
                        action = self._handle_input(event)
                        if action == "MENU": return "MENU"
                        if action == "QUIT": return "QUIT"
                        if action == "REPLAY":
                            # Relance une partie propre
                            self.set_game(MindbugGame(), self.ai_agent)

            # 3. Logique IA (Mise à jour + Application différée)
            if self.game and not self.game.winner:
                self._update_ai(current_time)

            # 4. Gestion Notification (Disparition auto)
            current_notif = self.notification_text
            if current_time > self.notification_end_time:
                current_notif = None

            self._handle_auto_discard_view()

            # 5. Rendu
            if self.renderer:
                self.renderer.render_all(
                    viewing_discard_owner=self.viewing_discard_owner,
                    is_paused=self.is_paused,
                    show_curtain=self.show_curtain,
                    notification=current_notif  # On passe la notif au renderer
                )

                if self.ai_thinking:
                    self._draw_ai_thinking_indicator()

            pygame.display.flip()
            self.clock.tick(FPS_CAP)

        return "MENU"

    # --- HELPERS UI ---

    def _handle_resize(self, w, h):
        self.screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
        if self.renderer:
            self.renderer.handle_resize(w, h)

    def _handle_hotseat_turn_change(self):
        if self.ai_agent: return  # Pas de rideau en PvE

        if getattr(self.config, "game_mode", "HOTSEAT") == "HOTSEAT" and not self.config.debug_mode:
            if self.game.active_player != self.last_active_player:
                self.show_curtain = True
                self.last_active_player = self.game.active_player
                self.viewing_discard_owner = None
                if self.renderer: self.renderer.zoomed_card = None

    def _handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.is_paused:
                    self.is_paused = False
                elif self.viewing_discard_owner:
                    self.viewing_discard_owner = None
                elif self.renderer and self.renderer.zoomed_card:
                    self.renderer.zoomed_card = None
                else:
                    self.is_paused = True
            return None

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 3:
                self._try_zoom_card(pygame.mouse.get_pos())
            elif event.button == 1:
                if self.renderer and self.renderer.zoomed_card:
                    self.renderer.zoomed_card = None
                else:
                    return self._handle_left_click(event.pos)

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 3 and self.renderer:
                self.renderer.zoomed_card = None
        return None

    def _try_zoom_card(self, mouse_pos):
        if not self.renderer: return
        for zone in self.renderer.click_zones:
            if zone["rect"].collidepoint(mouse_pos) and zone["index"] != -1:
                z_type = zone["type"]
                # En PvE, on ne peut pas zoomer la main de l'IA (triche)
                if self.ai_agent and "HAND_P2" in z_type and not self.config.debug_mode:
                    return
                card = self._get_card_from_zone(z_type, zone["index"])
                if card: self.renderer.zoomed_card = card
                return

    def _handle_left_click(self, pos):
        if not self.renderer: return None

        # Si Victoire -> Boutons de fin
        if self.game.winner:
            for zone in self.renderer.click_zones:
                if zone["rect"].collidepoint(pos):
                    if zone["type"] == "BTN_REPLAY": return "REPLAY"
                    if zone["type"] == "BTN_MENU_END": return "MENU"
            return None

        # Bloquer clic pendant tour IA
        if self.ai_agent and self.game.active_player_idx == 1:
            return None

        if self.is_paused:
            for zone in self.renderer.click_zones:
                if zone["rect"].collidepoint(pos):
                    if zone["type"] == "CONFIRM_QUIT": return "MENU"
                    if zone["type"] == "CANCEL_QUIT": self.is_paused = False
            return None

        # Bouton Menu en haut à droite
        for zone in self.renderer.click_zones:
            if zone["type"] == "TOGGLE_MENU" and zone["rect"].collidepoint(pos):
                self.is_paused = True
                return None

        if self.game.winner: return None

        legal_moves = self.game.get_legal_moves()

        for zone in self.renderer.click_zones:
            if zone["rect"].collidepoint(pos):
                action_type = zone["type"]
                idx = zone["index"]

                # Gestion Overlay Défausse
                if self.viewing_discard_owner:
                    if action_type == "OVERLAY_CARD":
                        is_p1 = (self.viewing_discard_owner == self.game.player1)
                        key = "SELECT_DISCARD_P1" if is_p1 else "SELECT_DISCARD_P2"
                        if (key, idx) in legal_moves:
                            self.game.step(key, idx)
                            self.viewing_discard_owner = None
                    continue

                if self.viewing_discard_owner: continue

                # Ouverture Défausse
                if action_type == "DISCARD_PILE_P1":
                    self.viewing_discard_owner = self.game.player1
                    return None
                elif action_type == "DISCARD_PILE_P2":
                    self.viewing_discard_owner = self.game.player2
                    return None

                # Boutons Contextuels
                if action_type == "BTN_MINDBUG" and ("MINDBUG", -1) in legal_moves:
                    self.game.step("MINDBUG", -1)
                    return None
                elif action_type == "BTN_PASS" and ("PASS", -1) in legal_moves:
                    self.game.step("PASS", -1)
                    return None
                elif action_type == "BTN_NO_BLOCK" and ("NO_BLOCK", -1) in legal_moves:
                    self.game.step("NO_BLOCK", -1)
                    return None

                # Cartes (Main / Board)
                engine_action = self._resolve_card_click(action_type, idx, legal_moves)
                if engine_action:
                    self.game.step(engine_action[0], engine_action[1])
                    return None

        if self.viewing_discard_owner:
            self.viewing_discard_owner = None
        return None

    def _resolve_card_click(self, action_type, idx, legal_moves):
        if self.game.phase == Phase.RESOLUTION_CHOICE:
            candidate = (f"SELECT_{action_type}", idx)
            if candidate in legal_moves: return candidate
            return None

        is_p1_zone = "P1" in action_type
        zone_owner = self.game.player1 if is_p1_zone else self.game.player2

        if zone_owner == self.game.active_player:
            if "HAND" in action_type and ("PLAY", idx) in legal_moves:
                return ("PLAY", idx)
            elif "BOARD" in action_type:
                if self.game.phase == Phase.BLOCK_DECISION and ("BLOCK", idx) in legal_moves:
                    return ("BLOCK", idx)
                elif self.game.phase in [Phase.P1_MAIN, Phase.P2_MAIN] and ("ATTACK", idx) in legal_moves:
                    return ("ATTACK", idx)
        return None

    # --- IA LOGIQUE AVEC DÉLAI (TEMPORISATION) ---

    def _update_ai(self, current_time):
        """
        Gère le cycle de vie de l'IA :
        1. Lance le thread de réflexion
        2. Récupère le coup
        3. Affiche une notification
        4. Attend un délai (ex: 1.5s)
        5. Joue le coup
        """
        # Vérification PvE : Si pas d'agent ou tour joueur humain, on sort
        if not self.ai_agent or self.game.active_player_idx != 1 or self.game.winner:
            return

        # ÉTAPE 3 : Exécution du coup après délai
        if self.ai_pending_move:
            if current_time >= self.ai_move_timer:
                move = self.ai_pending_move
                log_info(f"🖥️ [GUI] Application du coup IA différé : {move}")
                try:
                    if move:
                        self.game.step(move[0], move[1])
                    else:
                        self.game.step("PASS", -1)
                except Exception as e:
                    log_error(f"Erreur IA : {e}")

                self.ai_pending_move = None  # On libère la file
            return

        # ÉTAPE 2 : Réception du coup (Fin du thread)
        if not self.ai_thinking:
            if self.ai_thread_result is not None:
                # Le thread a fini, on configure le délai
                move = self.ai_thread_result
                self.ai_thread_result = None  # Reset

                # Configuration du délai et du texte
                delay = 1.0  # Minimum 1 seconde pour lisibilité
                notif = "L'IA joue..."

                if move:
                    if move[0] == "MINDBUG":
                        delay = 3.0  # Délai long pour moment dramatique
                        notif = "⚠️ L'IA UTILISE UN MINDBUG !"
                    elif move[0] == "ATTACK":
                        notif = "⚔️ L'IA ATTAQUE !"
                    elif move[0] == "BLOCK":
                        notif = "🛡️ L'IA BLOQUE !"
                    elif move[0] == "PASS":
                        notif = "L'IA laisse passer."
                    elif move[0] == "PLAY":
                        notif = "L'IA joue une carte."

                # Affichage
                self._show_notification(notif, duration=delay)

                # Mise en attente
                self.ai_pending_move = move
                self.ai_move_timer = current_time + delay

            else:
                # ÉTAPE 1 : Lancement du thread (Si rien en cours)
                self.ai_thinking = True
                threading.Thread(target=self._run_ai_thread).start()

    def _run_ai_thread(self):
        """Exécuté dans un thread séparé pour ne pas freezer l'interface."""
        try:
            # On stocke le résultat dans ai_thread_result
            self.ai_thread_result = self.ai_agent.get_move(self.game)
        except Exception as e:
            log_error(f"🛑 [Thread] CRASH IA : {e}")
            # Fallback en cas de crash
            legal = self.game.get_legal_moves()
            self.ai_thread_result = legal[0] if legal else ("PASS", -1)
        finally:
            # On signale que le calcul est fini
            self.ai_thinking = False

    def _show_notification(self, text, duration=2.0):
        self.notification_text = text
        self.notification_end_time = time.time() + duration

    def _draw_ai_thinking_indicator(self):
        if not self.renderer: return
        font = self.renderer.font_bold
        txt = font.render("Reflexion...", True, (200, 200, 200))
        rect = txt.get_rect(topright=(self.renderer.layout.screen_w - 20, 80))
        bg = rect.inflate(10, 10)
        pygame.draw.rect(self.screen, (0, 0, 0, 200), bg, border_radius=5)
        self.screen.blit(txt, rect)

    # --- UTILITAIRES ---
    def _handle_auto_discard_view(self):
        if self.game.phase == Phase.RESOLUTION_CHOICE and self.game.selection_context:
            candidates = self.game.selection_context.get("candidates", [])
            if candidates and not self.viewing_discard_owner:
                sample = candidates[0]
                if sample in self.game.player1.discard:
                    self.viewing_discard_owner = self.game.player1
                elif sample in self.game.player2.discard:
                    self.viewing_discard_owner = self.game.player2

    def _get_card_from_zone(self, zone_type, index):
        if index == -1: return None
        if "HAND_P1" in zone_type: return self.game.player1.hand[index]
        if "BOARD_P1" in zone_type: return self.game.player1.board[index]
        if "HAND_P2" in zone_type: return self.game.player2.hand[index]
        if "BOARD_P2" in zone_type: return self.game.player2.board[index]
        if "OVERLAY_CARD" in zone_type and self.viewing_discard_owner:
            try:
                return self.viewing_discard_owner.discard[index]
            except IndexError:
                return None
        return None