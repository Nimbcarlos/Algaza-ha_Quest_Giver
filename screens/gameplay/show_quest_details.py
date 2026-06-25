from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from screens.gameplay.hero_popup import show_hero_details


def show_quest_details(self, quest, *_):
    """Mostra painel com detalhes da quest e opções de heróis."""
    container = self.ids.quest_details
    container.clear_widgets()

    self.pending_assignments[quest.id] = []

    self.manager.qm.hero_manager.check_hero_unlocks(self.manager.qm.completed_quests, self.manager.qm.current_turn)

    # Lista os heróis disponíveis
    available_heroes = self.manager.qm.hero_manager.get_available_heroes()

    # Detecta se é tela pequena
    is_small_screen = container.width <= 850 or container.height <= 650

    container.add_widget(Label(
        text=f"[b]{quest.name}[/b]",
        markup=True, 
        font_size=24 if not is_small_screen else 20, 
        color=(0, 0, 0, 1),
        size_hint_y=None, 
        height=30
    ))

    container.add_widget(Label(
        text=f"{self.lm.t('type_label')}: {quest.type} | {self.lm.t('difficulty_label')}: {quest.difficulty}",
        color=(0, 0, 0, 1),
        size_hint_y=None,
        height=20,
        font_size=14 if is_small_screen else 16
    ))

    desc_label = Label(
        text=quest.description,
        color=(0, 0, 0, 1),
        halign="left",
        text_size=(container.width * 0.9, None),
        valign="top",
        size_hint_y=None,
        font_size=13 if is_small_screen else 15
    )
    desc_label.bind(
        texture_size=lambda *x: desc_label.setter("height")(desc_label, desc_label.texture_size[1])
    )
    container.add_widget(desc_label)

    # Taxa de sucesso
    self.success_label = Label(
        text=f'{self.lm.t("success_rate")}: --',
        color=(0, 0, 0, 1),
        size_hint_y=None,
        height=25,
        font_size=14 if is_small_screen else 16
    )
    container.add_widget(self.success_label)

    # "Heróis disponíveis:"
    container.add_widget(Label(
        text=self.lm.t("available_heroes"),
        bold=True,
        color=(0, 0, 0, 1),
        size_hint_y=None,
        height=25,
        font_size=15 if is_small_screen else 17
    ))

    heroes_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=5)
    heroes_box.bind(minimum_height=heroes_box.setter("height"))

    for hero in available_heroes:
        
        if is_small_screen:
            # ==================== LAYOUT COMPACTO (800x600) ====================
            # Card vertical para cada herói
            hero_card = BoxLayout(
                orientation="vertical", 
                size_hint_y=None, 
                height=110,
                padding=5,
                spacing=3
            )
            
            # Linha 1: Foto + Nome + Botão de detalhes
            top_row = BoxLayout(size_hint_y=None, height=50, spacing=5)
            
            if getattr(hero, "photo_url", None):
                top_row.add_widget(Image(
                    source=hero.photo_url,
                    size_hint=(None, 1),
                    width=45
                ))
            
            top_row.add_widget(Label(
                text=f"[b]{hero.name}[/b]",
                markup=True,
                color=(0, 0, 0, 1),
                halign="left",
                valign="middle",
                font_size=15
            ))
            
            top_row.add_widget(Button(
                text="🔍",
                size_hint=(None, 1),
                width=40,
                on_release=lambda *_, h=hero: show_hero_details(self, h)
            ))
            
            hero_card.add_widget(top_row)
            
            # Linha 2: Classe e Level
            info_row = BoxLayout(size_hint_y=None, height=25, spacing=5)
            
            info_row.add_widget(Label(
                text=f"{getattr(hero, 'hero_class', 'Unknown')}",
                color=(0, 0, 0, 1),
                halign="left",
                font_size=13
            ))
            
            info_row.add_widget(Label(
                text=f"{self.lm.t('lvl_prefix')} {getattr(hero, 'level', 1)}",
                color=(0, 0, 0, 1),
                halign="center",
                font_size=13
            ))
            
            hero_card.add_widget(info_row)
            
            # Linha 3: Botão de seleção (largo)
            select_btn = Button(
                text=self.lm.t('select'),
                size_hint_y=None,
                height=30,
                background_color=(0.8, 0.8, 0.8, 1),
                font_size=14
            )
            
            def on_select_press(btn, h=hero):
                self.select_hero_for_quest(quest, h)
                quest_id = quest.id
                if h.id in self.pending_assignments.get(quest_id, []):
                    btn.text = self.lm.t('selected')
                    btn.background_color = (0.4, 0.8, 0.4, 1)
                else:
                    btn.text = self.lm.t('select')
                    btn.background_color = (0.8, 0.8, 0.8, 1)
            
            select_btn.bind(on_release=on_select_press)
            hero_card.add_widget(select_btn)
            
            heroes_box.add_widget(hero_card)
            
        else:
            # ==================== LAYOUT NORMAL (telas maiores) ====================
            row = BoxLayout(size_hint_y=None, height=60, spacing=10)

            if getattr(hero, "photo_url", None):
                row.add_widget(Image(
                    source=hero.photo_url,
                    size_hint_x=None,
                    width=50
                ))
            else:
                row.add_widget(Label(
                    text="❓",
                    size_hint_x=None,
                    width=50
                ))

            row.add_widget(Label(
                text=hero.name,
                color=(0, 0, 0, 1),
                halign="left",
                valign="middle"
            ))

            row.add_widget(Label(
                text=f"{self.lm.t('class')}: {getattr(hero, 'hero_class', 'Unknown')}",
                color=(0, 0, 0, 1),
                halign="left",
                valign="middle"
            ))

            row.add_widget(Label(
                text=f"{self.lm.t('lvl_prefix')} {getattr(hero, 'level', 1)}",
                color=(0, 0, 0, 1),
                halign="left",
                valign="middle"
            ))

            row.add_widget(Button(
                text="🔍",
                size_hint_x=None,
                width=50,
                on_release=lambda *_, h=hero: show_hero_details(self, h)
            ))

            select_btn = Button(
                text=self.lm.t('select'),
                size_hint_x=None,
                width=120,
                background_color=(0.8, 0.8, 0.8, 1)
            )

            def on_select_press(btn, h=hero):
                self.select_hero_for_quest(quest, h)
                quest_id = quest.id
                if h.id in self.pending_assignments.get(quest_id, []):
                    btn.text = self.lm.t('selected')
                    btn.background_color = (0.4, 0.8, 0.4, 1)
                else:
                    btn.text = self.lm.t('select')
                    btn.background_color = (0.8, 0.8, 0.8, 1)

            select_btn.bind(on_release=on_select_press)
            row.add_widget(select_btn)

            heroes_box.add_widget(row)

    scroll = ScrollView(size_hint_y=0.4)
    scroll.add_widget(heroes_box)
    container.add_widget(scroll)

    # Botão enviar
    container.add_widget(Button(
        text=self.lm.t("send_to_quest_btn"),
        size_hint_y=None,
        height=50,
        on_release=lambda *_: self.start_quest(quest)
    ))