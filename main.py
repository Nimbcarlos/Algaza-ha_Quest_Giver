import sys, os, traceback
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def _log_error(e):
    exc_type, exc_value, exc_tb = sys.exc_info()
    tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    with open("log.txt", "a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n{datetime.now()}\n{tb_text}\n{'='*60}\n")
    print(tb_text)

try:
    import os, sys, json
    os.environ['KIVY_NO_CONSOLELOG'] = '1'

    from kivy.config import Config
    Config.set('input', 'mouse', 'mouse,multitouch_on_demand')
    Config.set('graphics', 'resizable', False)
    Config.set('graphics', 'dpi', '96')

    from kivy.app import App
    from kivy.uix.screenmanager import ScreenManager, FadeTransition
    from kivy.properties import StringProperty  # ✅ NOVO
    from screens.menu_screen import MenuScreen
    from screens.gameplay_screen import GameplayScreen
    from screens.load_game_screen import LoadGameScreen
    from screens.settings_screen import SettingsScreen
    from screens.responsive_frame import ResponsiveFrame
    from core.quest_manager import QuestManager
    from core.hero_manager import HeroManager
    from core.language_manager import LanguageManager
    from core.font_manager import FontManager
    import traceback
    from kivy.core.window import Window
    from datetime import datetime

    # Caminho do config.json
    CONFIG_FILE = "config.json"

    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            if "screen_size" in config:
                w, h = config["screen_size"]
                Window.size = (w, h)

    class GameScreenManager(ScreenManager):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.quest_manager = QuestManager()
            self.hero_manager = HeroManager()
            self.transition = FadeTransition(duration=0.3)


    class GameApp(App):
        # ✅ Propriedade reativa para fonte
        font_name = StringProperty("NotoSans")

        def build(self):
            # Registra fontes
            FontManager.register_fonts()
            
            # Cria gerenciador de idiomas
            self.lm = LanguageManager()
            
            # ✅ Define fonte inicial baseada no idioma
            self.font_name = FontManager.get_font_for_language(self.lm.language)
            
            # Cria screen manager
            sm = GameScreenManager()
            sm.add_widget(MenuScreen(name="menu"))
            sm.add_widget(GameplayScreen(name="gameplay"))
            sm.add_widget(LoadGameScreen(name="loadgame"))
            sm.add_widget(SettingsScreen(name="settings"))
            self.title = "ALGAZA-HA: Quest Giver"
            self.icon = "assets/icon.ico"
            return sm
        
        def change_language(self, language: str):
            """
            Troca o idioma do jogo e atualiza a fonte automaticamente.
            
            Args:
                language: Código do idioma (pt, en, zh, ja, etc.)
            """
            # Atualiza idioma
            self.lm.set_language(language)
            
            # ✅ Atualiza fonte (isso dispara atualização em TODOS os widgets)
            self.font_name = FontManager.get_font_for_language(language)
            
            if hasattr(self, 'root') and hasattr(self.root, 'hero_manager'):
                self.root.hero_manager.load_heroes(language)

            # 🔹 Recarrega os dados dependentes do idioma
            if hasattr(self, 'root') and hasattr(self.root, 'quest_manager'):
                self.root.quest_manager.load_quests(language)

            # 🔹 Notifica telas ativas
            if hasattr(self.root, "current_screen") and hasattr(self.root.current_screen, "on_language_changed"):

                self.root.current_screen.on_language_changed(language)


    if __name__ == "__main__":
        GameApp().run()


except Exception as e:
    exc_type, exc_value, exc_traceback = sys.exc_info()
    tb_list = traceback.format_exception(exc_type, exc_value, exc_traceback)
    tb_text = "".join(tb_list)

    # Extração básica
    tb = traceback.extract_tb(exc_traceback)
    filename, line, func, text = tb[-1]

    # ===============================
    # 📌 SALVA EM LOG.TXT
    # ===============================
    with open("log.txt", "a", encoding="utf-8") as log:
        log.write("\n" + "=" * 60 + "\n")
        log.write(f"Erro em: {datetime.now()}\n")
        log.write(f"Exception: {exc_type.__name__}\n")
        log.write(f"Arquivo: {filename}\n")
        log.write(f"Linha: {line}\n")
        log.write(f"Função: {func}\n")
        log.write(f"Mensagem: {exc_value}\n")
        log.write(f"Código: {text}\n")
        log.write("\n--- Traceback completo ---\n")
        log.write(tb_text)
        log.write("\n" + "=" * 60 + "\n")

    # Mostra no console também
    print("❌ Erro capturado!")
    print(tb_text)