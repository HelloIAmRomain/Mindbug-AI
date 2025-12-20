import pygame
from typing import List

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
        self.config = app.config
        self.res = app.res_manager

        # Liste typée pour l'IDE
        self.widgets: List[UIWidget] = []

        # Construction initiale de l'interface
        self._init_ui()

    def on_resize(self, w, h):
        """Recalcule la mise en page lors du redimensionnement."""
        super().on_resize(w, h)
        self._init_ui()

    def _init_ui(self):
        """Génère tous les widgets de l'écran."""
        self.widgets.clear()

        cx = self.width // 2
        y = 60
        spacing = 50

        # Styles de police
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
        # On récupère les métadonnées (label, couleur) depuis la config statique
        ui_data = DIFFICULTY_UI_CONFIG.get(curr_diff, DIFFICULTY_UI_CONFIG[list(DIFFICULTY_UI_CONFIG.keys())[0]])

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

        # Description sous le bouton
        self.desc_surf = font_small.render(ui_data['desc'], True, TEXT_SECONDARY)
        self.desc_rect = self.desc_surf.get_rect(center=(cx, y + 40))
        y += 90

        # 3. OPTIONS GLOBALES (Toggles)
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

        # Plein Écran (Si supporté par la config)
        if hasattr(self.config, "fullscreen"):
            tg_full = Toggle(
                cx=cx, y=y,
                label_text="Plein Écran",
                font=font_widget,
                initial_value=self.config.fullscreen,
                action="TOGGLE_FULLSCREEN"
            )
            self.widgets.append(tg_full)
            y += spacing

        y += 20  # Espacement section

        # 4. GESTION DES EXTENSIONS (Sets)
        self.sets_title_surf = font_sub.render("EXTENSIONS ACTIVES", True, ACCENT)
        self.sets_title_rect = self.sets_title_surf.get_rect(center=(cx, y))
        y += spacing

        avail = self.config.available_sets_in_db
        active = self.config.active_sets

        if not avail:
            # Cas fallback si aucun fichier chargé
            self.widgets.append(Button(cx - 150, y, 300, 40, "Aucun Set Trouvé", font_widget, None))
            y += spacing
        else:
            for s_id in avail:
                is_active = (s_id in active)
                # On crée un Toggle par set
                tg_set = Toggle(
                    cx=cx, y=y,
                    label_text=s_id.replace("_", " ").title(),  # Joli formatage
                    font=font_widget,
                    initial_value=is_active,
                    action=f"TOGGLE_SET:{s_id}"
                )
                self.widgets.append(tg_set)
                y += spacing

        # 5. PIED DE PAGE (Bouton Retour)
        # On le colle en bas, ou juste après le contenu si l'écran est grand
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
        """Gestion centralisée des événements."""
        for event in events:
            # Raccourci Clavier
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._save_and_exit()
                return "MENU"

            # Gestion Widgets
            for widget in self.widgets:
                action = widget.handle_event(event)

                if action:
                    return self._process_action(action)
        return None

    def _process_action(self, action: str):
        """Logique métier déclenchée par les widgets."""

        if action == "MENU":
            self._save_and_exit()
            return "MENU"

        elif action == "CYCLE_DIFF":
            self._cycle_difficulty()
            return None  # On reste sur l'écran

        elif action == "TOGGLE_DEBUG":
            self.config.debug_mode = not self.config.debug_mode
            # On ne reconstruit pas tout l'UI, le toggle a déjà changé visuellement
            # Mais pour Debug, parfois on veut voir l'effet immédiat, ici pas nécessaire.
            return None



        elif action == "TOGGLE_FULLSCREEN":
            # 1. On met à jour la config (Donnée)
            self.config.fullscreen = not self.config.fullscreen
            # 2. On applique immédiatement le changement graphique (Visuel)
            self.app.apply_display_mode()
            # 3. Comme la taille de l'écran a changé, on force un recalcul de l'UI Settings
            # (Car on_resize a été appelé sur l'app, mais on veut être sûr que le toggle reste centré)
            w, h = self.app.screen.get_size()
            self.on_resize(w, h)
            return None

        elif action.startswith("TOGGLE_SET:"):
            set_id = action.split(":")[1]
            # On inverse l'état dans la config
            # Note : Le widget Toggle a déjà inversé son état visuel (self.value)
            # Il faut juste s'assurer que la config suit.
            is_currently_active = set_id in self.config.active_sets
            self._update_sets_config(set_id, not is_currently_active)

            # Ici on doit recharger l'UI car si l'utilisateur a tenté de désactiver
            # le dernier set, la logique _update_sets_config l'en a peut-être empêché.
            # Le Toggle visuel serait alors "OFF" alors que la config est restée "ON".
            self._init_ui()
            return None

        return None

    def _cycle_difficulty(self):
        """Passe à la difficulté suivante."""
        curr = self.config.ai_difficulty
        if curr in DIFFICULTY_UI_CONFIG:
            next_diff = DIFFICULTY_UI_CONFIG[curr]["next"]
            self.config.ai_difficulty = next_diff
            self._init_ui()  # Refresh pour changer le texte et la couleur du bouton

    def _update_sets_config(self, set_id, should_be_active):
        """Met à jour la liste des sets avec sécurité (min 1 set actif)."""
        sets = self.config.active_sets

        if should_be_active:
            if set_id not in sets:
                sets.append(set_id)
        else:
            # Règle métier : On ne peut pas désactiver le dernier set
            if set_id in sets and len(sets) > 1:
                sets.remove(set_id)
            else:
                print("⚠️ Impossible de désactiver le dernier set.")

    def _save_and_exit(self):
        """Sauvegarde sur le disque en quittant."""
        print("💾 Sauvegarde des paramètres...")
        self.config.save_settings()

    def update(self, dt):
        """Animation et Hover."""
        mouse_pos = pygame.mouse.get_pos()
        for w in self.widgets:
            w.update(dt, mouse_pos)

    def draw(self, surface):
        """Rendu."""
        # Titres
        surface.blit(self.title_surf, self.title_rect)
        surface.blit(self.desc_surf, self.desc_rect)
        surface.blit(self.sets_title_surf, self.sets_title_rect)

        # Widgets
        for w in self.widgets:
            w.draw(surface)

        # Footer version
        v_txt = self.res.get_font(16).render("v3.0 Architecture Propre", True, TEXT_SECONDARY)
        surface.blit(v_txt, (15, self.height - 25))