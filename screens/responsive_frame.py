from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout


class ResponsiveFrame(BoxLayout):
    """
    Wrapper do layout principal — centraliza apenas o que ainda não é
    proporcional no build: largura do main_layout e tamanho de fontes.

    Uso no build:
        self.rf = ResponsiveFrame()
        self.main_layout = BoxLayout(
            size_hint_x = self.rf.main_width,
            pos_hint    = {"center_x": 0.5, "center_y": 0.5},
            ...
        )

    Uso nas fontes:
        label.font_size = self.rf.font_md
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._w = Window.width
        self._tier = self._detect_tier()

    # ── TIER ──────────────────────────────────────────────────────────────────
    def _detect_tier(self) -> str:
        w = self._w
        if   w <= 800:  return "xs"   # 800×600
        elif w <= 1024: return "sm"   # 1024×768
        elif w <= 1280: return "md"   # 1280×720
        elif w <= 1366: return "lg"   # 1366×768
        else:           return "xl"   # 1920×1080

    # ── LARGURA DO MAIN_LAYOUT ────────────────────────────────────────────────
    @property
    def main_width(self) -> float:
        return {
            "xs": 1.00,
            "sm": 0.97,
            "md": 0.94,
            "lg": 0.90,
            "xl": 0.78,
        }.get(self._tier, 0.9)

    # ── FONTES ────────────────────────────────────────────────────────────────
    # Escala suave: cada tier sobe ~1-2px por step.
    # Baseline md (1280×720) = valores "normais" de design.

    @property
    def padding_resp(self) -> int:
        return {"xs": 10,  "sm": 12,  "md": 14, "lg": 15, "xl": 16}[self._tier]

    @property
    def font_xs(self) -> int:
        return {"xs": 9,  "sm": 9,  "md": 10, "lg": 10, "xl": 11}[self._tier]

    @property
    def font_sm(self) -> int:
        return {"xs": 10, "sm": 11, "md": 12, "lg": 12, "xl": 13}[self._tier]

    @property
    def font_md(self) -> int:
        """Corpo de texto geral, labels de quest, nível do herói."""
        return {"xs": 11, "sm": 12, "md": 13, "lg": 13, "xl": 15}[self._tier]

    @property
    def font_lg(self) -> int:
        """Nomes de quest, nome do herói no card."""
        return {"xs": 13, "sm": 14, "md": 15, "lg": 16, "xl": 18}[self._tier]

    @property
    def font_xl(self) -> int:
        """Títulos de seção, nome da quest selecionada no topo."""
        return {"xs": 15, "sm": 16, "md": 18, "lg": 19, "xl": 22}[self._tier]

    @property
    def font_title(self) -> int:
        """Título de popups, cabeçalhos grandes."""
        return {"xs": 18, "sm": 20, "md": 26, "lg": 28, "xl": 30}[self._tier]

    @property
    def hero_card_size(self):

        return {
            "xs": (80, 120),
            "sm": (90, 135),
            "md": (100, 150),
            "lg": (110, 165),
            "xl": (125, 185),
        }.get(self._tier, (100, 150))

    # ── UTILITÁRIOS ───────────────────────────────────────────────────────────
    @property
    def size(self) -> tuple:
        """Compatibilidade com show_hero_details(parent_size=rf.size)."""
        return Window.size

    @property
    def tier(self) -> str:
        return self._tier

    def __repr__(self):
        w    = getattr(self, '_w',    '?')
        tier = getattr(self, '_tier', '?')
        mw   = getattr(self, 'main_width', '?') if tier != '?' else '?'
        return f"<ResponsiveFrame {w}px tier={tier} main_width={mw}>"    