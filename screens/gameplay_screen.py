import os

from docutils.nodes import row
from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.uix.textinput import TextInput
from kivy.app import App
from kivy.core.window import Window
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Color, RoundedRectangle, Line, Ellipse, Rectangle
from functools import partial
import re

# Importações reais do seu projeto
from core.quest_success_calculator import calculate_success_chance
from core.dialogue_manager import DialogueManager
from core.language_manager import LanguageManager
from core.quest_manager import QuestManager
from core.hero_manager import HeroManager
from core.music_manager import get_music_manager
from core.font_manager import FontManager
import core.save_manager as save

from screens.dialog_box import DialogueBox
from screens.gameplay.hero_popup import show_hero_details
from screens.gameplay.spinner_button import InfoMenuSpinner
from screens.gameplay.chapter_end_popup import show_chapter_end_popup
from screens.responsive_frame import ResponsiveFrame
from screens.gameplay.quest_card import QuestCard


class HeroCard(ButtonBehavior, FloatLayout):

    def __init__(self, hero, quest, pending_assignments, max_heroes,
                 on_selection_changed=None, readonly=False, **kwargs):
        super().__init__(**kwargs)
        font_name = StringProperty("NotoSans")


        self.readonly = readonly

        self.lm = LanguageManager()
        self.hero = hero
        self.quest = quest
        self.pending_assignments = pending_assignments
        self.max_heroes = max_heroes
        self.on_selection_changed = on_selection_changed  # callback p/ update_success_label
        self.selected = False
        self.rf = ResponsiveFrame()

        self.size_hint = (None, None)
        self.size = self.rf.hero_card_size

        # ── BACKGROUND ────────────────────────────────
        self._draw_background()
        self.bind(pos=self._update_graphics, size=self._update_graphics)

        # ── PORTRAIT ──────────────────────────────────
        portrait = Image(
            source=hero.photo_url or 'assets/img/default_hero.png',
            size_hint=(0.9, 0.65),
            pos_hint={"center_x": 0.5, "top": 0.98},
            allow_stretch=True,
            keep_ratio=True,
        )
        self.add_widget(portrait)

        # ── INFO BUTTON ───────────────────────────────
        info_btn = Button(
            size_hint=(None, None),
            size=(28, 28),
            pos_hint={"right": 0.98, "top": 0.98},
            background_normal='assets/buttons/info.png',
            background_down='assets/buttons/info_pressed.png',
            background_color=(1, 1, 1, 1),
            border=(0, 0, 0, 0),
        )
        info_btn.bind(on_release=lambda *_: show_hero_details(
            self, hero, self.rf.size
        ))
        self.add_widget(info_btn)

        role_source = f'assets/img/{hero.role}.png'
        if not os.path.exists(role_source):
            role_source = 'assets/img/default_role.png'

        role_ico = Image(
            size_hint=(None, None),
            size=(28, 28),
            pos_hint={"x": 0.02, "top": 0.98},
            source=role_source,
            allow_stretch=True,
            keep_ratio=True,
        )
        self.add_widget(role_ico)

        # ── NAME ──────────────────────────────────────
        self.add_widget(Label(
            text=hero.name,
            size_hint=(1, None),
            height=24,
            pos_hint={"center_x": 0.5, "y": 0.18},
            bold=True,
            color=(1, 1, 1, 1),
        ))

        # ── LEVEL ─────────────────────────────────────
        self.add_widget(Label(
            text=f"{self.lm.t('level_short')}: {hero.level}",
            size_hint=(1, None),
            height=20,
            pos_hint={"center_x": 0.5, "y": 0.08},
            color=(0.8, 0.8, 0.8, 1),
        ))

    # ── CANVAS ────────────────────────────────────────────
    def _draw_background(self):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.15, 0.15, 0.15, 0.85)
            self.bg = Ellipse(pos=self.pos, size=self.size)
            if self.selected:
                Color(0.9, 0.7, 0.2, 1)   # dourado = selecionado
            else:
                Color(0.5, 0.5, 0.5, 1)   # cinza = normal
            self.border = Line(
                ellipse=(self.x, self.y, self.width, self.height),
                width=2,
            )

    def _update_graphics(self, *_):
        self.bg.pos  = self.pos
        self.bg.size = self.size
        self.border.ellipse = (self.x, self.y, self.width, self.height)

    # ── SELEÇÃO ───────────────────────────────────────────
    def on_release(self):
        if self.readonly:
            return 

        quest_id = self.quest.id
        selected = self.pending_assignments.setdefault(quest_id, [])

        if self.hero.id in selected:
            # ── deseleciona ──
            selected.remove(self.hero.id)
            self.selected = False
        else:
            # ── limite atingido ──
            if len(selected) >= self.max_heroes:
                # dispara log via callback sem travar o card
                if self.on_selection_changed:
                    self.on_selection_changed(limit_reached=True)
                return
            selected.append(self.hero.id)
            self.selected = True

        self._draw_background()

        if self.on_selection_changed:
            self.on_selection_changed()

