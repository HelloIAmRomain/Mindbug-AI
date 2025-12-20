import pygame
from math import ceil
from mindbug_gui.screens.base_screen import BaseScreen
from mindbug_gui.widgets.buttons import Button
from mindbug_engine.core.consts import CardStatus
from mindbug_gui.core.colors import (
    TEXT_PRIMARY, BTN_DANGER, BTN_HOVER, BG_COLOR,
    STATUS_OK, STATUS_CRIT, ACCENT
)

# Imports pour le chargement des données
from mindbug_engine.infrastructure.card_loader import CardLoader
from constants import PATH_DATA


class DeckBuilderScreen(BaseScreen):
    """
    Écran de construction de deck.
    Permet de visualiser, forcer (Vert) ou bannir (Rouge) des cartes.
    """

    def __init__(self, app):
        super().__init__(app)

        # --- 1. INITIALISATION CRITIQUE ---
        # On définit les managers AVANT d'appeler _init_ui
        self.settings = app.settings_manager
        self.res = app.res_manager  # <--- C'est cette ligne qui manquait/était mal placée

        # 2. Chargement des données (Pool de cartes)
        if hasattr(app, 'raw_cards') and app.raw_cards:
            self.all_cards = app.raw_cards
        else:
            self.all_cards = CardLoader.load_from_json(PATH_DATA)

        # 3. Layout & Scroll
        self.scroll_y = 0
        self.card_w, self.card_h = 100, 140
        self.margin = 20
        self.cols = 8

        self.widgets = []

        # 4. Construction UI (Maintenant self.res existe !)
        self._init_ui()

    def _init_ui(self):
        self.widgets.clear()

        # Bouton Retour
        btn_back = Button(
            x=20, y=20, width=120, height=40,
            text="RETOUR",
            font=self.res.get_font(20, bold=True),
            action="BACK",
            bg_color=BTN_DANGER,
            hover_color=BTN_HOVER
        )
        self.widgets.append(btn_back)

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: return "BACK"

            # Scroll Molette
            if event.type == pygame.MOUSEWHEEL:
                self.scroll_y += event.y * 20
                self.scroll_y = min(0, self.scroll_y)  # Clamp top

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Widgets
                for w in self.widgets:
                    act = w.handle_event(event)
                    if act == "BACK": return self._exit()

                # Grille Cartes
                self._handle_grid_click(event.pos)

        return None

    def _handle_grid_click(self, pos):
        mx, my = pos
        start_x, start_y = 50, 80 + self.scroll_y

        # Filtrage sets actifs
        active_cards = [c for c in self.all_cards if c.set in self.settings.active_sets]

        for i, card in enumerate(active_cards):
            col = i % self.cols
            row = i // self.cols

            x = start_x + col * (self.card_w + self.margin)
            y = start_y + row * (self.card_h + self.margin)

            rect = pygame.Rect(x, y, self.card_w, self.card_h)
            if rect.collidepoint(mx, my):
                self.settings.cycle_card_status(card.id)
                return

    def _exit(self):
        """Méthode appelée pour quitter l'écran."""
        self.settings.save()
        from mindbug_gui.screens.settings_screen import SettingsScreen
        self.app.set_screen(SettingsScreen(self.app))

    def update(self, dt):
        pass

    def draw(self, surface):
        """
        Rendu de l'écran de construction de deck.
        Groupe les cartes par Set et affiche le quota (x1, x2, BAN) pour chaque ID unique.
        """
        surface.fill(BG_COLOR)

        # 1. Titre fixe
        title_font = self.res.get_font(40, bold=True)
        title_surf = title_font.render("SÉLECTION DES CARTES", True, TEXT_PRIMARY)
        surface.blit(title_surf, (200, 20))

        # 2. Zone de Clip pour le scroll (évite que les cartes débordent sur le titre)
        clip_rect = pygame.Rect(0, 70, self.width, self.height - 70)
        surface.set_clip(clip_rect)

        # Configuration du layout dynamique
        start_x, current_y = 50, 80 + self.scroll_y
        active_sets = sorted(list(self.settings.active_sets))

        font_header = self.res.get_font(28, bold=True)
        font_badge = self.res.get_font(18, bold=True)
        font_small = self.res.get_font(16)

        for s_id in active_sets:
            # Filtrage : On ne garde qu'une instance unique par ID pour l'affichage de la grille
            set_cards = []
            seen_ids = set()
            for c in self.all_cards:
                if c.set == s_id and c.id not in seen_ids:
                    set_cards.append(c)
                    seen_ids.add(c.id)

            if not set_cards:
                continue

            # --- A. EN-TÊTE DU SET ---
            header_surf = font_header.render(f"SET : {s_id.replace('_', ' ')}", True, ACCENT)
            surface.blit(header_surf, (start_x, current_y))
            current_y += 45

            # --- B. GRILLE DES CARTES DU SET ---
            for i, card in enumerate(set_cards):
                col = i % self.cols
                row = i // self.cols
                x = start_x + col * (self.card_w + self.margin)
                y = current_y + row * (self.card_h + self.margin)

                # Culling : Optimisation du rendu (ne dessine que ce qui est visible)
                if y < self.height and y + self.card_h > 0:
                    card_rect = pygame.Rect(x, y, self.card_w, self.card_h)

                    # Récupération du quota configuré (0, 1 ou 2)
                    copies = self.settings.get_card_copies(card.id)

                    # Rendu de l'image (face ou placeholder via ResourceManager)
                    img = self.res.get_card_image(card)
                    if img:
                        scaled_img = pygame.transform.smoothscale(img, (self.card_w, self.card_h))
                        surface.blit(scaled_img, (x, y))

                    # Logique visuelle selon le nombre de copies
                    if copies == 0:
                        border_col = STATUS_CRIT  # Rouge (Banni)
                        # Filtre rouge semi-transparent
                        overlay = pygame.Surface((self.card_w, self.card_h), pygame.SRCALPHA)
                        overlay.fill((200, 50, 50, 150))
                        surface.blit(overlay, (x, y))
                    elif copies == 1:
                        border_col = STATUS_WARN  # Orange/Jaune (1 exemplaire)
                    else:
                        border_col = STATUS_OK  # Vert (2 exemplaires / Standard)

                    # Dessin de la bordure (épaisse si banni ou 1 exemplaire)
                    pygame.draw.rect(surface, border_col, card_rect, 4 if copies < 2 else 2)

                    # Badge de quantité (x1, x2, BAN) en bas à droite
                    count_txt = "BAN" if copies == 0 else f"x{copies}"
                    badge_surf = font_badge.render(count_txt, True, TEXT_PRIMARY)
                    badge_rect = badge_surf.get_rect(bottomright=(x + self.card_w - 5, y + self.card_h - 5))

                    # Petit fond coloré derrière le texte pour la lisibilité
                    pygame.draw.rect(surface, border_col, badge_rect.inflate(8, 4))
                    surface.blit(badge_surf, badge_rect)

            # Calcul du décalage vertical pour le prochain set
            rows_in_set = ceil(len(set_cards) / self.cols)
            current_y += rows_in_set * (self.card_h + self.margin) + 30

        # 3. Nettoyage du clip et rendu de l'UI fixe
        surface.set_clip(None)

        for w in self.widgets:
            w.draw(surface)

        # 4. Statistiques globales (Somme des quotas pour tous les sets actifs)
        total_cards = 0
        banned_count = 0
        for c_id in set(c.id for c in self.all_cards if c.set in self.settings.active_sets):
            q = self.settings.get_card_copies(c_id)
            total_cards += q
            if q == 0:
                banned_count += 1

        stat_txt = font_small.render(f"Total Deck: {total_cards} | IDs Bannis: {banned_count}", True, TEXT_PRIMARY)
        surface.blit(stat_txt, (self.width - 350, 30))