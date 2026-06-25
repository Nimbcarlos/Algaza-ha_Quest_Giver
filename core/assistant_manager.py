from core.hero import Hero
import random

class AssistantManager:
    def __init__(self, language_manager, dialogue_box=None):
        self.lm = language_manager
        self.dialogue_box = dialogue_box
        self.first_time = True

        self.id = "assistant"
        self.name = "Lyria"
        self.last_name = "Bloodseeker"
        self.portrait = "assets/img/assistant.png"

        # humores possíveis
        self.moods = ["normal", "happy", "ironic", "dark", "bipolar_up", "bipolar_down"]
        self.current_mood = "normal"  # humor padrão

        self.fake_hero = Hero(
            id=self.id,
            name=self.name,
            last_name=self.last_name,
            role="Assistant",
            hero_class='Assistant',
            status="assistant_only",
            perks=[],
            defects=[],
            story="Sua guia espiritual e companheira de aventuras.",
            photo_url=self.portrait,
            photo_body_url="assets/img/assistantfullbody.png",
            unlock_by_quest=None,
            available_from_turn=0,
            leave_on_quest=False,
            growth_curve={},
            growth_rules={} 
        )

        self.commentary_quests = {
            "0": "assistant_0",
            "997": "assistant_997",
            "998": "assistant_998",
            "999": "assistant_999"
        }

    # -------------------------------------------------------------
    #   ESCOLHA DE HUMOR
    # -------------------------------------------------------------
    def set_mood(self, mood):
        """Define um humor fixo (caso você queira)."""
        if mood in self.moods:
            self.current_mood = mood

    def randomize_mood(self):
        """Randomiza um humor a cada evento."""
        self.current_mood = random.choice(self.moods)

    # -------------------------------------------------------------
    #   FALA COM HUMOR
    # -------------------------------------------------------------
    def speak(self, key, mood=None, **kwargs):
        """Fala da assistente com suporte a humor."""

        # Seleciona o humor
        if mood is None:
            # humor aleatório
            self.randomize_mood()
            mood = self.current_mood
        else:
            # humor forçado
            self.set_mood(mood)

        # carrega as falas
        entry = self.lm.t(key)

        # se for algo tipo {"normal": "...", "ironic": "..."}
        if isinstance(entry, dict):
            msg = entry.get(mood) or entry.get("normal")

            if msg is None:
                msg = f"[missing_translation:{key}:{mood}]"
        else:
            # fallback: tradução simples sem humor
            msg = entry

        msg = msg.format(**kwargs)

        if self.dialogue_box:
            dialogue = [{"id": self.id, "text": msg}]

            self.dialogue_box.queue.append(
                ([self.fake_hero], "assistant_event", dialogue, None)
            )

            if not self.dialogue_box.popup:
                self.dialogue_box._process_next()
        else:
            print(f"[{self.name}] {msg}")

    # ---------------- Eventos principais ----------------
    def on_new_quests(self, count):
        self.speak("assistant_new_quests", count=count)

    def on_heroes_return(self, hero_names):
        self.speak("assistant_heroes_return", heroes=", ".join(hero_names))

    def on_hero_level_up(self, hero_name, level):
        self.speak("assistant_level_up", hero=hero_name, level=level)

    def on_game_start(self):
        if self.first_time:
            self.speak("assistant_intro_1")
            self.speak("assistant_intro_2")
            self.speak("assistant_intro_3")
            self.speak("assistant_intro_4")
            self.speak("assistant_intro_5")
            self.speak("assistant_intro_6")
            self.first_time = False
        else:
            self.speak("assistant_welcome_back")

    def on_quests_expired(self, quest_names):
        self.speak("assistant_quest_expired", quests=", ".join(quest_names))

    def on_quest_resolved(self, quest, result):
        quest_id = str(quest.id)

        # só reage às quests especiais
        if quest_id not in self.commentary_quests:
            return

        key = self.commentary_quests[quest_id]

        if result == "success":
            self.speak(
                f"{key}_success",
                name=quest.name
            )
        else:
            self.speak(
                f"{key}_fail",
                name=quest.name,
                randomize=False
            )
