from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.uix.widget import Widget

# ── mapa tipo → cor da borda lateral ──────────────────────────
TYPE_COLORS = {
    "fight":        (0.89, 0.29, 0.29, 1),   # vermelho
    "diplomacy":    (0.22, 0.54, 0.87, 1),   # azul
    "nature":       (0.39, 0.60, 0.13, 1),   # verde
    "thievery":     (0.73, 0.46, 0.04, 1),   # âmbar
    "arcana":       (0.33, 0.29, 0.72, 1),   # roxo
    "alchemy":      (0.12, 0.62, 0.60, 1),   # teal
    "cure":         (0.91, 0.45, 0.32, 1),   # coral
    "performance":  (0.83, 0.21, 0.51, 1),   # pink
    "intimidation": (0.37, 0.37, 0.35, 1),   # cinza escuro
    "survival":     (0.24, 0.50, 0.25, 1),   # verde escuro
    "engineering":  (0.45, 0.45, 0.42, 1),   # cinza
    "athletics":    (0.85, 0.33, 0.10, 1),   # laranja
    "stealth":       (0.35, 0.30, 0.60, 1),   # roxo
    "investigation": (0.15, 0.45, 0.75, 1),   # azul médio
    "religion":      (0.80, 0.65, 0.10, 1),   # dourado
    "mining":        (0.50, 0.38, 0.25, 1),   # marrom
    "smithing":      (0.75, 0.38, 0.10, 1),   # laranja ferrugem
}
DEFAULT_BORDER_COLOR = (0.55, 0.55, 0.52, 1)

# ── mapa tipo → cor da tag (bg, texto) ────────────────────────
TAG_COLORS = {
    "fight":        ((0.99, 0.92, 0.92, 1), (0.64, 0.18, 0.18, 1)),
    "diplomacy":    ((0.90, 0.95, 0.98, 1), (0.10, 0.37, 0.65, 1)),
    "nature":       ((0.92, 0.95, 0.87, 1), (0.23, 0.43, 0.07, 1)),
    "thievery":     ((0.98, 0.93, 0.85, 1), (0.52, 0.31, 0.02, 1)),
    "arcana":       ((0.93, 0.92, 0.99, 1), (0.20, 0.17, 0.55, 1)),
    "alchemy":      ((0.88, 0.96, 0.95, 1), (0.06, 0.43, 0.41, 1)),
    "cure":         ((0.99, 0.93, 0.91, 1), (0.65, 0.22, 0.10, 1)),
    "performance":  ((0.98, 0.90, 0.94, 1), (0.60, 0.10, 0.32, 1)),
    "intimidation": ((0.94, 0.94, 0.94, 1), (0.30, 0.30, 0.28, 1)),
    "survival":     ((0.90, 0.96, 0.90, 1), (0.13, 0.35, 0.14, 1)),
    "engineering":  ((0.94, 0.94, 0.93, 1), (0.35, 0.35, 0.33, 1)),
    "athletics":    ((0.99, 0.93, 0.89, 1), (0.60, 0.20, 0.04, 1)),
    "stealth":       ((0.92, 0.92, 0.96, 1), (0.22, 0.18, 0.45, 1)),  # roxo escuro — sombra/furtivo
    "investigation": ((0.90, 0.94, 0.99, 1), (0.08, 0.30, 0.58, 1)),  # azul — lógica/dedução
    "religion":      ((0.99, 0.96, 0.88, 1), (0.55, 0.38, 0.04, 1)),  # dourado — fé/sagrado
    "mining":        ((0.93, 0.91, 0.89, 1), (0.38, 0.28, 0.18, 1)),  # marrom — terra/pedra
    "smithing":      ((0.98, 0.93, 0.88, 1), (0.55, 0.25, 0.05, 1)),  # laranja ferrugem — forja
}
DEFAULT_TAG_COLORS = ((0.94, 0.94, 0.93, 1), (0.37, 0.37, 0.35, 1))

BORDER_W = 4   # largura da barra lateral em px

def _make_tag(text, bg, fg, lm, rf):

    tag = Label(
        text=lm.t(text) if lm else text,
        font_size=rf.font_lg,
        color=fg,
        size_hint=(None, None),
        halign='center',
        valign='middle',
    )

    def update_size(*_):
        padding_x = 16
        padding_y = 8

        tag.texture_update()

        tag.size = (
            tag.texture_size[0] + padding_x,
            tag.texture_size[1] + padding_y
        )

        tag.text_size = tag.size

    tag.bind(
        text=update_size,
        texture_size=update_size
    )

    update_size()

    with tag.canvas.before:
        Color(*bg)
        tag._bg = RoundedRectangle(
            pos=tag.pos,
            size=tag.size,
            radius=[10]
        )

    tag.bind(
        pos=lambda w, v: setattr(w._bg, 'pos', v),
        size=lambda w, v: setattr(w._bg, 'size', v)
    )

    return tag