class GameplayScreen(Screen):
    previous_screen = StringProperty("settings")

    def __init__(self, **kwargs):
        super(GameplayScreen, self).__init__(**kwargs)
        self.first_time_entering = True
        self.pending_assignments = {}
        self.pause_popup = None
        self.save_popup = None
        self.coming_from_load = False   # ← padrão explícito
        self.coming_from_settings = False   # ← padrão explícito

        # Simulando o self.ids para manter compatibilidade com o código original
        self.ui_elements = {}

    def build_ui(self):
        self.clear_widgets()  # Limpa a tela antes de construir a UI
        # Layout base com fundo geral
        root_float = FloatLayout()

        # Responsive Frame (Centralizado)
        self.main_layout = BoxLayout(orientation="vertical", size_hint_x=self.rf.main_width, pos_hint={"center_x": 0.5, "center_y": 0.5})
        
        top_row = BoxLayout(orientation="horizontal", size_hint_y=0.1)
        bottom_row = BoxLayout(orientation="horizontal", size_hint_y=0.9)
        self.main_layout.add_widget(top_row)
        self.main_layout.add_widget(bottom_row)

        # 1. Turn Log (Topo)
        self.ui_elements['turn_log'] = BoxLayout(orientation="horizontal", padding=(16, 5, 16, 5), spacing=8)
        with self.ui_elements['turn_log'].canvas.before:
            Color(1, 1, 1, 1)
            self.turn_bg = Rectangle(source="assets/background_ls.png")
        self.ui_elements['turn_log'].bind(pos=self._update_turn_bg, size=self._update_turn_bg)
        top_row.add_widget(self.ui_elements['turn_log'])

        # --- PARTE ESQUERDA (65%) ---
        left_column = BoxLayout(orientation="vertical", size_hint_x=0.65)

        # 2. Quest Details (Centro)
        details_area = BoxLayout(orientation="horizontal", size_hint_y=0.6)
        with details_area.canvas.before:
            Color(1, 1, 1, 1)
            self.details_bg = Rectangle(source="assets/background_gameplay.png")
        details_area.bind(pos=self._update_details_bg, size=self._update_details_bg)
        
        self.ui_elements['quest_details'] = BoxLayout(orientation="horizontal", padding=self.rf.padding_resp, spacing=5)
        details_area.add_widget(self.ui_elements['quest_details'])
        left_column.add_widget(details_area)
        
        # 3. Mission Log (Base)
        log_area = BoxLayout(orientation="vertical", size_hint_y=0.2, padding=10)
        with log_area.canvas.before:
            Color(1, 1, 1, 1)
            self.log_bg = Rectangle(source="assets/background_ls.png")
        log_area.bind(pos=self._update_log_bg, size=self._update_log_bg)
        
        log_title = Label(text=self.lm.t("mission_log"), font_size=self.rf.font_title, size_hint_y=None, height=16, color=(0,0,0,1))
        log_area.add_widget(log_title)
        
        self.ui_elements['mission_scroll'] = ScrollView(do_scroll_x=False, do_scroll_y=True)
        self.ui_elements['mission_log'] = BoxLayout(orientation="vertical", size_hint_y=None)
        self.ui_elements['mission_log'].bind(minimum_height=self.ui_elements['mission_log'].setter('height'))
        self.ui_elements['mission_scroll'].add_widget(self.ui_elements['mission_log'])
        log_area.add_widget(self.ui_elements['mission_scroll'])
        left_column.add_widget(log_area)
        
        bottom_row.add_widget(left_column)
        
        # --- SIDEBAR DIREITA (30%) ---
        sidebar = BoxLayout(orientation="vertical", size_hint_x=0.35, padding=self.rf.padding_resp, spacing=5)
        with sidebar.canvas.before:
            Color(1, 1, 1, 1)
            self.sidebar_bg = Rectangle(source="assets/background.png")
        sidebar.bind(pos=self._update_sidebar_bg, size=self._update_sidebar_bg)
        
        # Seção Quests Ativas
        sidebar.add_widget(Label(text=self.lm.t('active_quests'), size_hint_y=None, height=30, color=(0,0,0,1)))
        active_scroll = ScrollView(size_hint_y=0.45)
        self.ui_elements['active_quests'] = BoxLayout(orientation="vertical", size_hint_y=None, spacing=5)
        self.ui_elements['active_quests'].bind(minimum_height=self.ui_elements['active_quests'].setter('height'))
        active_scroll.add_widget(self.ui_elements['active_quests'])
        sidebar.add_widget(active_scroll)
        
        # Seção Quests Disponíveis
        sidebar.add_widget(Label(text=self.lm.t('available_quests'), size_hint_y=None, height=30, color=(0,0,0,1)))
        available_scroll = ScrollView(size_hint_y=0.45)
        self.ui_elements['available_quests'] = BoxLayout(orientation="vertical", size_hint_y=None, spacing=5)
        self.ui_elements['available_quests'].bind(minimum_height=self.ui_elements['available_quests'].setter('height'))
        available_scroll.add_widget(self.ui_elements['available_quests'])
        sidebar.add_widget(available_scroll)
        
        # Seção Quests Concluídas
        sidebar.add_widget(Label(text="Menu", size_hint_y=None, height=30, color=(0,0,0,1)))
        self.ui_elements['completed_quests'] = BoxLayout(orientation="horizontal", size_hint_y=0.1, spacing=5)
        sidebar.add_widget(self.ui_elements['completed_quests'])
        
        bottom_row.add_widget(sidebar)
        root_float.add_widget(self.main_layout)
        self.add_widget(root_float)

    # --- Funções de Atualização de Background ---
    def _update_bg(self, instance, value): self.bg_rect.size = value; self.bg_rect.pos = instance.pos
    def _update_turn_bg(self, instance, value): self.turn_bg.pos = instance.pos; self.turn_bg.size = instance.size
    def _update_details_bg(self, instance, value): self.details_bg.pos = instance.pos; self.details_bg.size = instance.size
    def _update_log_bg(self, instance, value): self.log_bg.pos = instance.pos; self.log_bg.size = instance.size
    def _update_sidebar_bg(self, instance, value): self.sidebar_bg.pos = instance.pos; self.sidebar_bg.size = instance.size

    @property
    def ids(self): return self.ui_elements

    # --- LÓGICA ORIGINAL INTEGRADA ---
    def on_pre_enter(self):
        self.rf = ResponsiveFrame()
        self.lm = LanguageManager()
        self.dm = DialogueManager(language=self.lm.language)
        self.dialog_box = DialogueBox(self.dm)
        self.info_menu = InfoMenuSpinner(manager_instance=self)

        FontManager.register_fonts()
        # ✅ Define fonte inicial baseada no idioma
        self.font_name = FontManager.get_font_for_language(self.lm.language)


        self.build_ui()

    def on_enter(self):
        if getattr(self, 'coming_from_load', False) or getattr(self, 'coming_from_settings', False):
            # print("[GameplayScreen] Carregando a partir de um save existente. Pulando inicialização padrão.")
            # Reseta a flag para os próximos acessos comuns
            self.coming_from_load = False 
            self.coming_from_settings = False
        else:
            # Inicialização padrão para um "Novo Jogo"
            # print("[GameplayScreen] Iniciando um novo jogo.")
            self.quest_manager = QuestManager()
            self.hero_manager = self.quest_manager.hero_manager
            
            # Executa apenas diálogos ou lógicas iniciais de um novo jogo aqui...
            if hasattr(self.quest_manager, 'assistant'):
                self.quest_manager.assistant.first_time = True
                
        self.quest_manager.hero_manager.check_hero_unlocks(self.quest_manager.completed_quests, self.quest_manager.current_turn)

        if self.quest_manager.assistant:
            self.quest_manager.assistant.dialogue_box = self.dialog_box

        self.quest_manager.set_dialog_callback(self.open_dialog)
        self.quest_manager.set_ui_callback(self.update_ui)
        self.quest_manager.set_log_callback(self.update_log)

        self.active_quests_label = self.lm.t("active_quests")
        self.available_quests_label = self.lm.t("available_quests")
        self.log_messages = self.lm.t("log_messages")

        if self.first_time_entering and not self.coming_from_settings and not self.coming_from_load:
            self.quest_manager.assistant.on_game_start()
            self.first_time_entering = False
        elif self.coming_from_load:
            self.quest_manager.assistant.on_game_start()

        self.update_sidebar()
        self.turn_bar()
        Window.bind(on_key_down=self._on_key_down)
        self.music = get_music_manager()
        self.music.play()
        if not self.music.is_playing and self.music.current_sound:
            self.music.resume()

    def on_leave(self):
        try: Window.unbind(on_key_down=self._on_key_down)
        except Exception: pass

    def _on_key_down(self, window, key, scancode, codepoint, modifiers):
        if key == 27: self.open_pause_menu(); return True
        return False

    def update_log(self, message):
        log_widget = self.ids['mission_log']
        label = Label(text=message, size_hint_y=None, height=30, color=(0,0,0,1), halign='left', text_size=(log_widget.width, None), font_size=self.rf.font_xl)
        label.bind(
            texture_size=lambda *_:
            setattr(label, "height", label.texture_size[1])
        )
        Clock.schedule_once(lambda dt: setattr(self.ids['mission_scroll'], "scroll_y", 0), 0.5)
        log_widget.add_widget(label)

    def turn_bar(self):

        turn_widget = self.ids['turn_log']
        turn_widget.clear_widgets()

        # ==================================================
        # TURN PANEL
        # ==================================================

        turn_panel = BoxLayout(
            orientation="vertical",
            size_hint_x=0.09,
            padding=6
        )

        turn_title = Label(
            text=self.lm.t("turn_label"),
            color=(0, 0, 0, 1),
            font_size=self.rf.font_title,
            halign="left"
        )

        turn_number = Label(
            text=str(self.quest_manager.current_turn),
            color=(0, 0, 0, 1),
            bold=True,
            font_size=self.rf.font_title
        )

        turn_panel.add_widget(turn_title)
        turn_panel.add_widget(turn_number)

        # ==================================================
        # QUEST PANEL
        # ==================================================

        quest_panel = BoxLayout(
            orientation="vertical",
            size_hint_x=0.63,
            padding=6,
            spacing=2
        )

        quest_label = Label(
            text=self.lm.t("selected_quest_label"),
            color=(0.35, 0.25, 0.15, 1),
            font_size=self.rf.font_title,
            halign="left",
            size_hint_y=0.3
        )

        self.quest_title = Label(
            text="--",
            color=(0, 0, 0, 1),
            bold=True,
            font_size=self.rf.font_title,
            halign="left",
            size_hint_y=0.7
        )

        quest_panel.add_widget(quest_label)
        quest_panel.add_widget(self.quest_title)

        # ==================================================
        # DANGER PANEL
        # ==================================================

        difficulty_panel = BoxLayout(
            orientation="vertical",
            size_hint_x=0.12,
            padding=6
        )

        diff_label = Label(
            text=self.lm.t("difficulty_label"),
            color=(0.35, 0.25, 0.15, 1),
            font_size=self.rf.font_title
        )

        self.diff_value = Label(
            text="--",
            color=(0.8, 0.35, 0.1, 1),
            bold=True,
            font_size=self.rf.font_title
        )

        difficulty_panel.add_widget(diff_label)
        difficulty_panel.add_widget(self.diff_value)

        # ==================================================
        # ADVANCE BUTTON
        # ==================================================

        advance_button = Button(
            text=self.lm.t("advance_turn_btn"),
            border=(0,0,0,0),
            background_normal="assets/buttons/button.png",
            size_hint_x=0.18,
            on_release=lambda *_: self.advance_turn()
        )

        # ==================================================
        # ADD
        # ==================================================

        turn_widget.add_widget(turn_panel)
        turn_widget.add_widget(quest_panel)
        turn_widget.add_widget(difficulty_panel)
        turn_widget.add_widget(advance_button)

    def advance_turn(self, *_):
        self.quest_manager.advance_turn()
        self.ids['quest_details'].clear_widgets()
        # if self.quest_manager.current_turn > 150:
        #     show_chapter_end_popup(self, chapter_name=self.lm.t("chapter_1_complete"))
        #     return
        self.update_sidebar()
        self.turn_bar()

    def update_sidebar(self):

        self.ids['active_quests'].clear_widgets()
        self.ids['available_quests'].clear_widgets()
        self.ids['completed_quests'].clear_widgets()

        # for quest in self.quest_manager.get_active_quests():
        #     self.ids['active_quests'].add_widget(Button(text=quest.name, size_hint_y=None, height=45, on_release=partial(self.show_active_quest_details, quest)))

        for quest in self.quest_manager.get_active_quests():
            card = QuestCard(
                quest=quest,
                lm=self.lm,
                on_press=self.show_active_quest_details,
                rf=self.rf,
            )
            self.ids['active_quests'].add_widget(card)

        for quest in self.quest_manager.get_available_quests():
            card = QuestCard(
                quest=quest,
                lm=self.lm,
                on_press=self.show_quest_details,
                rf=self.rf,
            )
            self.ids['available_quests'].add_widget(card)

        # for quest in self.quest_manager.get_available_quests():
            # self.ids['available_quests'].add_widget(Button(text=quest.name, size_hint_y=None, height=45, on_release=partial(self.show_quest_details, quest)))

        info_spinner = self.info_menu.create_menu_spinner()
        self.ids['completed_quests'].add_widget(info_spinner)
        gear_btn = Button(            text="",
            size_hint=(None, None),
            size=(40, 40),
            background_normal="assets/buttons/gear.png",
            background_down="assets/buttons/gear.png",
            background_disabled_normal="assets/buttons/gear.png",
            border=(0, 0, 0, 0),
            on_release=lambda *_: self.open_pause_menu()
            )
        self.ids['completed_quests'].add_widget(gear_btn)

    def show_quest_details(self, quest, *_):
        container = self.ids['quest_details']
        container.clear_widgets()
        self.pending_assignments[quest.id] = []


        quest_left_panel = BoxLayout(
            orientation="vertical",
            size_hint_x=0.40
            )
        quest_right_panel = BoxLayout(
            orientation="vertical",
            size_hint_x=0.60
        )

        # ═══════════════════════════════════════
        # TAXA DE SUCESSO
        # ═══════════════════════════════════════

        self.update_topbar(quest)

        # Descrição
        quest_desc = Label(
            text=f"{self.lm.t('description_label')}",
            color=(0,0,0,1),
            size_hint_y=0.07,
            halign="left",
            valign="top",
            font_size=self.rf.font_title
        )
        desc = Label(
            text=quest.description,
            color=(0,0,0,1),
            size_hint_y=None,
            halign="left",
            valign="top",
            font_size=self.rf.font_title
        )

        def update_desc_size(*_):
            desc.text_size = (quest_left_panel.width * 0.95, None)
            desc.texture_update()
            desc.height = desc.texture_size[1]

        quest_left_panel.bind(width=update_desc_size)

        update_desc_size()

        quest_left_panel.add_widget(quest_desc)
        desc_scroll = ScrollView(size_hint=(1, 1))
        desc_scroll.add_widget(desc)
        quest_left_panel.add_widget(desc_scroll)

        self.success_title = Label(
            text=f"{self.lm.t('success_rate')}:",
            color=(0, 0, 0, 1),
            size_hint_y=None,
            height=22,
            font_size=self.rf.font_title
        )
        self.success_label = Label(
            text="--",
            color=(0, 0, 0, 1),
            size_hint_y=None,
            height=22,
            font_size=self.rf.font_title
        )
        quest_left_panel.add_widget(self.success_title)
        quest_left_panel.add_widget(self.success_label)

        # ═══════════════════════════════════════
        # 🎯 DADOS DA QUEST
        # ═══════════════════════════════════════
        quest_types = self._parse_quest_types(quest.type)
        is_combat = "fight" in quest_types

        self.max_heroes = getattr(quest, "max_heroes", 1)
        recommended = getattr(quest, "recommended_heroes", 1)
       
        # Tipos e Dificuldade
        quest_types = self._parse_quest_types(quest.type)
        type_text = ", ".join(self.lm.t(qtype) for qtype in quest_types)

        max_heroes_label = Label(
            text=f"{self.lm.t('max_heroes')}: {self.max_heroes}",
            color=(0, 0, 0, 1),
            size_hint_y=None,
            height=self.rf.font_xl * 1.2,
            font_size=self.rf.font_xl
        )

        type_label = Label(
            text=f"{self.lm.t('type_label')}: {type_text}",
            color=(0, 0, 0, 1),
            size_hint_y=None,
            height=self.rf.font_xl * 1.2,
            font_size=self.rf.font_xl
        )

        turns_label = Label(
            text=f"{self.lm.t('duration')}: {quest.duration} {self.lm.t('turns')}",
            color=(0, 0, 0, 1),
            size_hint_y=None,
            height=self.rf.font_xl * 1.2,
            font_size=self.rf.font_xl
        )


        # ═══════════════════════════════════════
        # 🎯 HERÓIS ELEGÍVEIS
        # ═══════════════════════════════════════
        if is_combat:
            eligible_heroes = self._get_combat_eligible_heroes()
        else:
            eligible_heroes = self._filter_heroes_by_quest_type(quest_types)

        # ═══════════════════════════════════════
        # LISTA DE HERÓIS
        # ═══════════════════════════════════════
        quest_right_panel.add_widget(Label(
            text=self.lm.t("available_heroes"),
            bold=True,
            color=(0, 0, 0, 1),
            size_hint_y=None,
            height=25,
            font_size=self.rf.font_title
        ))
        if len(eligible_heroes) < 4:
            hero_cols = len(eligible_heroes)
        else:
            hero_cols = 3

        heroes_box = GridLayout(
            cols=hero_cols,
            size_hint_y=None
        )
        heroes_box.bind(minimum_height=heroes_box.setter("height"))

        if not eligible_heroes:
            heroes_box.add_widget(Label(
                text=self.lm.t("no_eligible_heroes"),
                color=(0.8, 0, 0, 1),
                size_hint_y=None,
                height=40,
                font_size=self.rf.font_title
            ))
        else:
            for hero in eligible_heroes:
                heroes_box.add_widget(
                    self._create_hero_card(hero, quest)
                    # self._create_hero_row(hero, quest, is_combat)
                )

        scroll = ScrollView(size_hint_y=0.4)
        scroll.add_widget(heroes_box)
        quest_right_panel.add_widget(scroll)

        quest_right_panel.add_widget(max_heroes_label)
        quest_right_panel.add_widget(type_label)
        quest_right_panel.add_widget(turns_label)

        # Botão Enviar
        quest_right_panel.add_widget(Button(
            text=self.lm.t("send_to_quest_btn"),
            background_normal='assets/buttons/Button3.png',
            size_hint_y=None,
            border=(0,0,0,0),
            height=50,
            on_release=lambda *_: self.start_quest(quest)
            ))
        container.add_widget(quest_left_panel)
        container.add_widget(quest_right_panel)

    def _parse_quest_types(self, qtype):
        if isinstance(qtype, list): return [str(t).strip().lower() for t in qtype]
        if isinstance(qtype, str): return [t.strip().lower() for t in qtype.split("+")] if "+" in qtype else [qtype.strip().lower()]
        return []

    def start_quest(self, quest):
        hero_ids = self.pending_assignments.get(quest.id, [])
        if not hero_ids:
            self.quest_manager._log(self.lm.t("no_hero_selected"))
            return
        self.quest_manager.send_heroes_on_quest(quest.id, hero_ids)
        self.pending_assignments.pop(quest.id, None)
        self.ids['quest_details'].clear_widgets()
        self.update_sidebar()
        self.turn_bar()

    def open_dialog(self, selected_heroes, quest, result, quest_type, quest_context):
        # Aqui você só chama a função passando heróis, quest_id e resultado
        self.dialog_box.show_dialogue(selected_heroes,
                                      quest,
                                      result,
                                      parent_size=self.size,
                                      quest_type=quest_type,
                                      context=quest_context)


    # Métodos de navegação e salvamento (mantidos do original)
    def update_ui(self): self.update_sidebar(); self.turn_bar()

    def open_pause_menu(self):
        if self.pause_popup and self.pause_popup.parent:
            self.pause_popup.dismiss()
            self.pause_popup = None
            return

        content = BoxLayout(orientation="vertical", spacing=10, padding=10)

        btn_save = Button(
            text=self.lm.t("save_game"),
            background_normal="assets/buttons/button.png",
            border=(0,0,0,0),
            size_hint_y=None,
            height=48
        )
        btn_save.bind(on_release=self.save_and_close_popup)
        content.add_widget(btn_save)

        btn_load = Button(
            text=self.lm.t("load_game"),
            background_normal="assets/buttons/button.png",
            border=(0,0,0,0),
            size_hint_y=None,
            height=48
        )
        btn_load.bind(on_release=self.load_and_close_popup)
        content.add_widget(btn_load)

        btn_settings = Button(
            text=self.lm.t("settings_title"),
            background_normal="assets/buttons/button.png",
            border=(0,0,0,0),
            size_hint_y=None,
            height=48
        )
        btn_settings.bind(on_release=self.open_settings)
        content.add_widget(btn_settings)

        btn_menu = Button(
            text=self.lm.t("back_to_menu"),
            background_normal="assets/buttons/button.png",
            border=(0,0,0,0),
            size_hint_y=None,
            height=48
        )
        btn_menu.bind(on_release=self.goto_menu)
        content.add_widget(btn_menu)

        btn_quit = Button(
            text=self.lm.t("quit_game"),
            background_normal="assets/buttons/button.png",
            border=(0,0,0,0),
            size_hint_y=None,
            height=48
        )
        btn_quit.bind(on_release=lambda *_: App.get_running_app().stop())
        content.add_widget(btn_quit)

        # guarda no self para poder dar .dismiss() depois
        self.pause_popup = Popup(title=self.lm.t("pause_menu_title"),
                                content=content, 
                                size_hint=(None, None),
                                size=(300, 360),
                                background="assets/background.png",
                                separator_height=0,
                                title_color=(0, 0, 0, 1)
                                )
        self.pause_popup.open()

    def save_and_close_popup(self, *args):
        if getattr(self, "pause_popup", None):
            try:
                self.pause_popup.dismiss()
            except Exception:
                pass
            self.pause_popup = None

        box = BoxLayout(orientation="vertical", spacing=8, padding=10)

        input_name = TextInput(
            hint_text=self.lm.t("save_name_hint"),
            multiline=False,
            size_hint_y=None,
            height=40,
            input_filter=self.safe_input_filter
        )
        box.add_widget(input_name)

        existing_saves = save.list_saves()

        if existing_saves:
            box.add_widget(Label(
                text=self.lm.t("existing_saves"),
                color=(0, 0, 0, 1),
                size_hint_y=None,
                height=25
            ))

            saves_scroll = ScrollView(size_hint=(1, 1))
            saves_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=5)
            saves_box.bind(minimum_height=saves_box.setter("height"))

            for save_name in existing_saves:
                btn = Button(
                    text=save_name,
                    background_normal="assets/buttons/button.png",
                    border=(0,0,0,0),
                    size_hint_y=None,
                    height=40,
                    on_release=lambda btn, name=save_name: setattr(
                        input_name, "text", name.replace(".json", "")
                    )
                )
                saves_box.add_widget(btn)

            saves_scroll.add_widget(saves_box)
            box.add_widget(saves_scroll)

        btns = BoxLayout(size_hint_y=None, height=35, spacing=5)
        btns.add_widget(Button(
            background_normal="assets/buttons/button.png",
            border=(0,0,0,0),
            text=self.lm.t("save"),
            on_release=lambda *_: self.confirm_save(input_name.text)
        ))
        btns.add_widget(Button(
            background_normal="assets/buttons/button.png",
            border=(0,0,0,0),
            text=self.lm.t("cancel"),
            on_release=lambda *_: popup.dismiss()
        ))
        box.add_widget(btns)

        popup = Popup(
            title=self.lm.t("save_game"),
            title_color=(0, 0, 0, 1),
            content=box,
            size_hint=(0.6, 0.6),
            auto_dismiss=False,
            padding=10,
            background="assets/background_ls.png",
        )
        popup.open()
        self.save_popup = popup

    def confirm_save(self, filename):
        if not re.match(r"^[A-Za-z0-9_]+$", filename):
            self.quest_manager._log(self.lm.t("invalid_name"))
            return

        save_exists = filename in save.list_saves()
        filename_json = f"{filename}.json"

        save.save_game(self.quest_manager, filename_json)

        if save_exists:
            self.quest_manager._log(self.lm.t("game_overwritten").format(filename=filename_json))
        else:
            self.quest_manager._log(self.lm.t("game_saved").format(filename=filename_json))

        if getattr(self, "save_popup", None):
            try:
                self.save_popup.dismiss()
            except Exception:
                pass
            self.save_popup = None

    def load_and_close_popup(self, *args):
        if self.pause_popup:
            self.pause_popup.dismiss()
            self.pause_popup = None
        
        elif getattr(self, "pause_popup", None):
            try:
                self.pause_popup.dismiss()
            except Exception:
                pass
            self.pause_popup = None

        load_screen = self.manager.get_screen("loadgame")
        load_screen.previous_screen = "gameplay"
        self.manager.current = "loadgame"

    def open_settings(self, *args):
        if getattr(self, "pause_popup", None):
            try:
                self.pause_popup.dismiss()
                self.music.stop()
            except Exception:
                pass
            self.pause_popup = None

        settings = self.manager.get_screen("settings")
        settings.previous_screen = "gameplay"
        self.manager.current = "settings"

    def goto_menu(self, *args):
        # fecha popup se necessário
        if getattr(self, "pause_popup", None):
            try:
                self.pause_popup.dismiss()
                self.music.stop()
            except Exception:
                pass
            self.pause_popup = None

        # volta ao menu principal
        self.manager.current = "menu"

    def show_completed_quests_popup(self, *_):
        """Abre um popup listando as quests completas e permite ver detalhes."""

        # === Popup principal ===
        main_layout = BoxLayout(orientation="horizontal", spacing=15, padding=10)

        # === LISTA LATERAL (esquerda) ===
        quest_list_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=5)
        quest_list_box.bind(minimum_height=quest_list_box.setter('height'))
        
        quest_scroll = ScrollView(size_hint=(0.35, 1))
        quest_scroll.add_widget(quest_list_box)

        # === ÁREA DE DETALHES (direita) ===
        details_container = BoxLayout(orientation="vertical", spacing=5)
        
        # Título da quest selecionada (topo)
        quest_title_label = Label(
            text="",
            color=(0, 0, 0, 1),
            font_size=24,
            bold=True,
            markup=True,
            halign="left",
            valign="top",
            size_hint_y=None,
            height=60
        )
        quest_title_label.bind(size=lambda instance, value: setattr(instance, 'text_size', (value[0], None)))
        
        # ScrollView para a descrição (caso seja longa)
        details_scroll = ScrollView(size_hint=(1, 1))
        
        details_label = Label(
            text=self.lm.t("select_quest_to_view"),
            color=(0, 0, 0, 1),
            font_size=self.rf.font_title,
            halign="left",
            valign="top",
            size_hint_y=None
        )
        details_label.bind(
            texture_size=lambda instance, value: setattr(instance, 'height', value[1])
        )
        details_label.bind(
            size=lambda instance, value: setattr(instance, 'text_size', (value[0] - 20, None))
        )
        
        details_scroll.add_widget(details_label)
        
        # Adiciona título e scroll ao container
        details_container.add_widget(quest_title_label)
        details_container.add_widget(details_scroll)

        main_layout.add_widget(quest_scroll)
        main_layout.add_widget(details_container)

        # === Função interna para atualizar detalhes ===
        def show_details(quest):
            # Atualiza o título
            quest_title_label.text = f"[b]{quest.name}[/b]"
            
            # Pega os heróis que completaram essa quest
            hero_ids = self.quest_manager.completed_quests.get(quest.id, set())
            
            # Monta a lista de nomes dos heróis
            hero_names = []
            if hero_ids:
                for hero_id in hero_ids:
                    hero = self.quest_manager.hero_manager.get_hero_by_id(hero_id)
                    if hero:
                        hero_names.append(hero.name)
            
            # Formata o texto dos heróis
            if hero_names:
                heroes_text = f"[b]{self.lm.t('completed_by')}:[/b] {', '.join(hero_names)}\n\n"
            else:
                heroes_text = ""
            
            # Atualiza os detalhes
            quest_types = quest.type if isinstance(quest.type, list) else [quest.type]
            type_text = ", ".join(self.lm.t(qtype) for qtype in quest_types)

            details_label.text = (
                f"[b]{self.lm.t('type_label')}:[/b] {type_text}\n"
                f"[b]{self.lm.t('difficulty_label')}:[/b] {quest.difficulty}\n\n"
                f"{heroes_text}"
                f"{quest.description}"
            )
            details_label.markup = True

        # === Preenche a lista de quests ===
        completed = self.quest_manager.completed_quests
        if not completed:
            quest_list_box.add_widget(Label(
                text=self.lm.t("no_completed_quests"),
                color=(0, 0, 0, 1),
                size_hint_y=None,
                height=30,
            ))
        else:
            for qid in completed:
                q = self.quest_manager.get_quest(qid)
                if q:
                    btn = Button(
                        text=q.name,
                        background_normal="assets/buttons/button.png",
                        border=(0,0,0,0),
                        size_hint_y=None,
                        height=50,
                        background_color=(0.9, 0.85, 0.7, 1),
                        on_release=lambda *_, quest=q: show_details(quest)
                    )
                    quest_list_box.add_widget(btn)

        # === Cria o popup ===
        popup = Popup(
            title=self.lm.t("completed_quests_title"),
            content=main_layout,
            size_hint=(None, None),
            size=(550, 550),
            auto_dismiss=True,
            background="assets/background.png",
            separator_height=0,
            title_color=(0, 0, 0, 1)
        )
        popup.open()

    def show_active_quest_details(self, quest, *_):
        container = self.ids['quest_details']
        container.clear_widgets()

        quest_left_panel = BoxLayout(
            orientation="vertical",
            size_hint_x=0.40
            )
        quest_right_panel = BoxLayout(
            orientation="vertical",
            size_hint_x=0.60
        )

        self.update_topbar(quest)

        quest_data = self.quest_manager.active_quests.get(quest.id)
        if not quest_data:
            container.add_widget(Label(
                text=self.lm.t("quest_not_found"),
                color=(0, 0, 0, 1)
            ))
            return

        heroes = quest_data.get("heroes", [])
        turns_left = quest_data.get("turns_left", "?")

        # Cabeçalho
        quest_left_panel.add_widget(Label(
            text=self.lm.t("description_label"),
            markup=True,
            font_size=24,
            color=(0, 0, 0, 1),
            size_hint_y=None,
            height=30
        ))

        desc = Label(
            text=quest.description,
            color=(0, 0, 0, 1),
            halign="left",
            valign="top",
            text_size=(container.width * 0.95, None),
            size_hint_y=None,
            font_size=self.rf.font_title,
        )

        def update_desc_size(*_):
            desc.text_size = (quest_left_panel.width * 0.95, None)
            desc.texture_update()
            desc.height = desc.texture_size[1]

        quest_left_panel.bind(width=update_desc_size)
        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(desc)

        quest_left_panel.add_widget(scroll)
        
        # Lista de heróis na missão

