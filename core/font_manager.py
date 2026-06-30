from kivy.core.text import LabelBase


class FontManager:
    """
    Gerencia fontes baseado no idioma ativo.
    Retorna a fonte apropriada para cada idioma.
    """
    
    # Mapeamento de idiomas para fontes
    FONT_MAP = {
        # Línguas latinas (português, inglês, espanhol, etc.)
        "pt": "NotoSans",
        "en": "NotoSans",
        "es": "NotoSans",
        "fr": "NotoSans",
        "de": "NotoSans",
        "it": "NotoSans",
        
        # Chinês (simplificado e tradicional)
        "zh": "NotoSansSC",
        "zh-cn": "NotoSansSC",
        "zh-tw": "NotoSansSC",
        
        # Japonês
        "ja": "NotoSansJP",
        
        # Coreano
        "ko": "NotoSansKR",
        "kr": "NotoSansKR",
        
        # Russo e cirílico
        "ru": "NotoSans",
        "uk": "NotoSans",
        "bg": "NotoSans",
    }
    
    # Fonte padrão (fallback)
    DEFAULT_FONT = "NotoSans"
    
    @staticmethod
    def register_fonts():
        """
        Registra todas as fontes necessárias.
        Deve ser chamado uma vez no início da aplicação.
        """
        try:
            LabelBase.register(
                name='Icons',
                fn_regular='assets/fonts/MaterialIcons-Regular.ttf'
            )
        except Exception as e:
            print(f"⚠️  Erro ao registrar ícones: {e}")
        
        try:
            LabelBase.register(
                name="Roboto",
                fn_regular="assets/fonts/NotoSans-Regular.ttf"
            )
        except Exception as e:
            print(f"⚠️  Erro ao registrar NotoSans: {e}")
        
        try:
            LabelBase.register(
                name="Roboto",
                fn_regular="assets/fonts/NotoSansSC-Regular.ttf"
            )
        except Exception as e:
            print(f"⚠️  Erro ao registrar NotoSansSC: {e}")
        
        try:
            LabelBase.register(
                name="Roboto",
                fn_regular="assets/fonts/NotoSansJP-Regular.ttf"
            )

        except Exception as e:
            print(f"⚠️  Erro ao registrar NotoSansJP: {e}")
        
        try:
            LabelBase.register(
                name="Roboto",
                fn_regular="assets/fonts/NotoSansKR-Regular.ttf"
            )
        except Exception as e:
            print(f"⚠️  Erro ao registrar NotoSansKR: {e}")
    
    @staticmethod
    def get_font_for_language(language: str) -> str:
        """
        Retorna o nome da fonte apropriada para o idioma.
        
        Args:
            language: Código do idioma (pt, en, zh, ja, ko, etc.)
        
        Returns:
            Nome da fonte registrada
        
        Examples:
            >>> FontManager.get_font_for_language("pt")
            "NotoSans"
            
            >>> FontManager.get_font_for_language("ja")
            "NotoSansJP"
            
            >>> FontManager.get_font_for_language("zh")
            "NotoSansSC"
        """
        language = language.lower().strip()
        print(language)
        return FontManager.FONT_MAP.get(language, FontManager.DEFAULT_FONT)
    
    @staticmethod
    def get_icon_font() -> str:
        """Retorna o nome da fonte de ícones."""
        return "Icons"
    
    @staticmethod
    def is_cjk_language(language: str) -> bool:
        """
        Verifica se o idioma é CJK (Chinese, Japanese, Korean).
        
        Args:
            language: Código do idioma
        
        Returns:
            True se for CJK, False caso contrário
        """
        cjk_languages = {"zh", "zh-cn", "zh-tw", "ja", "ko", "kr"}
        return language.lower().strip() in cjk_languages


# ============= TESTE =============
if __name__ == "__main__":
    print("🧪 Testando FontManager...\n")
    
    # Registra fontes
    FontManager.register_fonts()
    
    print("\n" + "=" * 60)
    print("📝 Testando mapeamento de fontes")
    print("=" * 60)
    
    # Testa vários idiomas
    test_languages = ["pt", "en", "zh", "ja", "ko", "ru", "es", "fr", "xx"]
    
    for lang in test_languages:
        font = FontManager.get_font_for_language(lang)
        is_cjk = "✅ CJK" if FontManager.is_cjk_language(lang) else "❌ Não-CJK"
        print(f"{lang.upper():6} → {font:15} | {is_cjk}")
    
    print("\n✅ Testes concluídos!")