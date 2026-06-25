# screens/settings_screen.py
import json
import os
from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.slider import Slider
from kivy.uix.checkbox import CheckBox
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.uix.image import Image
from kivy.app import App
from core.music_manager import get_music_manager
from core.language_manager import LanguageManager
from kivy.properties import StringProperty

CONFIG_FILE = "config.json"


class SettingsScreen(Screen):
    previous_screen = StringProperty("menu")

    # settings_screen.py - adicione no método __init__ ou build_ui

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.lm = LanguageManager()
        self.config = self.load_config()

        self.music_volume_label = None
        self.ui_volume_label = None

        # Aplica configurações de música ao carregar
        self._apply_music_settings()
        
        self.build_ui()

    def on_enter(self):
        """Quando entra na tela de settings"""
        # Pausa a música
        music = get_music_manager()
        music.pause()
        Window.bind(on_keyboard=self._on_keyboard)

    def on_leave(self):
        """Quando sai da tela de settings"""
        # Resume a música se estava tocando antes
        music = get_music_manager()
        if not music.is_playing and music.current_sound:
            music.resume()

    # ---------------- CONFIG ----------------
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            default = {
                "language": "en",
                "screen_mode": "Window",
                "screen_size": [800, 600],
                "music_muted": False,
                "ui_muted": False,
                "music_volume": 50.0,
                "ui_volume": 50.0,
            }
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(default, f, indent=4)
            return default

    def save_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4)

    # ---------------- UI ----------------
    def build_ui(self):
        layout = FloatLayout()

        # Fundo
        from kivy.graphics import Color, Rectangle
        with layout.canvas.before:
            Color(0, 0, 0, 1)
            self.bg_rect = Rectangle(size=layout.size, pos=layout.pos)
        layout.bind(size=self._update_bg, pos=self._update_bg)

        # Container principal
        box = BoxLayout(
            orientation="vertical",
            size_hint=(None, None),
            size=(800, 580),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            spacing=20,
            padding=40,
        )

        pergaminho = Image(
            source="assets/background_ls.png",
            size_hint=(None, None),
            size=(800, 600),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            allow_stretch=True,
            keep_ratio=False
        )
        layout.add_widget(pergaminho)

        # Título
        title = Label(
            text=f"{self.lm.t('settings_title')}",
            font_size=32,
            bold=True,
            color=(0.16, 0.09, 0.06, 1),
            size_hint_y=None,
            height=50,
        )
        box.add_widget(title)

        # Conteúdo
        content = BoxLayout(orientation="horizontal", spacing=30)

        # Coluna esquerda
        left = BoxLayout(orientation="vertical", spacing=15)

        # Idioma
        left.add_widget(Label(
            text=self.lm.t("language"),
            color=(0.16, 0.09, 0.06, 1),
            size_hint_y=None, height=25
        ))

        lang_spinner = Spinner(
            text=self.config.get("language", "pt"),
            values=["pt", "en", "es", "ru", "zh", "ja"],
            size_hint_y=None, height=40
        )
        lang_spinner.bind(text=self.set_language)
        left.add_widget(lang_spinner)

        # Modo de tela
        left.add_widget(Label(
            text=self.lm.t("screen_mode"),
            color=(0.16, 0.09, 0.06, 1),
            size_hint_y=None, height=25
        ))
        mode_spinner = Spinner(
            text=self.config.get("screen_mode", "Window"),
            values=["Window", "Fullscreen"],
            size_hint_y=None, height=40
        )
        mode_spinner.bind(text=self.set_screen_mode)
        left.add_widget(mode_spinner)

        # Resolução
        left.add_widget(Label(
            text=self.lm.t("screen_size"),
            color=(0.16, 0.09, 0.06, 1),
            size_hint_y=None, height=25
        ))
        size_spinner = Spinner(
            text=f"{self.config['screen_size'][0]}x{self.config['screen_size'][1]}",
            values=["800x600", "1024x768", "1280x720", "1366x768", "1920x1080"],
            size_hint_y=None, height=40
        )
        size_spinner.bind(text=self.set_screen_size)
        left.add_widget(size_spinner)

        # Coluna direita
        right = BoxLayout(orientation="vertical", spacing=15)

        # Volume música
        self.music_volume_label = Label(
            text=f"{self.lm.t('music_volume')}: {int(self.config['music_volume'])}%",
            color=(0.16, 0.09, 0.06, 1),
            size_hint_y=None, height=25
        )
        right.add_widget(self.music_volume_label)

        music_slider = Slider(
            min=0, max=100, value=self.config["music_volume"],
            size_hint_y=None, height=40
        )
        music_slider.bind(value=self.set_music_volume)
        right.add_widget(music_slider)

        # Volume UI
        self.ui_volume_label = Label(
            text=f"{self.lm.t('ui_volume')}: {int(self.config['ui_volume'])}%",
            color=(0.16, 0.09, 0.06, 1),
            size_hint_y=None, height=25
        )
        right.add_widget(self.ui_volume_label)

        ui_slider = Slider(
            min=0, max=100, value=self.config["ui_volume"],
            size_hint_y=None, height=40
        )
        ui_slider.bind(value=self.set_ui_volume)
        right.add_widget(ui_slider)

        # Mute música
        mute_box = BoxLayout(orientation="horizontal", spacing=10, size_hint_y=None, height=40)
        mute_box.add_widget(Label(
            text=self.lm.t("mute_music"),
            color=(0.16, 0.09, 0.06, 1),
        ))
        cb_music = CheckBox(active=self.config["music_muted"], size_hint=(None, None), size=(40, 40))
        cb_music.bind(active=self.toggle_music_mute)
        mute_box.add_widget(cb_music)
        right.add_widget(mute_box)

        # Mute UI
        ui_box = BoxLayout(orientation="horizontal", spacing=10, size_hint_y=None, height=40)
        ui_box.add_widget(Label(
            text=self.lm.t("mute_ui"),
            color=(0.16, 0.09, 0.06, 1),
        ))
        cb_ui = CheckBox(active=self.config["ui_muted"], size_hint=(None, None), size=(40, 40))
        cb_ui.bind(active=self.toggle_ui_mute)
        ui_box.add_widget(cb_ui)
        right.add_widget(ui_box)

        # Juntar colunas
        content.add_widget(left)
        content.add_widget(right)
        box.add_widget(content)

        # --- Créditos de Música ---
        credits_box = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=60,
            spacing=2
        )

        credits_title = Label(
            text=self.lm.t("music_credits_title"),
            font_size=20,
            bold=True,
            color=(0.16, 0.09, 0.06, 1),
            size_hint_y=None,
            height=20
        )

        credits_text = Label(
            text=self.lm.t("music_credits_text"),
            font_size=16,
            halign="left",
            valign="top",
            color=(0.16, 0.09, 0.06, 1),
            size_hint_y=None,
            height=40
        )
        credits_text.bind(size=lambda *x: credits_text.texture_update())

        credits_box.add_widget(credits_title)
        credits_box.add_widget(credits_text)

        box.add_widget(credits_box)

        # Botão Voltar
        back_btn = Button(
            text=self.lm.t('back_to_menu'),
            size_hint_y=None, height=60,
            font_size=20, bold=True,
            background_color=(0.4, 0.3, 0.2, 1),
            color=(0.9, 0.85, 0.7, 1)
        )
        back_btn.bind(on_release=self.go_back)
        box.add_widget(back_btn)

        layout.add_widget(box)
        self.add_widget(layout)


    def _update_bg(self, instance, value):
        self.bg_rect.size = instance.size
        self.bg_rect.pos = instance.pos

    # ---------------- CALLBACKS ----------------
    def set_language(self, instance, lang):
        self.config["language"] = lang
        self.lm.set_language(lang)

        self.save_config()

        # 🔤 Atualiza a fonte global (acessa o app principal)
        app = App.get_running_app()
        app.change_language(lang)

        self.clear_widgets()
        self.build_ui()  # Reconstrói UI no novo idioma

    def set_screen_mode(self, instance, mode):
        self.config["screen_mode"] = mode
        Window.fullscreen = (mode == "Fullscreen")
        self.save_config()

    def set_screen_size(self, instance, size_str):
        w, h = map(int, size_str.split("x"))
        self.config["screen_size"] = [w, h]
        Window.size = (w, h)
        self.save_config()

    def set_music_volume(self, instance, value):
        value = float(value)
        self.config["music_volume"] = value
        if self.music_volume_label:
            self.music_volume_label.text = f"{self.lm.t('music_volume')}: {int(value)}%"
        music = get_music_manager()
        music.set_volume(value / 100.0)
        self.save_config()

    def set_ui_volume(self, instance, value):
        value = float(value)
        self.config["ui_volume"] = value
        if self.ui_volume_label:
            self.ui_volume_label.text = f"{self.lm.t('ui_volume')}: {int(value)}%"
        self.save_config()

    def toggle_music_mute(self, instance, value):
        self.config["music_muted"] = value
        music = get_music_manager()
        if value and not music.is_muted:
            music.toggle_mute()
        elif not value and music.is_muted:
            music.toggle_mute()
        self.save_config()

    def toggle_ui_mute(self, instance, value):
        self.config["ui_muted"] = value
        self.save_config()

    def go_back(self, *args):
        if self.previous_screen == "gameplay":
            gameplay = self.manager.get_screen("gameplay")
            gameplay.coming_from_settings = True    # ← faltava isso
            music = get_music_manager()
            if music.is_muted:
                music.toggle_mute()
        else:
            print("Voltando ao menu principal...")

        self.manager.current = self.previous_screen

    def _apply_music_settings(self):
        """Aplica as configurações de música carregadas do config"""
        music = get_music_manager()
        
        # Aplica volume
        music_volume = self.config.get("music_volume", 50.0)
        music.set_volume(music_volume / 100.0)
        
        # Aplica mute se necessário
        is_muted = self.config.get("music_muted", False)
        if is_muted and not music.is_muted:
            music.toggle_mute()
        elif not is_muted and music.is_muted:
            music.toggle_mute()

    def on_leave(self):
        Window.unbind(on_keyboard=self._on_keyboard)

    def _on_keyboard(self, window, key, scancode, codepoint, modifiers):
        if key == 27:  # ESC / botão voltar
            self.go_back()
            return True  # impede o fechamento da janela
        return False