def _make_tag(text, bg, fg, lm, rf):

    tag = Label(
        text=lm.t(text) if lm else text,
        font_size=rf.font_md,
        color=fg,
        size_hint=(None, None),
        halign="center",
        valign="middle",
    )

    tag.texture_update()

    tag.size = (
        tag.texture_size[0] + 8,
        tag.texture_size[1] + 4
    )

    with tag.canvas.before:
        Color(*bg)
        tag._bg = RoundedRectangle(
            pos=tag.pos,
            size=tag.size,
            radius=[10]
        )

    tag.bind(
        pos=lambda w, v: setattr(w._bg, "pos", v),
        size=lambda w, v: setattr(w._bg, "size", v)
    )

    return tag

class QuestCard(ButtonBehavior, BoxLayout):

    def __init__(self, quest, lm, on_press, rf, **kwargs):
        super().__init__(**kwargs)

        self.orientation  = 'horizontal'
        self.size_hint_y  = None
        self.height       = 55
        self.spacing      = 0
        self.padding      = 0

        self._quest    = quest
        self._lm       = lm
        self._callback = on_press
        self._rf = rf

        # tipos da quest (lista)
        types = quest.type if isinstance(quest.type, list) else [quest.type or '']
        primary_type = (types[0] or '').lower()

        border_color = TYPE_COLORS.get(primary_type, DEFAULT_BORDER_COLOR)

        # ── CANVAS: fundo + borda lateral ─────────────────────
        with self.canvas.before:
            # fundo
            Color(0.78, 0.73, 0.60, 0.6)
            self._bg = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[8]
            )
            # borda lateral (retângulo fino à esquerda)
            Color(*border_color)
            self._bar = RoundedRectangle(
                pos=self.pos,
                size=(BORDER_W, self.height),
                radius=[8, 0, 0, 8],
            )

        self.bind(pos=self._update_canvas, size=self._update_canvas)

        # ── CONTEÚDO ──────────────────────────────────────────
        # padding esquerdo após a barra
        self.add_widget(Widget(size_hint=(None, 1), width=BORDER_W + 8))

        content = BoxLayout(
            orientation='vertical',
            size_hint=(1, 1),
            # spacing=2,
            padding=[0, 8, 8, 8],
        )

        # linha 1: nome + dificuldade
        row1 = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=self._rf.font_xl + 2,
            # spacing=2,
        )

        name_lbl = Label(
            text=quest.name,
            font_size=self._rf.font_xl,
            color=(0.10, 0.06, 0.02, 1),
            halign='left',
            valign='middle',
            size_hint=(1, 1),
            shorten=True,
            shorten_from='right',
        )
        name_lbl.bind(size=lambda w, v: setattr(w, 'text_size', v))
        row1.add_widget(name_lbl)

        # pill de dificuldade
        dif_val  = getattr(quest, 'difficulty', '?')
        dif_bg, dif_fg = self._dif_colors(dif_val)
        dif_lbl  = Label(
            text=f'Dif {dif_val}',
            font_size=self._rf.font_lg,
            bold=True,
            color=dif_fg,
            size_hint=(None, None),
            size=(58, 20),
            halign='center',
            valign='middle',
        )
        dif_lbl.bind(size=lambda w, v: setattr(w, 'text_size', v))
        with dif_lbl.canvas.before:
            Color(*dif_bg)
            dif_lbl._bg = RoundedRectangle(
                pos=dif_lbl.pos, size=dif_lbl.size, radius=[10]
            )
        dif_lbl.bind(
            pos=lambda w, v: setattr(w._bg, 'pos', v),
            size=lambda w, v: setattr(w._bg, 'size', v),
        )
        row1.add_widget(dif_lbl)
        content.add_widget(row1)

        # linha 2: tags de tipo
        row2 = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=22,
            # spacing=2,
        )
        for qt in types[:3]:
            qt_key   = (qt or '').lower()
            bg, fg   = TAG_COLORS.get(qt_key, DEFAULT_TAG_COLORS)
            tag_text = lm.t(qt_key) if lm else qt_key
            row2.add_widget(_make_tag(tag_text, bg, fg, self._lm, self._rf))

        content.add_widget(row2)
        self.add_widget(content)

        # callback
        if on_press:
            self.bind(on_release=lambda *_: on_press(quest))

    # ── CANVAS UPDATE ──────────────────────────────────────────
    def _update_canvas(self, *_):
        self._bg.pos  = self.pos
        self._bg.size = self.size
        self._bar.pos = self.pos
        self._bar.size = (BORDER_W, self.height)

    # ── COR DA DIFICULDADE ─────────────────────────────────────
    @staticmethod
    def _dif_colors(dif):
        try:
            v = float(dif)
        except (TypeError, ValueError):
            return (0.94, 0.94, 0.93, 1), (0.37, 0.37, 0.35, 1)
        if v <= 1.0:
            return (0.92, 0.95, 0.87, 1), (0.23, 0.43, 0.07, 1)   # verde
        if v <= 2.0:
            return (0.98, 0.93, 0.85, 1), (0.52, 0.31, 0.02, 1)   # âmbar
        return     (0.99, 0.92, 0.92, 1), (0.64, 0.18, 0.18, 1)   # vermelho