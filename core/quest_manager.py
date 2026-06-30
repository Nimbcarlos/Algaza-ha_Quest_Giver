import random

from core.hero_manager import HeroManager
from core.quest import Quest
from core.quest_success_calculator import calculate_success_chance, run_mission_roll
from core.save_manager import save_game, load_game
from core.assistant_manager import AssistantManager
from collections import defaultdict
from core.language_manager import LanguageManager
from core.steam_manager import SteamManager
from core.quest_requirements import (
    check_required_quests,
    check_trigger_on_fail,
    check_not_completed,
    check_min_hero_level,
    check_not_active,
    check_expired_quests,
    check_available_turn,
    process_expired_quests,
)
from core.quest_gen import ProceduralQuestSystem
from core.map_graph import MapGraph


class QuestManager:
    def __init__(self, save_file="auto_save.json"):
        self.completed_quests = defaultdict(set)
        self.failed_quests = set()
        self.active_quests = {}     # {quest_id: {"heroes": [...], "turns_left": n}}
        self.current_turn = 1

        self.save_file = save_file
        self.requirement_checks = [
            check_not_completed,
            check_trigger_on_fail,
            check_required_quests,
            check_min_hero_level,
            check_not_active,
            check_expired_quests,
            check_available_turn,
        ]

        self.lm = LanguageManager()
        self.hero_manager = HeroManager(language=self.lm.language)
        self.quest_registry = {}  # {quest_id: Quest}

        self.quests = Quest.load_quests(language=self.lm.language)
        for quest in self.quests:
            quest.origin = "handcrafted"
            self.quest_registry[quest.id] = quest
        self.procedural_pool = {}  # {seed: Quest}

        self.proc_gen = ProceduralQuestSystem(
            language=self.lm.language,
            data_file="data/quest_data.json"
        )

        self.log_callback = None
        self.dialog_callback = None
        self.ui_callback = None

        self.assistant = AssistantManager(self.lm)
        self.steam = SteamManager()

    # ──────────────────────────────────────────────────────────────────────────
    # UI / Callbacks
    # ──────────────────────────────────────────────────────────────────────────

    def set_log_callback(self, callback):
        self.log_callback = callback

    def _log(self, message: str):
        if self.log_callback:
            self.log_callback(message)

    def set_dialog_callback(self, callback):
        self.dialog_callback = callback

    def set_ui_callback(self, callback):
        self.ui_callback = callback

    # ──────────────────────────────────────────────────────────────────────────
    # Heróis
    # ──────────────────────────────────────────────────────────────────────────

    def get_hero(self, hero_id: str):
        return self.hero_manager.get_hero_by_id(hero_id)

    # ──────────────────────────────────────────────────────────────────────────
    # Quests — Acesso
    # ──────────────────────────────────────────────────────────────────────────

    def get_quest(self, quest_id):
        quest = self.quest_registry.get(quest_id)
        avg_lvl = self._get_average_hero_level()

        if quest:
            return quest

        # fallback procedural
        if isinstance(quest_id, int):
            try:
                quest_data = self.proc_gen.reconstruct_quest_from_seed(quest_id, avg_lvl)
                quest = self.proc_gen.to_quest_object(quest_data)
                quest.origin = "procedural"

                self.quest_registry[quest_id] = quest
                return quest
            except Exception as e:
                print(f"[QM] erro: {e}")

        return None

    # ──────────────────────────────────────────────────────────────────────────
    # Quests — Envio
    # ──────────────────────────────────────────────────────────────────────────

    def send_heroes_on_quest(self, quest_id: int, hero_ids: list[str]):
        quest = self.get_quest(quest_id)

        if not quest:
            return self.lm.t("quest_not_found").format(id=quest_id)

        selected_heroes = [self.get_hero(hid) for hid in hero_ids if self.get_hero(hid)]
        if not selected_heroes:
            return self.lm.t("no_valid_hero_selected")

        for hero in selected_heroes:
            hero.status = "on_mission"

        self.active_quests[quest_id] = {
            "heroes": selected_heroes,
            "turns_left": quest.duration
        }

        self._log(self.lm.t("heroes_sent").format(name=quest.name, turns=quest.duration))

        if self.dialog_callback:
            self.dialog_callback(selected_heroes, quest.id, "start", quest.type, quest.context)

        if self.ui_callback:
            self.ui_callback()

        return self.lm.t("mission_started")

    # ──────────────────────────────────────────────────────────────────────────
    # Quests — Resolução
    # ──────────────────────────────────────────────────────────────────────────

    def resolve_quest(self, quest_id: int, data):
        self.pending_level_ups = []

        heroes = data["heroes"]
        quest = self.get_quest(quest_id)

        if quest is None:
            self._log(self.lm.t("quest_not_found_on_resolve").format(id=quest_id))
            return

        success_chance = calculate_success_chance(heroes, quest)
        result = run_mission_roll(success_chance)
        self.steam.on_quest_resolved(quest, heroes, result)

        if result == "success":
            result_key = self.lm.t(result)
            self._log(self.lm.t("quest_completed").format(name=quest.name, result=result_key))
            self.assistant.speak(
                "assistant_quest_completed",
                name=quest.name,
                result=result_key
            )

            if quest.id not in self.completed_quests:
                self.completed_quests[quest.id] = set()

            if len(heroes) > 1:
                xp_reward = round((quest.rewards.get("xp", 0) / len(heroes)) * 1.2)
            else:
                xp_reward = quest.rewards.get("xp", 0)

            for hero in heroes:
                old_level = hero.level
                self._log(
                    self.lm.t("hero_gained_xp").format(hero=hero.name, xp=xp_reward)
                )
                hero.add_xp(xp_reward)
                new_level = hero.level

                if new_level > old_level:
                    self._log(self.lm.t("hero_leveled_up").format(
                        hero=hero.name, level=new_level
                    ))
                    self.pending_level_ups.append((hero.name, new_level))

                self.completed_quests[quest.id].add(hero.id)

        else:
            self.assistant.speak("assistant_quest_failed", name=quest.name)
            self._log(self.lm.t("quest_failed").format(name=quest.name))

            if quest.return_on_fail:
                quest.available_since_turn = None
            else:
                self.failed_quests.add(quest.id)

        for hero in heroes:
            try:
                hero.status = "idle"
            except Exception:
                pass

        if self.dialog_callback:
            self.dialog_callback(heroes, quest.id, result, quest.type, quest.context)
            self.assistant.on_quest_resolved(quest, result)
            if self.assistant:
                for hero_name, level in self.pending_level_ups:
                    self.assistant.speak("assistant_level_up", hero=hero_name, level=level)

    # ──────────────────────────────────────────────────────────────────────────
    # Quests — Disponibilidade
    # ──────────────────────────────────────────────────────────────────────────

    def available_quests(self):
        process_expired_quests(self)

        quests_list = []
        new_quests = 0

        all_quests = list(self.quest_registry.values())

        for quest in all_quests:
            if (quest.id in self.completed_quests or
                    quest.id in self.failed_quests or
                    quest.id in self.active_quests):
                continue

            self._handle_quest_map_impact(quest)

            passes_requirements = all(
                check(quest, self) for check in self.requirement_checks
            )
            if not passes_requirements:
                continue

            # Marca o turno de nascimento — uma vez, para sempre
            if getattr(quest, "available_since_turn", None) is None:
                quest.available_since_turn = self.current_turn
                new_quests += 1

            quests_list.append(quest)

        if new_quests > 0 and self.assistant:
            if self.assistant.dialogue_box:
                self.assistant.on_new_quests(new_quests)
            else:
                print(f"[Assistente] {new_quests} novas quests disponíveis!")

        return quests_list

    def get_active_quests(self):
        return [self.get_quest(qid) for qid in self.active_quests if self.get_quest(qid)]

    def get_available_quests(self):
        return self.available_quests()

    # ──────────────────────────────────────────────────────────────────────────
    # Turno
    # ──────────────────────────────────────────────────────────────────────────

    def advance_turn(self):
        self.current_turn += 1
        self._ensure_procedural_pool()

        # Notifica expiração de procedurais que não foram aceitas
        for quest in self.procedural_pool.values():
            if (quest.id not in self.active_quests and
                    quest.id not in self.completed_quests and
                    quest.id not in self.failed_quests and
                    hasattr(quest, 'is_expired') and
                    quest.is_expired(self.current_turn)):
                self._log(f"⌛ {quest.name} expirou sem ser aceita.")
                # self.assistant.speak("assistant_quest_expired", name=quest.name)

        # Resolve quests ativas cujo prazo encerrou
        to_resolve = []
        for qid, data in list(self.active_quests.items()):
            data["turns_left"] -= 1
            if data["turns_left"] <= 0:
                to_resolve.append((qid, data))

        for qid, data in to_resolve:
            self.resolve_quest(qid, data)
            self.active_quests.pop(qid, None)

        save_game(self, self.save_file)

    # ──────────────────────────────────────────────────────────────────────────
    # Geração Procedural
    # ──────────────────────────────────────────────────────────────────────────

    def _ensure_procedural_pool(self):
        # Heróis desbloqueados E disponíveis (idle) — quem pode aceitar quests agora
        available_heroes = self.hero_manager.get_available_heroes()
        available_count = len(available_heroes)

        if available_count == 0:
            return  # Ninguém livre, não adianta gerar quests

        active_procedural_count = sum(
            1 for qid in self.active_quests
            if qid in self.procedural_pool
        )

        available_procedural = [
            q for q in self.procedural_pool.values()
            if (q.id not in self.completed_quests and
                q.id not in self.failed_quests and
                q.id not in self.active_quests and
                not (hasattr(q, 'is_expired') and q.is_expired(self.current_turn)))
        ]

        in_play = len(available_procedural) + active_procedural_count

        # Teto: total em jogo não pode passar do número de heróis disponíveis
        headroom = max(0, available_count - in_play)

        # Delta fixo por turno: metade dos disponíveis, limitado pelo headroom
        to_generate = min(available_count // 2, headroom)

        for _ in range(to_generate):
            quest = self._generate_new_procedural()
            if quest:
                self.quest_registry[quest.id] = quest
            else:
                break

    def _get_average_hero_level(self) -> int:
        unlocked = [
            hero for hero in self.hero_manager.all_heroes
            if hero.id in self.hero_manager.unlocked_heroes
        ]
        if not unlocked:
            return 1
        total = sum(h.level for h in unlocked)
        return max(1, total // len(unlocked))

    # ──────────────────────────────────────────────────────────────────────────
    # Pontes / Acessibilidade
    # ──────────────────────────────────────────────────────────────────────────

    def _handle_quest_map_impact(self, quest):
        sub_location_key = quest.context.get("sub_location_key", "")
        location_type = quest.context.get("location_type", "")
        location_key = quest.context.get("location_key", "")

        if not location_key:
            return

        map_graph = MapGraph()

        # 1. distância original
        original_distance = map_graph.get_distance_to(location_key)

        # 2. bloqueia ponte (se for)
        if location_type == "bridge":
            map_graph.block_bridge(sub_location_key)

        # 3. nova distância
        new_distance = map_graph.get_distance_to(location_key)

        # 4. calcula desvio REAL
        if original_distance > 0 and new_distance > 0:
            detour = new_distance - original_distance

            if detour > 0:
                print(f"⏳ +{detour} turnos (desvio real)")
                quest.duration += detour

                if quest.id in self.active_quests:
                    self.active_quests[quest.id]["turns_left"] += detour

        elif new_distance == -1:
            self._log(f"⚠️ Alvo {location_key} tornou-se inalcançável!")

    # ──────────────────────────────────────────────────────────────────────────
    # Utilitários
    # ──────────────────────────────────────────────────────────────────────────

    def load_quests(self, language: str = "pt"):
        self.language = language
        self.quests = Quest.load_quests(language)

    def _revalidate_available_quests(self):
        from core.quest_requirements import (
            check_available_turn,
            check_required_quests,
            check_not_completed,
            check_not_active,
            check_expired_quests
        )
        
        # Para cada quest no catálogo
        for quest in self.quests:
            # Pula se já está completa, ativa ou falhou
            if (quest.id in self.completed_quests or 
                quest.id in self.active_quests or 
                quest.id in self.failed_quests):
                continue
            
            # Verifica se REALMENTE deveria estar disponível
            if not (check_available_turn(quest, self) and
                    check_required_quests(quest, self) and
                    check_not_completed(quest, self) and
                    check_not_active(quest, self) and
                    check_expired_quests(quest, self)):
                
                # Se NÃO deveria estar disponível, reseta o available_since_turn
                quest.available_since_turn = None

    def reset_game_state(self):
        self.current_turn = 1
        self.active_quests = {}
        self.completed_quests = defaultdict(set)
        self.failed_quests = set()
        self.procedural_pool = {}

        for quest in self.quests:
            quest.available_since_turn = None

    def _get_latest_quest_in_location(self, quest):
        latest_turn = -1
        latest_quest = None

        is_bridge = quest.context.get("location_type") == "bridge"

        if is_bridge:
            key_to_compare = quest.context.get("location_key")
        else:
            key_to_compare = quest.context.get("sub_location_key")

        for other in self.quest_registry.values():
            if other.id in self.completed_quests or other.id in self.failed_quests:
                continue

            other_is_bridge = other.context.get("location_type") == "bridge"

            if is_bridge != other_is_bridge:
                continue

            if is_bridge:
                other_key = other.context.get("location_key")
            else:
                other_key = other.context.get("sub_location_key")

            if other_key != key_to_compare:
                continue

            start = getattr(other, "available_since_turn", 0)
            duration = getattr(other, "duration", 1)
            end = start + duration

            if end > latest_turn:
                latest_turn = end
                latest_quest = other

        return latest_quest, latest_turn

    def _generate_new_procedural(self) -> Quest:
        avg_lvl = self._get_average_hero_level()
        quest = self.proc_gen.generate_quest_of_type("fight", avg_lvl)

        location = quest.context.get("sub_location_key", "")

        latest_quest, latest_end = self._get_latest_quest_in_location(quest)

        if latest_quest:
            buffer = random.randint(2, 3)
            quest.available_since_turn = latest_end + buffer
        else:
            quest.available_since_turn = self.current_turn

        queue_size = self._count_queued_in_location(location)

        if queue_size >= 3:
            return None  # 👈 segura geração

        return quest

    def _count_queued_in_location(self, sub_location_key):
        count = 0

        for quest in self.quest_registry.values():
            if quest.id in self.completed_quests or quest.id in self.failed_quests:
                continue

            if quest.context.get("sub_location_key", "") != sub_location_key:
                continue

            if getattr(quest, "available_since_turn", 0) > self.current_turn:
                count += 1

        return count


# import traceback
# import datetime
# import sys
# try:
#     pass
# except Exception as e:
#     exc_type, exc_value, exc_traceback = sys.exc_info()
#     tb_list = traceback.format_exception(exc_type, exc_value, exc_traceback)
#     tb_text = "".join(tb_list)

#     # Extração básica
#     tb = traceback.extract_tb(exc_traceback)
#     filename, line, func, text = tb[-1]

#     # ===============================
#     # 📌 SALVA EM LOG.TXT
#     # ===============================
#     with open("log.txt", "a", encoding="utf-8") as log:
#         log.write("\n" + "=" * 60 + "\n")
#         log.write(f"Erro em: {datetime.now()}\n")
#         log.write(f"Exception: {exc_type.__name__}\n")
#         log.write(f"Arquivo: {filename}\n")
#         log.write(f"Linha: {line}\n")
#         log.write(f"Função: {func}\n")
#         log.write(f"Mensagem: {exc_value}\n")
#         log.write(f"Código: {text}\n")
#         log.write("\n--- Traceback completo ---\n")
#         log.write(tb_text)
#         log.write("\n" + "=" * 60 + "\n")

#     # Mostra no console também
#     print("❌ Erro capturado!")
#     print(tb_text)