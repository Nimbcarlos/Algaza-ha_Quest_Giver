# screens/load_game_screen.py
import os
from datetime import datetime
from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.graphics import Color, Rectangle
from core.music_manager import get_music_manager
import core.save_manager as save
from core.language_manager import LanguageManager
from kivy.properties import StringProperty
from kivy.core.window import Window


SAVE_DIR = "saves"

class LoadGameScreen(Screen):
    previous_screen = StringProperty('menu')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.lm = LanguageManager()
        self.saves_list = None
        self.build_ui()

    def on_pre_enter(self):
        self.lm = LanguageManager()  # recarrega idioma atualizado
        self.refresh_saves()
        self.build_ui()
        Window.bind(on_keyboard=self._on_keyboard)

    def build_ui(self):
        """Cria toda a UI em Python, zero dependência de .kv"""
        # FloatLayout principal
        main_layout = FloatLayout()
        
        # Background preto
        with main_layout.canvas.before:
            Color(0, 0, 0, 1)
            self.bg_rect = Rectangle(size=main_layout.size, pos=main_layout.pos)
        main_layout.bind(size=self._update_bg, pos=self._update_bg)
        
        # Pergaminho
        pergaminho = Image(
            source="assets/background_ls.png",
            size_hint=(None, None),
            size=(800, 600),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            allow_stretch=True,
            keep_ratio=False
        )
        main_layout.add_widget(pergaminho)
        
        # Container de conteúdo
        content_layout = BoxLayout(
            orientation="vertical",
            size_hint=(None, None),
            size=(800, 580),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            padding=40,
            spacing=20
        )
        
        # Título
        title = Label(
            text=self.lm.t("load_game_title"),
            font_size=28,
            bold=True,
            color=(0.16, 0.09, 0.06, 1),
            size_hint_y=None,
            height=50
        )
        content_layout.add_widget(title)
        
        # ScrollView com lista de saves
        scroll = ScrollView()
        self.saves_list = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=8
        )
        self.saves_list.bind(minimum_height=self.saves_list.setter("height"))
        scroll.add_widget(self.saves_list)
        content_layout.add_widget(scroll)
        
        # Botão Voltar
        back_btn = Button(
            text=self.lm.t("back_to_menu"),
            size_hint_y=None,
            height=60,
            font_size=20,
            bold=True,
            background_color=(0.4, 0.3, 0.2, 1),
            color=(0.9, 0.85, 0.7, 1)
        )
        back_btn.bind(on_release=self.go_back)
        content_layout.add_widget(back_btn)
        
        main_layout.add_widget(content_layout)
        self.add_widget(main_layout)

    def _update_bg(self, instance, value):
        """Atualiza o background quando redimensiona"""
        self.bg_rect.size = instance.size
        self.bg_rect.pos = instance.pos

    def on_enter(self):
        """Atualiza a lista de saves ao entrar na tela"""
        self.refresh_saves()

    def refresh_saves(self):
        """Lista todos os saves disponíveis"""
        self.saves_list.clear_widgets()
        
        if not os.path.exists(SAVE_DIR):
            os.makedirs(SAVE_DIR)

        files = [f for f in os.listdir(SAVE_DIR) if f.endswith(".json")]
        
        if not files:
            self.saves_list.add_widget(Label(
                text=self.lm.t("no_saves_found"),
                color=(0.16, 0.09, 0.06, 1),
                size_hint_y=None,
                height=40
            ))
            return

        for f in files:
            filepath = os.path.join(SAVE_DIR, f)
            modified = datetime.fromtimestamp(os.path.getmtime(filepath))
            date_str = modified.strftime("%d/%m/%Y %H:%M")

            row = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=50,
                spacing=5
            )

            # Nome do save + data
            row.add_widget(Label(
                text=f"{f.replace('.json', '')} - {date_str}",
                color=(0.16, 0.09, 0.06, 1),
                halign="left",
                valign="middle"
            ))

            # Botão Carregar
            load_btn = Button(
                text=self.lm.t("load_button"),
                size_hint_x=None,
                width=120,
                background_color=(0.4, 0.8, 0.4, 1)
            )
            load_btn.bind(on_release=lambda _, file=f: self.load_save(file))
            row.add_widget(load_btn)

            # Botão Deletar
            delete_btn = Button(
                text=self.lm.t("delete_button"),
                size_hint_x=None,
                width=100,
                background_color=(0.8, 0.4, 0.4, 1)
            )
            delete_btn.bind(on_release=lambda _, file=f: self.confirm_delete(file))
            row.add_widget(delete_btn)

            self.saves_list.add_widget(row)

    def confirm_delete(self, filename):
        """Mostra popup de confirmação antes de apagar"""
        content = BoxLayout(orientation="vertical", spacing=10, padding=10)
        
        content.add_widget(Label(
            text=self.lm.t("confirm_delete_message").format(filename=filename.replace('.json', '')),
            color=(0, 0, 0, 1)
        ))

        btns = BoxLayout(size_hint_y=None, height=40, spacing=10)
        
        popup = Popup(
            title=self.lm.t("confirm_delete_title"),
            content=content,
            size_hint=(0.5, 0.3),
            background="assets/background.png",
            separator_color=(0, 0, 0, 0)
        )

        cancel_btn = Button(
            text=self.lm.t("cancel_button"),
            background_color=(0.7, 0.7, 0.7, 1)
        )
        cancel_btn.bind(on_release=popup.dismiss)
        
        delete_btn = Button(
            text=self.lm.t("delete_confirm_button"),
            background_color=(0.8, 0.4, 0.4, 1)
        )
        delete_btn.bind(on_release=lambda _: (self.delete_save(filename), popup.dismiss()))
        
        btns.add_widget(cancel_btn)
        btns.add_widget(delete_btn)
        content.add_widget(btns)

        popup.open()

    def delete_save(self, filename):
        """Deleta um save"""
        filepath = os.path.join(SAVE_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"[LoadGameScreen] Save deletado: {filename}")
        self.refresh_saves()

    def load_save(self, filename):
        """Carrega o save e entra no gameplay"""
        gameplay = self.manager.get_screen("gameplay")
        
        # Garante que as instâncias existam antes de carregar os dados nelas
        from core.quest_manager import QuestManager
        gameplay.quest_manager = QuestManager()
        gameplay.hero_manager = gameplay.quest_manager.hero_manager

        # carrega o save no qm do gameplay
        if save.load_state(gameplay.quest_manager, filename):
            # print(f"✅ {self.lm.t('save_loaded_success')}: {filename}")
            # sinaliza que veio de um load (on_enter do gameplay usa isso)
            gameplay.coming_from_load = True
            self.manager.current = "gameplay"
        else:
            print(f"⚠️ {self.lm.t('save_loaded_error')}: {filename}")

    def go_back(self, *args):
            """Volta para a tela anterior armazenada na propriedade."""
            target_screen = self.previous_screen
            
            # Fallback para o menu se a propriedade estiver vazia por algum motivo
            if not target_screen:
                target_screen = 'menu'
            
            print(f"Voltando para a tela: {target_screen}")
            self.manager.current = target_screen

    def on_leave(self):
        Window.unbind(on_keyboard=self._on_keyboard)

    def _on_keyboard(self, window, key, scancode, codepoint, modifiers):
        if key == 27:  # ESC / botão voltar
            self.go_back()
            return True  # impede o fechamento da janela
        return False