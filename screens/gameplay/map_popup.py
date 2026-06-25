from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.graphics import Color, Ellipse, Line
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.core.window import Window

MAP_REGIONS = {
    # ── Hub Central e Arredores (Noroeste / Centro-Oeste) ────────────────────
    "goldenreach_plains": {"x": 0.380, "y": 0.430},
    "evergreen_kokiri": {"x": 0.170, "y": 0.160},
    "whispering_elwyn": {"x": 0.395, "y": 0.180},
    "azurewind_prairie": {"x": 0.145, "y": 0.390},

    # ── Montanhas e Região Nordeste ──────────────────────────────────────────
    "olympos_peak_base": {"x": 0.585, "y": 0.220},
    "olympos_peak_plateau": {"x": 0.605, "y": 0.200},
    "mount_chillyard_passage": {"x": 0.730, "y": 0.230},
    "mount_chillyard_gorge": {"x": 0.745, "y": 0.260},
    "mount_chillyard_summit": {"x": 0.725, "y": 0.280},
    "howling_crown_range": {"x": 0.720, "y": 0.350},
    "throat_of_rotghar": {"x": 0.810, "y": 0.340},
    "great_jura_wilds": {"x": 0.880, "y": 0.290},
    "petrified_caelum": {"x": 0.935, "y": 0.420},

    # ── Faixa Central-Leste (Campos Secos / Destruídos) ──────────────────────
    "blightgrass_fields_west": {"x": 0.530, "y": 0.505},
    "blightgrass_fields_east": {"x": 0.615, "y": 0.535},
    "spine_of_the_worldshard": {"x": 0.815, "y": 0.510},
    "ashen_summit_of_khar": {"x": 0.830, "y": 0.690},

    # ── Sudoeste (Campos de Batalha e Florestas Escuras) ──────────────────────
    "fields_of_broken_grace": {"x": 0.135, "y": 0.630},
    "fields_of_endless_strife_west": {"x": 0.355, "y": 0.655},
    "fields_of_endless_strife_east": {"x": 0.450, "y": 0.685},
    "shadowed_limgrave": {"x": 0.265, "y": 0.880},
    "fungal_zangarmarsh": {"x": 0.390, "y": 0.870},
    "marshes_of_the_fallen": {"x": 0.485, "y": 0.945},

    # ── Sul / Sudeste (Pântanos, Baías e Delhas) ──────────────────────────────
    "the_tarnished_expanse": {"x": 0.690, "y": 0.705},
    "stagnant_fens": {"x": 0.605, "y": 0.755},
    "misty_swamp_planet": {"x": 0.540, "y": 0.865},
    "quagmire_of_despair": {"x": 0.725, "y": 0.905},
    "toxic_bayou": {"x": 0.895, "y": 0.785},
    "sunken_wilderness": {"x": 0.890, "y": 0.885},
}

MAP_IMAGE_SOURCE = "assets/world_map.png"

# ── constantes visuais do marcador B ─────────────────────────────
PIN_OUTER_R   = 14    # raio do círculo externo (escuro)
PIN_INNER_R   = 6     # raio do ponto luminoso interno
PIN_STEM_W    = 3     # espessura do "pé" do pin
PULSE_MIN_R   = 16    # raio mínimo do anel de pulso
PULSE_MAX_R   = 26    # raio máximo do anel de pulso
PULSE_SPEED   = 18    # px/s de expansão do pulso

COLOR_OUTER   = (0.55, 0.10, 0.10, 1)    # vermelho escuro
COLOR_INNER   = (1.00, 0.27, 0.27, 1)    # vermelho vivo
COLOR_STEM    = (0.30, 0.05, 0.05, 1)    # haste quase preta
COLOR_LABEL   = (0.10, 0.04, 0.02, 1)    # marrom escuro — contrasta no pergaminho


