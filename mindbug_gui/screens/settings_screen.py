import pygame
from typing import List

from mindbug_engine.utils.logger import log_info
# --- GUI BASE & WIDGETS ---
from mindbug_gui.screens.base_screen import BaseScreen
from mindbug_gui.widgets.buttons import Button, Toggle, UIWidget

# --- CONFIG & COLORS ---
from mindbug_gui.core.settings_config import DIFFICULTY_UI_CONFIG
from mindbug_gui.core.colors import (
    TEXT_PRIMARY, TEXT_SECONDARY, ACCENT,
    BTN_SURFACE, BTN_DANGER, BTN_HOVER
)


class SettingsScreen(BaseScreen):
    """
    Écran de configuration du jeu.
    Permet de modifier la difficulté, le mode debug et les sets actifs.
    """

    def __init__(self, app):
        super().__init__(app)
        # Utilisation du nouveau ConfigurationService centralisé
        self.config = app.config
        self.res = app.res_manager

        # Liste typée pour les éléments interactifs
        self.widgets: List[UIWidget] = []

        # Construction de l'interface
        self._init_ui()

    def on_resize(self, w, h):
        """Recalcule la mise en page lors du redimensionnement de la fenêtre."""
        super().on_resize(w, h)
        self._init_ui()

    def _init_ui(self):
        """Génère tous les widgets de l'écran en fonction de l'état actuel de la config."""
        self.widgets.clear()

        cx = self.width // 2
        y = 60
        spacing = 50

        # Récupération des polices via le ResourceManager
        font_title = self.res.get_font(60, bold=True)
        font_sub = self.res.get_font(28, bold=True)
        font_widget = self.res.get_font(24)
        font_small = self.res.get_font(18)

        # 1. TITRE
        self.title_surf = font_title.render("PARAMÈTRES", True, TEXT_PRIMARY)
        self.title_rect = self.title_surf.get_rect(center=(cx, y))
        y += 100

        # 2. SÉLECTION DIFFICULTÉ (Bouton Cycle)
        curr_diff = self.config.ai_difficulty
        # On récupère les métadonnées visuelles (label, couleur)
        ui_data = DIFFICULTY_UI_CONFIG.get(
            curr_diff, DIFFICULTY_UI_CONFIG[next(iter(DIFFICULTY_UI_CONFIG))])

        btn_diff = Button(
            x=cx - 150, y=y, width=300, height=50,
            text=f"NIVEAU : {ui_data['label']}",
            font=font_widget,
            action="CYCLE_DIFF",
            bg_color=BTN_SURFACE,
            text_color=ui_data['color'],
            hover_color=BTN_HOVER
        )
        self.widgets.append(btn_diff)

        # Description sous le bouton de difficulté
        self.desc_surf = font_small.render(
            ui_data['desc'], True, TEXT_SECONDARY)
        self.desc_rect = self.desc_surf.get_rect(center=(cx, y + 40))
        y += 90

        # 3. OPTIONS GLOBALES (Interrupteurs / Toggles)
        # Mode Debug
        tg_debug = Toggle(
            cx=cx, y=y,
            label_text="Mode Debug",
            font=font_widget,
            initial_value=self.config.debug_mode,
            action="TOGGLE_DEBUG"
        )
        self.widgets.append(tg_debug)
        y += spacing

        # Plein Écran
        tg_full = Toggle(
            cx=cx, y=y,
            label_text="Plein Écran",
            font=font_widget,
            initial_value=getattr(self.config, "fullscreen", False),
            action="TOGGLE_FULLSCREEN"
        )
        self.widgets.append(tg_full)
        y += spacing + 20

        # 4. GESTION DES EXTENSIONS (Sets)
        self.sets_title_surf = font_sub.render(
            "EXTENSIONS ACTIVES", True, ACCENT)
        self.sets_title_rect = self.sets_title_surf.get_rect(center=(cx, y))
        y += spacing

        avail = self.config.available_sets_in_db
        active = self.config.active_sets

        if not avail:
            # Fallback si aucune donnée n'est chargée
            self.widgets.append(
                Button(cx - 150, y, 300, 40, "Aucun Set Trouvé", font_widget, None))
            y += spacing
        else:
            for s_id in avail:
                is_active = (s_id in active)
                tg_set = Toggle(
                    cx=cx, y=y,
                    label_text=s_id.replace("_", " ").title(),
                    font=font_widget,
                    initial_value=is_active,
                    action=f"TOGGLE_SET:{s_id}"
                )
                self.widgets.append(tg_set)
                y += spacing

        # 5. PIED DE PAGE (Bouton Retour)
        btn_y = max(y + 30, self.height - 80)
        btn_back = Button(
            x=cx - 100, y=btn_y, width=200, height=50,
            text="RETOUR",
            font=font_widget,
            action="MENU",
            bg_color=BTN_DANGER,
            hover_color=BTN_HOVER
        )
        self.widgets.append(btn_back)

    def handle_events(self, events):
        """Gestion des entrées clavier et souris."""
        for event in events:
            # Raccourci ECHAP pour quitter et sauvegarder
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._save_and_exit()
                return "MENU"

            # Dispatch des événements vers les widgets
            for widget in self.widgets:
                action = widget.handle_event(event)
                if action:
                    return self._process_action(action)
        return None

    def _process_action(self, action: str):
        """Logique interne déclenchée par les clics widgets."""
        if action == "MENU":
            self._save_and_exit()
            return "MENU"

        elif action == "CYCLE_DIFF":
            self._cycle_difficulty()
            return None

        elif action == "TOGGLE_DEBUG":
            self.config.debug_mode = not self.config.debug_mode
            return None

        elif action == "TOGGLE_FULLSCREEN":
            self.config.fullscreen = not self.config.fullscreen
            # Appel à la méthode de l'App pour changer le mode d'affichage
            self.app.apply_display_mode()
            # Recalcul de l'UI pour s'adapter à la nouvelle résolution
            w, h = self.app.screen.get_size()
            self.on_resize(w, h)
            return None

        elif action.startswith("TOGGLE_SET:"):
            set_id = action.split(":")[1]
            is_active = set_id in self.config.active_sets
            self._update_sets_config(set_id, not is_active)
            # On réinitialise l'UI pour valider visuellement le changement (sécurité min 1 set)
            self._init_ui()
            return None

        return None

    def _cycle_difficulty(self):
        """Alterne entre les niveaux de difficulté via la config UI."""
        curr = self.config.ai_difficulty
        if curr in DIFFICULTY_UI_CONFIG:
            self.config.ai_difficulty = DIFFICULTY_UI_CONFIG[curr]["next"]
            self._init_ui()

    def _update_sets_config(self, set_id: str, should_be_active: bool):
        """Met à jour les sets actifs avec une sécurité pour garder au moins 1 set."""
        sets = self.config.active_sets
        if should_be_active:
            if set_id not in sets:
                sets.append(set_id)
        else:
            if set_id in sets and len(sets) > 1:
                sets.remove(set_id)
            else:
                log_info(
                    "⚠️ Action refusée : Au moins un set de cartes doit rester actif.")

    def _save_and_exit(self):
        """Persiste les paramètres via le ConfigurationService avant de quitter."""
        log_info("💾 Sauvegarde des paramètres en cours...")
        self.config.save()

    def update(self, dt):
        """Met à jour l'état de survol des boutons."""
        mouse_pos = pygame.mouse.get_pos()
        for w in self.widgets:
            w.update(dt, mouse_pos)

    def draw(self, surface):
        """Rendu visuel de l'écran."""
        # Titres et labels
        surface.blit(self.title_surf, self.title_rect)
        surface.blit(self.desc_surf, self.desc_rect)
        surface.blit(self.sets_title_surf, self.sets_title_rect)

        # Dessin des widgets
        for w in self.widgets:
            w.draw(surface)

        # Footer versioning
        footer_font = self.res.get_font(14)
        v_txt = footer_font.render(
            "v4.0 - Configuration Centralisée", True, TEXT_SECONDARY)
        surface.blit(v_txt, (15, self.height - 25))
