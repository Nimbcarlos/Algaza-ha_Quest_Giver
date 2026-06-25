# screens/menu_screen.py
import os
from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.anchorlayout import AnchorLayout
from kivy.graphics import Color, Rectangle
from kivy.app import App
import core.save_manager as save
from screens.gameplay_screen import GameplayScreen
from core.quest_manager import QuestManager
from core.hero_manager import HeroManager
from screens.confirmation_popup import ConfirmationPopup  # ✅ NOVO IMPORT


class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "menu"
        self.language_manager = None  # ✅ Será setado pelo app
        self.build_ui()

    def on_enter(self):
        latest_save = save.get_latest_save()

        self.continue_btn.disabled = latest_save is None
        self.continue_btn.opacity = 0.5 if latest_save is None else 1

    def build_ui(self):
        """Constrói toda a interface do menu em Python puro."""
        # FloatLayout principal
        main_layout = FloatLayout()
        
        # ═══════════════════════════════════════════════════════
        # 1️⃣ Background preto
        # ═══════════════════════════════════════════════════════
        with main_layout.canvas.before:
            Color(0, 0, 0, 1)
            self.bg_rect = Rectangle(size=main_layout.size, pos=main_layout.pos)
        
        # Atualiza background quando redimensionar
        main_layout.bind(
            size=self._update_bg,
            pos=self._update_bg
        )
        
        # ═══════════════════════════════════════════════════════
        # 2️⃣ Pergaminho de fundo
        # ═══════════════════════════════════════════════════════
        pergaminho = Image(
            source="assets/background_ls.png",
            size_hint=(None, None),
            size=(800, 600),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            allow_stretch=True,
            keep_ratio=False
        )
        main_layout.add_widget(pergaminho)
        
        # ═══════════════════════════════════════════════════════
        # 3️⃣ Container horizontal (logo + botões)
        # ═══════════════════════════════════════════════════════
        content_box = BoxLayout(
            orientation="horizontal",
            spacing=10,
            size_hint=(None, None),
            size=(800, 500),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            padding=[10, 10, 10, 10]
        )
        
        # ═══════════════════════════════════════════════════════
        # 4️⃣ LADO ESQUERDO: Logo
        # ═══════════════════════════════════════════════════════
        logo_container = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            size_hint_x=0.45
        )
        
        logo = Image(
            source="assets/logo.png",
            size_hint=(None, None),
            size=(400, 350),
            allow_stretch=True,
            keep_ratio=True
        )
        logo_container.add_widget(logo)
        content_box.add_widget(logo_container)
        
        # ═══════════════════════════════════════════════════════
        # 5️⃣ LADO DIREITO: Botões
        # ═══════════════════════════════════════════════════════
        buttons_box = BoxLayout(
            orientation="vertical",
            center_x=5,
            spacing=5,
            size_hint_x=0.35,
            padding=[0, 50, 0, 0]
        )

        self.continue_btn = Button(
            background_normal="assets/buttons/continue.png",
            background_down="assets/buttons/continue.png",
            size_hint=(None, None),
            width=300,
            height=65,
            border=(0, 0, 0, 0)
        )
        self.continue_btn.bind(on_release=self.continue_game)
        buttons_box.add_widget(self.continue_btn)

        # New Game Button
        new_game_btn = Button(
            background_normal="assets/buttons/new_game.png",
            background_down="assets/buttons/new_game.png",
            size_hint=(None, None),
            width=300,
            height=65,
            border=(0, 0, 0, 0)
        )
        new_game_btn.bind(on_release=self.new_game)
        buttons_box.add_widget(new_game_btn)
        
        # Load Game Button
        load_game_btn = Button(
            background_normal="assets/buttons/load_game.png",
            background_down="assets/buttons/load_game.png",
            size_hint=(None, None),
            width=300,
            height=65,
            border=(0, 0, 0, 0)
        )
        load_game_btn.bind(on_release=self.open_load_game)
        buttons_box.add_widget(load_game_btn)
        
        # Settings Button
        settings_btn = Button(
            background_normal="assets/buttons/settings.png",
            background_down="assets/buttons/settings.png",
            size_hint=(None, None),
            width=300,
            height=65,
            border=(0, 0, 0, 0)
        )
        settings_btn.bind(on_release=self.open_settings)
        buttons_box.add_widget(settings_btn)
        
        # Exit Button
        exit_btn = Button(
            background_normal="assets/buttons/exit.png",
            background_down="assets/buttons/exit.png",
            size_hint=(None, None),
            width=300,
            height=65,
            border=(0, 0, 0, 0)
        )
        exit_btn.bind(on_release=self.exit_game)  # ✅ Agora vai abrir o popup
        buttons_box.add_widget(exit_btn)
        
        content_box.add_widget(buttons_box)
        main_layout.add_widget(content_box)
        
        # Adiciona tudo à tela
        self.add_widget(main_layout)
    
    def _update_bg(self, instance, value):
        """Atualiza o tamanho/posição do background."""
        self.bg_rect.size = instance.size
        self.bg_rect.pos = instance.pos
    
    # ═══════════════════════════════════════════════════════════
    # MÉTODOS DE NAVEGAÇÃO
    # ═══════════════════════════════════════════════════════════
    
    def new_game(self, *args):
        """Inicia um novo jogo."""
        # print("[MenuScreen] Iniciando novo jogo...")
        
        # 1️⃣ Cria managers totalmente novos
        self.manager.quest_manager = QuestManager()
        self.manager.quest_manager.hero_manager = HeroManager()
        
        # 2️⃣ Remove a tela antiga de gameplay se existir
        if self.manager.has_screen("gameplay"):
            old_screen = self.manager.get_screen("gameplay")
            self.manager.remove_widget(old_screen)
        
        # 3️⃣ Recria a tela de gameplay
        new_gameplay = GameplayScreen(name="gameplay")
        self.manager.add_widget(new_gameplay)
        
        # 4️⃣ Vai para gameplay
        self.manager.current = "gameplay"
    
    def open_load_game(self, *args):
        """Abre a tela de carregar jogo."""
        self.manager.current = "loadgame"
    
    def open_settings(self, *args):
        """Abre a tela de configurações."""
        settings_screen = self.manager.get_screen("settings")
        settings_screen.previous_screen = "menu"
        self.manager.current = "settings"
    
    def exit_game(self, *args):
        """Mostra popup de confirmação para sair do jogo."""
        # ✅ USA A NOVA ASSINATURA DO ConfirmationPopup
        popup = ConfirmationPopup(
            message_key="exit_confirm_message",
            on_confirm=self._confirm_exit
        )
        popup.open()

    def _confirm_exit(self):
        """Fecha o app após confirmação."""
        # print("[MenuScreen] Saindo do jogo...")
        App.get_running_app().stop()

    # ═══════════════════════════════════════════════════════════
    # MÉTODOS AUXILIARES (caso precise de lista de saves no menu)
    # ═══════════════════════════════════════════════════════════
    
    def show_save_files(self, *args):
        """
        Mostra lista de saves (se você quiser implementar aqui).
        Por enquanto, apenas redireciona para loadgame screen.
        """
        self.manager.current = "loadgame"
    
    def _on_select_save(self, filename: str, *args):
        """Handler quando o jogador escolhe um save."""
        qm = getattr(self.manager, "quest_manager", None)
        if qm is None:
            print("[MenuScreen] QuestManager não encontrado!")
            self.manager.current = "gameplay"
            return
        
        ok = save.load_game(qm, filename=filename)
        if not ok:
            print(f"[MenuScreen] Erro ao carregar {filename}")
        else:
            print(f"[MenuScreen] Save carregado: {filename}")
        
        self.manager.current = "gameplay"

    def continue_game(self, *args):
        latest = save.get_latest_save()
        if not latest:
            print("[MenuScreen] ❌ Nenhum save encontrado")
            return

        filename = os.path.basename(latest)
        # print(f"[MenuScreen] 🔄 Carregando: {filename}")

        gameplay = self.manager.get_screen("gameplay")

        from core.quest_manager import QuestManager
        gameplay.quest_manager = QuestManager()
        gameplay.hero_manager  = gameplay.quest_manager.hero_manager

        if save.load_game(gameplay.quest_manager, filename):
            # print(f"[MenuScreen] ✅ Save carregado!")
            gameplay.coming_from_load = True
            self.manager.current = "gameplay"
        else:
            print(f"[MenuScreen] ❌ Erro ao carregar '{filename}'")