class QuestMapPopup:
    """
    Popup do mapa do mundo com marcadores estilo pin (B) pulsantes
    em todas as regiões com quest ativa.

    Uso:
        self.quest_map_popup = QuestMapPopup()
        ...
        self.quest_map_popup.open(self.qm.get_active_quests(), self.lm)
    """

    def __init__(self):
        self._popup        = None
        self._map_image    = None
        self._marker_layer = None
        self._markers      = []      # lista de dicts com referências do canvas
        self._pulse_event  = None

    # ── API pública ──────────────────────────────────────────────
    def open(self, quests, lm=None):
        self._build_popup()
        by_region = self._group_by_region(quests)

        # on_open + delay garante que o FloatLayout filho já calculou
        # tamanho real antes de _get_image_bounds() ser chamado
        self._popup.bind(
            on_open=lambda *_: Clock.schedule_once(
                lambda dt: self._draw_markers(by_region, lm), 0.15
            )
        )
        self._popup.open()

    def dismiss(self):
        if self._popup:
            self._popup.dismiss()

    # ── construção do popup ─────────────────────────────────────
    def _build_popup(self):
        self._markers = []

        img_w, img_h     = CoreImage(MAP_IMAGE_SOURCE).size
        aspect_ratio     = img_w / img_h
        popup_width_hint = 0.88
        target_w_px      = Window.width * popup_width_hint
        target_h_px      = target_w_px / aspect_ratio
        popup_height_hint = min(target_h_px / Window.height, 0.92)

        root = FloatLayout(size_hint=(1, 1))

        self._map_image = Image(
            source=MAP_IMAGE_SOURCE,
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        root.add_widget(self._map_image)

        # camada de marcadores sobreposta à imagem
        self._marker_layer = FloatLayout(size_hint=(1, 1))
        root.add_widget(self._marker_layer)

        close_btn = Button(
            text="X",
            size_hint=(None, None),
            size=(32, 32),
            pos_hint={"right": 0.99, "top": 0.99},
            background_color=(0.30, 0.05, 0.05, 1),
            color=(0.95, 0.88, 0.78, 1),
        )
        close_btn.bind(on_release=lambda *_: self.dismiss())
        root.add_widget(close_btn)

        self._popup = Popup(
            title="",
            content=root,
            size_hint=(popup_width_hint, popup_height_hint),
            separator_height=0,
            background="",
            background_color=(0, 0, 0, 0),
            auto_dismiss=True,
        )

        # ── DEBUG: clique no mapa imprime as coordenadas relativas ──
        # remova quando as posições estiverem calibradas
        def on_touch_debug(instance, touch):
            if not self._map_image:
                return
            rx, ry, rw, rh = self._get_image_bounds()
            if rx <= touch.x <= rx + rw and ry <= touch.y <= ry + rh:
                rel_x = (touch.x - rx) / rw
                rel_y = 1 - (touch.y - ry) / rh   # invertido (y=0 = topo)
                print(f'[MapDebug] x={rel_x:.3f}, y={rel_y:.3f}')

        self._marker_layer.bind(on_touch_down=on_touch_debug)

    def _group_by_region(self, quests):
        for quest in quests:
            location_key = ""
            if hasattr(quest, "context") and quest.context:
                location_key = quest.context.get("location_key", "")

        by_region = {}
        for quest in quests:
            location_key = ""
            if hasattr(quest, "context") and quest.context:
                location_key = quest.context.get("location_key", "")
            if not location_key or location_key not in MAP_REGIONS:
                continue
            by_region.setdefault(location_key, []).append(quest)

        return by_region

    # ── bounds reais da imagem (desconta letterbox de keep_ratio) ─
    def _get_image_bounds(self):
        img = self._map_image
        tex = img.texture
        if not tex:
            return img.x, img.y, img.width, img.height

        tex_ratio = tex.size[0] / tex.size[1]
        box_ratio = img.width  / img.height

        if box_ratio > tex_ratio:
            # letterbox nas laterais
            real_h = img.height
            real_w = real_h * tex_ratio
            real_x = img.x + (img.width - real_w) / 2
            real_y = img.y
        else:
            # letterbox em cima/baixo
            real_w = img.width
            real_h = real_w / tex_ratio
            real_x = img.x
            real_y = img.y + (img.height - real_h) / 2

        return real_x, real_y, real_w, real_h

    # ── limpeza ──────────────────────────────────────────────────
    def _clear_markers(self):
        if self._marker_layer:
            for m in self._markers:
                lbl = m.get("label")
                if lbl and lbl.parent:
                    self._marker_layer.remove_widget(lbl)
            self._marker_layer.canvas.after.clear()
        self._markers = []

    # ── desenho (canvas aberto UMA VEZ para todos os marcadores) ─
    def _draw_markers(self, by_region, lm):
        self._clear_markers()
        real_x, real_y, real_w, real_h = self._get_image_bounds()

        with self._marker_layer.canvas.after:
            for location_key, quests_here in by_region.items():
                region = MAP_REGIONS[location_key]
                px = real_x + real_w  * region["x"]
                py = real_y + real_h  * (1 - region["y"])

                PIN_RADIUS = 6

                Color(0.75, 0.10, 0.10, 1)

                dot = Ellipse(
                    pos=(px - PIN_RADIUS, py - PIN_RADIUS),
                    size=(PIN_RADIUS * 2, PIN_RADIUS * 2),
                )

                Line(
                    points=[px, py - PIN_RADIUS, px, py - 18],
                    width=2,
                )

                self._markers.append({
                    "dot": dot,
                    "px": px,
                    "py": py,
                })
