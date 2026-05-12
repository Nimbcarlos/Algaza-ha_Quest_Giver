from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from core.language_manager import LanguageManager
from core.hero import Hero


def show_hero_details(screen_instance, hero, parent_size):
    lm = getattr(screen_instance, "lm", LanguageManager())
    language = lm.language
    frame_width, frame_height = parent_size

    popup_width = frame_width * 0.70
    popup_height = frame_height * 0.90

    root = BoxLayout(orientation="horizontal", spacing=15, padding=10)

    # ═══════════════════════════════════════════════
    # 🖼️ RETRATO
    # ═══════════════════════════════════════════════

    portrait = Image(
        source=hero.photo_body_url or "assets/img/default_hero.png",
        size_hint=(0.55, 1),
        width=350,
        allow_stretch=True,
        keep_ratio=True
    )
    root.add_widget(portrait)

    # ═══════════════════════════════════════════════
    # 📜 CONTEÚDO
    # ═══════════════════════════════════════════════
    content = BoxLayout(orientation="vertical", spacing=15)

    # ── Nome
    content.add_widget(Label(
        text=f"[b]{hero.name} {hero.last_name}[/b]",
        markup=True,
        font_size=max(38, int(frame_height * 0.0335)),
        color=(0, 0, 0, 1),
        size_hint_y=None,
        height=50,
        halign="left",
        valign="middle"
    ))

    # ── Classe + Role
    role_text = lm.t(f"role_{hero.role}") if hero.role else "—"
    content.add_widget(Label(
        text=f"{lm.t(hero.hero_class)} • {role_text}",
        font_size=max(22, int(frame_height * 0.0295)),
        color=(0, 0, 0, 1),
        size_hint_y=None,
        height=24,
        halign="left",
        valign="middle"
    ))
    content.add_widget(Label(
        text=f'{lm.t("level_label")}: {hero.level} ',
        font_size=max(22, int(frame_height * 0.0295)),
        color=(0, 0, 0, 1),
        size_hint_y=None,
        height=24,
        halign="left",
        valign="middle"
    ))

    # ═══════════════════════════════════════════════
    # 📊 STATS
    # ═══════════════════════════════════════════════
    def stat(label, value):
        return Label(
            text=f"[b]{lm.t(label)}[/b]: {value}",
            font_size=max(22, int(frame_height * 0.0295)),
            markup=True,
            color=(0, 0, 0, 1),
            halign="left",
            valign="middle"
        )

    stats_box = BoxLayout(orientation="vertical", size_hint_y=None, height=90)

    row1 = BoxLayout()
    row1.add_widget(stat("strength", hero.stats.get("strength", 0)))
    row1.add_widget(stat("intelligence", hero.stats.get("intelligence", 0)))
    stats_box.add_widget(row1)

    row2 = BoxLayout()
    row2.add_widget(stat("dexterity", hero.stats.get("dexterity", 0)))
    row2.add_widget(stat("wisdom", hero.stats.get("wisdom", 0)))
    stats_box.add_widget(row2)

    content.add_widget(stats_box)

    # ═══════════════════════════════════════════════
    # 🎒 PERKS
    # ═══════════════════════════════════════════════
    if hero.perks:
        perks_text = " • ".join(
            lm.t(f"{perk}") for perk in hero.perks
        )
    else:
        perks_text = lm.t("no_perks")

    content.add_widget(Label(
        text=f"[b]{perks_text}[/b]",
        font_size=max(22, int(frame_height * 0.0295)),
        markup=True,
        color=(0, 0, 0, 1),
        size_hint_y=None,
        height=26,
        halign="left",
        valign="middle"
    ))

    # ═══════════════════════════════════════════════
    # ── SEPARADOR
    # ═══════════════════════════════════════════════
    content.add_widget(Image(
        source="assets/img/separator.png",
        size_hint_y=None,
        height=24,
        allow_stretch=True
    ))

    # ═══════════════════════════════════════════════
    # 📖 HISTÓRIA
    # ═══════════════════════════════════════════════
    story_scroll = ScrollView()
    heroes = Hero.get_hero_by_id(hero.id, language=language)

    story_label = Label(
        text=heroes.story or "",
        font_size=max(22, int(frame_height * 0.0295)),
        markup=True,
        color=(0, 0, 0, 1),
        halign="left",
        valign="top",
        size_hint_y=None
    )
    story_label.bind(
        texture_size=lambda i, v: setattr(story_label, "height", v[1])
    )
    story_label.bind(
        size=lambda i, v: setattr(story_label, "text_size", (v[0] - 20, None))
    )

    story_scroll.add_widget(story_label)
    content.add_widget(story_scroll)

    root.add_widget(content)
    # ═══════════════════════════════════════════════
    # 🪟 POPUP
    # ═══════════════════════════════════════════════
    Popup(
        title='',
        content=root,
        size_hint=(None, None),
        size=(popup_width, popup_height),
        title_align="center",
        title_color=(0, 0, 0, 1),
        title_size=1,
        separator_height=0,
        background="assets/background_ls.png",
        auto_dismiss=True
    ).open()