# ── heróis na missão ──────────────────────────────────────
        quest_right_panel.add_widget(Label(
            text=self.lm.t("heroes_on_quest"),
            bold=True,
            color=(0, 0, 0, 1),
            size_hint_y=None,
            height=25,
        ))

        heroes_box = GridLayout(
            cols=3,
            size_hint_y=None,
            spacing=8,
            padding=[8, 4, 8, 4],
        )
        heroes_box.bind(minimum_height=heroes_box.setter("height"))

        def _on_panel_size(panel, size):
            w = size[0]
            if w <= 1:
                return
            cols = 3
            heroes_box.cols = cols

        quest_right_panel.bind(size=_on_panel_size)
        if quest_right_panel.width > 1:
            _on_panel_size(quest_right_panel, quest_right_panel.size)

        for hero in heroes:
            card = HeroCard(
                hero=hero,
                quest=quest,
                pending_assignments=None,
                max_heroes=quest.max_heroes,
                on_selection_changed=None,
                readonly=True,          # ← sem seleção
            )
            heroes_box.add_widget(card)

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(heroes_box)
        quest_right_panel.add_widget(scroll)

        # Tipo / Dificuldade / Turnos restantes
        quest_right_panel.add_widget(Label(
            text=f"{self.lm.t('type_label')}: {self.lm.t(quest.type)}",
            color=(0, 0, 0, 1),
            size_hint_y=None,
            height=self.rf.font_xl * 1.2,
            font_size=self.rf.font_xl
        ))
        quest_right_panel.add_widget(Label(
            text=f"{self.lm.t('turns_left_label')}: {turns_left}",
            color=(0, 0, 0, 1),
            size_hint_y=None,
            height=self.rf.font_xl * 1.2,
            font_size=self.rf.font_xl
        ))

        # Botão de voltar/fechar
        quest_right_panel.add_widget(Button(
            background_normal="assets/buttons/button.png",
            background_down="assets/buttons/button.png",
            background_disabled_normal="assets/button/gear.png",
            border=(0,0,0,0),
            text=self.lm.t("close"),
            size_hint_y=None,
            height=45,
            on_release=lambda *_: container.clear_widgets()
        ))

        container.add_widget(quest_left_panel)
        container.add_widget(quest_right_panel)

    def _filter_heroes_by_quest_type(self, quest_types: list) -> list:
        available_heroes = self.quest_manager.hero_manager.get_available_heroes()
        eligible = []

        for hero in available_heroes:
            hero_perks = [p.lower() for p in getattr(hero, "perks", [])]

            # se bater qualquer tipo da quest, o herói é válido
            if any(qt in hero_perks for qt in quest_types):
                eligible.append(hero)

        return eligible

    def _get_combat_eligible_heroes(self) -> list:
        available_heroes = self.quest_manager.hero_manager.get_available_heroes()
        
        # Filtra apenas heróis que têm roles definidas
        return [h for h in available_heroes if getattr(h, "role", [])]

    def update_success_label(self, quest):
        """Atualiza a taxa de sucesso no label quando heróis são selecionados."""
        hero_ids = self.pending_assignments.get(quest.id, [])
        heroes = [
            self.quest_manager.get_hero(hid)
            for hid in hero_ids
            if self.quest_manager.get_hero(hid)
        ]

        if not heroes:
            self.success_label.text = "--"
            return

        chance = calculate_success_chance(heroes, quest)
        tier = self.get_narrative_tier(chance)

        # 🔹 Tradução via chave (ex: tier_safe, tier_risky…)
        tier_text = self.lm.t(f"tier_{tier}")

        self.success_label.text = f"{tier_text}"

    def get_narrative_tier(self, chance: float) -> str:
        if chance < 0.2:
            return "reckless"
        if chance < 0.4:
            return "risky"
        if chance < 0.6:
            return "uncertain"
        if chance < 0.8:
            return "safe"
        return "trivial"

    def show_assistant_message(self, msg: str):
        """Repassa a fala da assistente para o DialogueBox"""
        if hasattr(self, "dialog_box"):
            self.dialog_box.show_assistant_message(msg)
        else:
            print(f"[Assistente] {msg} (sem DialogueBox ativo)")

    @staticmethod
    def safe_input_filter(substring, from_undo):
        # Permite apenas letras, números e underline
        return re.sub(r'[^A-Za-z0-9_]', '', substring)

    def update_topbar(self, quest):

        if not quest:
            self.quest_title.text = "-"
            self.diff_value.text = "-"
            return

        self.quest_title.text = quest.name
        self.diff_value.text = f"{quest.difficulty:.1f}"

    def _create_hero_card(self, hero, quest):

        def on_selection_changed(limit_reached=False):
            if limit_reached:
                self.quest_manager._log(
                    self.lm.t("max_heroes_reached").format(max=self.max_heroes)
                )
                return
            self.update_success_label(quest)

        card = HeroCard(
            hero=hero,
            quest=quest,
            pending_assignments=self.pending_assignments,
            max_heroes=self.max_heroes,
            on_selection_changed=on_selection_changed,
            readonly=False
        )
        return card

    def on_language_changed(self, language):
        # atualiza o lm local
        self.lm = LanguageManager()

        # sincroniza o lm do quest_manager (ele tem o próprio)
        self.quest_manager.lm = LanguageManager()

        # labels estáticos
        self.active_title.text    = self.lm.t("active_quests")
        self.available_title.text = self.lm.t("available_quests")
        self.menu_title.text      = self.lm.t("menu_label") or "MENU"
        self.log_title_label.text = self.lm.t("mission_log")

        # sidebar — agora quest.name já está no idioma novo
        self.update_ui()

        # se havia um painel de detalhes aberto, fecha e limpa
        # (não dá para re-abrir sem saber qual quest estava selecionada)
        try:
            details = self.ids['quest_details']
            if details.children:
                details.clear_widgets()
        except Exception:
            pass
