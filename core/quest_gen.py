import json
import random
from pathlib import Path
from typing import Dict, List, Literal, Optional, TypedDict

from core.quest import Quest


QuestType = Literal[
    "fight",
    "diplomacy",
    "nature",
    "athletics",
    "thievery",
    "religion",
    "arcana",
    "intimidation",
    "survival",
    "cure",
    "performance",
    "investigation",
    "alchemy",
    "stealth",
]


class QuestData(TypedDict, total=False):
    seed: int
    id: int
    name: Dict[str, str]
    description: Dict[str, str]
    type: str
    max_heroes: int
    expired_at: int
    available_from_turn: int
    duration: int
    difficulty: int
    rewards: Dict[str, int]
    required_quests: List[int]
    forbidden_quests: List[int]
    required_perks: List[str]
    context: Dict[str, str]
    conclusion: Dict[str, Dict[str, str]]
    is_procedural: bool


class ProceduralQuestSystem:

    SUPPORTED_LANGUAGES = {"pt", "en", "es", "zh", "ja", "ru"}

    def __init__(self, language: str = "pt", data_file: str = "data/quest_data"):
        self.language = language if language in self.SUPPORTED_LANGUAGES else "pt"

        try:
            from core.language_manager import LanguageManager
            self.lm = LanguageManager()
            self.lm.set_language(self.language)
        except ImportError:
            self.lm = None

        path = Path(data_file)
        if path.suffix == ".json":
            self.data_dir = path.parent / path.stem
        else:
            self.data_dir = path

        self.actions: Dict = {}
        self.subjects: Dict = {}
        self.locations: Dict = {}
        self.sub_locations: Dict = {}
        self.modifiers: Dict = {}
        self.incompatible_modes: Dict = {}
        self.text_fragments: Dict = {}
        self.action_subject_rules: Dict = {}
        self.modifier_subject_rules: Dict = {}
        self.modifier_chance_by_action: Dict = {}
        self.max_heroes_weights: Dict = {}

        self.location_groups_raw: Dict = {}
        self.sub_location_groups_raw: Dict = {}

        self.type_by_id: Dict = {}
        self.verb_by_type_and_id: Dict = {}
        self.subject_by_id: Dict = {}
        self.location_by_id: Dict = {}
        self.sub_location_by_id: Dict = {}
        self.modifier_by_id: Dict = {}

        self.seeds = {
            "available": set(),
            "active": {},
            "completed": set(),
        }

        self._load_data()
        self._build_indexes()


    # ============================================================
    # LOAD / INDEX
    # ============================================================

    def _load_file(self, filename: str) -> Dict:
        """
        Carrega um arquivo JSON da pasta de dados.
        Lança ValueError com nome do arquivo se falhar — facilita debug
        quando um dos arquivos está corrompido ou ausente.
        """
        path = self.data_dir / filename
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"[ProcSystem] ❌ Arquivo não encontrado: {path}")
            return {}
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Erro ao ler {filename}: {e.msg}", e.doc, e.pos
            )

    def _load_data(self) -> None:
        try:
            actions_data        = self._load_file("actions.json")
            subjects_data       = self._load_file("subjects.json")
            locations_data      = self._load_file("locations.json")
            sub_locations_data  = self._load_file("sub_locations.json")
            modifiers_data      = self._load_file("modifiers.json")
            text_fragments_data = self._load_file("text_fragments.json")
            weights_data        = self._load_file("weights.json")

            self.actions               = actions_data
            self.subjects              = subjects_data
            self.modifiers             = modifiers_data
            self.incompatible_modes    = weights_data.get("incompatible_modes", {})
            self.text_fragments        = text_fragments_data
            self.action_subject_rules      = weights_data.get("action_subject_rules", {})
            self.modifier_subject_rules    = weights_data.get("modifier_subject_rules", {})
            self.modifier_chance_by_action = weights_data.get("modifier_chance_by_action", {})
            self.max_heroes_weights        = weights_data.get("max_heroes_weights", {})

            location_groups_data = self._load_file("location_groups.json")

            self.location_groups_raw     = locations_data
            self.sub_location_groups_raw = sub_locations_data
            self.location_groups         = location_groups_data  # biomas: mountain, forest, swamp...

            self.locations     = self._flatten_grouped_entries(self.location_groups_raw,     mode="location")
            self.sub_locations = self._flatten_grouped_entries(self.sub_location_groups_raw, mode="sub_location")

            self._validate_loaded_data()

            total = sum(len(v) for v in [
                self.actions, self.subjects, self.locations,
                self.sub_locations, self.modifiers
            ])
            files = ["actions", "subjects", "locations", "location_groups",
                     "sub_locations", "modifiers", "text_fragments", "weights"]
            print(f"📦 quest_data carregado: {total} entradas / {len(files)} arquivos em {self.data_dir.name}/")

        except json.JSONDecodeError as e:
            print(f"[ProcSystem] ❌ JSON inválido: {e}")
            raise
        except ValueError as e:
            print(f"[ProcSystem] ❌ Dados inválidos: {e}")
            raise

    def _create_default_data(self) -> None:
        self.actions = {}
        self.subjects = {}
        self.locations = {}
        self.sub_locations = {}
        self.modifiers = {}
        self.incompatible_modes = {}
        self.text_fragments = {}
        self.action_subject_rules = {}
        self.modifier_subject_rules = {}
        self.modifier_chance_by_action = {}
        self.max_heroes_weights = {}
        self.location_groups_raw = {}
        self.sub_location_groups_raw = {}
        self.type_by_id = {}
        self.verb_by_type_and_id = {}
        self.subject_by_id = {}
        self.location_by_id = {}
        self.sub_location_by_id = {}
        self.modifier_by_id = {}

    def _flatten_grouped_entries(self, raw_groups: Dict, mode: str) -> Dict:
        flat: Dict = {}

        for group_key, children in raw_groups.items():
            if not isinstance(children, dict):
                raise ValueError(f"Grupo '{group_key}' deve conter um objeto")

            for child_key, child_data in children.items():
                if not isinstance(child_data, dict):
                    raise ValueError(f"Entrada '{child_key}' dentro de '{group_key}' deve ser um objeto")

                item = dict(child_data)
                item["key"] = child_key

                if mode == "location":
                    item.setdefault("group", group_key)
                elif mode == "sub_location":
                    item.setdefault("type", group_key)
                else:
                    raise ValueError(f"Modo inválido em _flatten_grouped_entries: {mode}")

                flat[child_key] = item

        return flat

    def _validate_loaded_data(self) -> None:
        if not self.actions:
            raise ValueError("JSON sem 'actions'")
        if not self.subjects:
            raise ValueError("JSON sem 'subjects'")
        if not self.locations:
            raise ValueError("JSON sem 'locations'")
        if not self.sub_locations:
            raise ValueError("JSON sem 'sub_locations'")
        if not self.modifiers:
            raise ValueError("JSON sem 'modifiers'")

        for action_key, categories in self.action_subject_rules.items():
            if action_key not in self.actions:
                raise ValueError(f"Regra de action_subject_rules para action inexistente: '{action_key}'")
            if not isinstance(categories, list) or not categories:
                raise ValueError(f"action_subject_rules['{action_key}'] deve ser uma lista não vazia")

        for action_key, action_data in self.actions.items():
            if "id" not in action_data:
                raise ValueError(f"Action '{action_key}' sem 'id'")
            if "verbs" not in action_data or not action_data["verbs"]:
                raise ValueError(f"Action '{action_key}' sem verbos")

        for subject_key, subject_data in self.subjects.items():
            sub_location_groups = subject_data.get("locations", [])
            if not isinstance(sub_location_groups, list):
                raise ValueError(f"Subject '{subject_key}' com locations inválido")

            for sub_location_group_key in sub_location_groups:
                if sub_location_group_key not in self.sub_location_groups_raw:
                    raise ValueError(
                        f"Subject '{subject_key}' referencia grupo de sub_location inexistente: '{sub_location_group_key}'"
                    )

        for sub_location_group_key, sub_location_group in self.sub_location_groups_raw.items():
            if not isinstance(sub_location_group, dict) or not sub_location_group:
                raise ValueError(f"Grupo de sub_locations '{sub_location_group_key}' inválido ou vazio")

            for sub_location_key, sub_location_data in sub_location_group.items():
                location_keys = sub_location_data.get("locations", [])
                if not isinstance(location_keys, list) or not location_keys:
                    raise ValueError(
                        f"Sub-location '{sub_location_key}' sem lista 'locations' válida"
                    )

                for location_key in location_keys:
                    if location_key not in self.locations:
                        raise ValueError(
                            f"Sub-location '{sub_location_key}' referencia location inexistente: '{location_key}'"
                        )

    def _build_indexes(self) -> None:
        self.type_by_id = {
            data["id"]: action_key
            for action_key, data in self.actions.items()
        }

        self.verb_by_type_and_id = {}
        for action_key, action_data in self.actions.items():
            self.verb_by_type_and_id[action_key] = {
                verb_data["id"]: verb_data
                for _, verb_data in action_data.get("verbs", {}).items()
            }

        self.subject_by_id = {
            data["id"]: data
            for _, data in self.subjects.items()
        }

        self.location_by_id = {
            data["id"]: data
            for _, data in self.locations.items()
        }

        self.sub_location_by_id = {
            data["id"]: data
            for _, data in self.sub_locations.items()
        }

        self.modifier_by_id = {
            data["id"]: data
            for _, data in self.modifiers.items()
        }

    # ============================================================
    # RANDOM / LOOKUP
    # ============================================================

    def _random_key(self, mapping: Dict) -> str:
        if not mapping:
            raise ValueError("Map vazio para escolha aleatória")
        return random.choice(list(mapping.keys()))

    def _get_action(self, quest_type: str) -> Dict:
        action = self.actions.get(quest_type)
        if not action:
            raise ValueError(f"Tipo '{quest_type}' não existe no JSON")
        return action

    def _get_verb_data(self, quest_type: str, verb_key: Optional[str] = None) -> Dict:
        action = self._get_action(quest_type)
        verbs = action.get("verbs", {})
        if not verbs:
            raise ValueError(f"Tipo '{quest_type}' não possui verbos")

        if verb_key is None:
            verb_key = self._random_key(verbs)

        verb = verbs.get(verb_key)
        if not verb:
            raise ValueError(f"Verbo '{verb_key}' não existe em '{quest_type}'")
        return verb

    def _get_type_by_id(self, type_id: int) -> str:
        try:
            return self.type_by_id[type_id]
        except KeyError:
            raise ValueError(f"Tipo ID {type_id} não encontrado")

    def _get_verb_by_id(self, quest_type: str, verb_id: int) -> Dict:
        try:
            return self.verb_by_type_and_id[quest_type][verb_id]
        except KeyError:
            raise ValueError(f"Verbo ID {verb_id} não encontrado em '{quest_type}'")

    def _get_subject_by_id(self, subject_id: int) -> Dict:
        try:
            return self.subject_by_id[subject_id]
        except KeyError:
            raise ValueError(f"Subject ID {subject_id} não encontrado")

    def _get_location_by_id(self, location_id: int) -> Dict:
        try:
            return self.location_by_id[location_id]
        except KeyError:
            raise ValueError(f"Location ID {location_id} não encontrado")

    def _get_sub_location_by_id(self, sub_location_id: int) -> Dict:
        try:
            return self.sub_location_by_id[sub_location_id]
        except KeyError:
            raise ValueError(f"Sub-location ID {sub_location_id} não encontrado")

    def _get_modifier_by_id(self, modifier_id: int) -> Dict:
        try:
            return self.modifier_by_id[modifier_id]
        except KeyError:
            raise ValueError(f"Modifier ID {modifier_id} não encontrado")

    # ============================================================
    # SEED
    # ============================================================

    def generate_seed(
        self,
        quest_type: str,
        party_level: int = 1,
        verb_key: Optional[str] = None,
        subject_key: Optional[str] = None,
        location_key: Optional[str] = None,
        sub_location_key: Optional[str] = None,
        modifier_key: Optional[str] = None,
        max_heroes: Optional[int] = None,
        expired_at: Optional[int] = None,
        duration: Optional[int] = None,
    ) -> int:
        action = self._get_action(quest_type)
        verb = self._get_verb_data(quest_type, verb_key)
        subject = self._get_subject_data_for_action(quest_type, party_level, subject_key)
        sub_location = self._get_sub_location_for_subject(subject, sub_location_key)
        location = self._get_location_for_sub_location(sub_location, location_key)
        modifier = self._get_modifier_for_subject(subject, modifier_key, quest_type)

        max_heroes = self._get_max_heroes(max_heroes)
        expired_at = self._clamp(expired_at if expired_at is not None else random.randint(3, 7), 1, 9)
        duration = self._clamp(duration if duration is not None else random.randint(2, 5), 1, 9)

        seed_str = (
            f"{action['id']:02d}"
            f"{verb['id']:02d}"
            f"{subject['id']:02d}"
            f"{location['id']:02d}"
            f"{sub_location.get('id', 0):02d}"
            f"{modifier['id']:02d}"
            f"{max_heroes:01d}"
            f"{expired_at:01d}"
            f"{duration:01d}"
        )
        return int(seed_str)

    def decode_seed(self, seed: int) -> Dict[str, int]:
        seed_str = str(seed).zfill(15)
        return {
            "type_id": int(seed_str[0:2]),
            "verb_id": int(seed_str[2:4]),
            "subject_id": int(seed_str[4:6]),
            "location_id": int(seed_str[6:8]),
            "sub_location_id": int(seed_str[8:10]),
            "modifier_id": int(seed_str[10:12]),
            "max_heroes": int(seed_str[12:13]),
            "expired_at": int(seed_str[13:14]),
            "duration": int(seed_str[14:15]),
        }

    # ============================================================
    # QUEST BUILD
    # ============================================================

    def reconstruct_quest_from_seed(self, seed: int) -> QuestData:
        parts = self.decode_seed(seed)

        quest_type = self._get_type_by_id(parts["type_id"])
        verb = self._get_verb_by_id(quest_type, parts["verb_id"])
        subject = self._get_subject_by_id(parts["subject_id"])
        location = self._get_location_by_id(parts["location_id"])

        sub_location_id = parts.get("sub_location_id", 0)
        if sub_location_id > 0:
            sub_location = self._get_sub_location_by_id(sub_location_id)
        else:
            sub_location = {"id": 0, "pt": "", "en": "", "es": "", "ru": "", "zh": "", "ja": ""}

        modifier = self._get_modifier_by_id(parts["modifier_id"])

        difficulty_value = (
            verb.get("difficulty", 1.0)
            * subject.get("power", 1.0)
            * location.get("danger", 1.0)
            + sub_location.get("danger_add", 0.0)
            + modifier.get("difficulty_add", 0.0)
        )

        heroes_multiplier = {1: 1.00, 2: 1.35, 3: 1.70, 4: 2.05}.get(parts["max_heroes"], 1.0)
        duration_multiplier = {1: 1.00, 2: 1.08, 3: 1.15, 4: 1.22, 5: 1.28}.get(parts["duration"], 1.30)
        xp = int((difficulty_value * 45) * heroes_multiplier * duration_multiplier)

        description = self._generate_description(quest_type, verb, subject, location, sub_location, modifier)
        conclusion = self._generate_conclusion(quest_type, subject, location, sub_location, modifier)
        narrative_context = self._generate_context(subject, location, sub_location, modifier)

        context = {
            "location": self._compose_location_phrase(sub_location, location, self.language),
            "location_key": location.get("key", ""),
            "sub_location_key": sub_location.get("key", ""),
            "location_type": sub_location.get("type", ""),   # ← "bridge", "forest", etc
            "enemy": self._compose_subject_phrase(quest_type, subject, modifier, self.language),
            "enemy_data": subject,
            "enemy_type": self._get_modifier_form(modifier, subject, self.language),
            "subject_category": subject.get("category", "unknown"),
            "action_type": quest_type,
            "narrative": narrative_context[self.language],
            "sub_location_data": sub_location,
        }

        sub_loc_text_pt = self._get_location_with_preposition(sub_location, "em", "pt")
        sub_loc_text_en = self._get_location_with_preposition(sub_location, "em", "en")
        sub_loc_text_es = self._get_location_with_preposition(sub_location, "em", "es")

        return {
            "seed": seed,
            "id": seed,
            "name": {
                "pt": f"{verb.get('pt', '')} {self._compose_subject_phrase(quest_type, subject, modifier, 'pt')} {sub_loc_text_pt}".strip(),
                "en": f"{verb.get('en', '')} {self._compose_subject_phrase(quest_type, subject, modifier, 'en')} {sub_loc_text_en}".strip(),
                "es": f"{verb.get('es', verb.get('en', ''))} {self._compose_subject_phrase(quest_type, subject, modifier, 'es')} {sub_loc_text_es}".strip(),
                "ru": f"{verb.get('ru', '')} {self._compose_subject_phrase(quest_type, subject, modifier, 'ru')}",
                "zh": f"{verb.get('zh', '')} {self._compose_subject_phrase(quest_type, subject, modifier, 'zh')}",
                "ja": f"{verb.get('ja', '')} {self._compose_subject_phrase(quest_type, subject, modifier, 'ja')}",
            },
            "description": description,
            "type": quest_type,
            "max_heroes": parts["max_heroes"],
            "expired_at": parts["expired_at"],
            "available_from_turn": 1,
            "duration": parts["duration"],
            "difficulty": max(1, round(difficulty_value)),
            "rewards": {"xp": xp},
            "required_quests": [],
            "forbidden_quests": [],
            "required_perks": [],
            "context": context,
            "conclusion": conclusion,
            "is_procedural": True,
        }

    def to_quest_object(self, quest_data: QuestData) -> Quest:
        quest = Quest(
            id=quest_data["id"],
            name=quest_data["name"],
            description=quest_data["description"],
            type=quest_data["type"],
            max_heroes=quest_data["max_heroes"],
            expired_at=quest_data.get("expired_at", 5),
            available_from_turn=quest_data.get("available_from_turn", 1),
            duration=quest_data["duration"],
            difficulty=quest_data["difficulty"],
            rewards=quest_data["rewards"],
            required_quests=quest_data.get("required_quests", []),
            forbidden_quests=quest_data.get("forbidden_quests", []),
            required_perks=quest_data.get("required_perks", []),
            context=quest_data.get("context", {}),
            conclusion=quest_data.get("conclusion", {}),
            language=self.language,
        )

        quest.is_procedural = True
        quest.seed = quest_data["seed"]
        return quest

    # ============================================================
    # PUBLIC API
    # ============================================================

    def generate_quest_of_type(self, quest_type: QuestType, party_level: int = 1) -> Quest:
        seed = self.generate_seed(quest_type, party_level)
        quest_data = self.reconstruct_quest_from_seed(seed)
        return self.to_quest_object(quest_data)

    def get_quest_from_seed(self, seed: int) -> Quest:
        quest_data = self.reconstruct_quest_from_seed(seed)
        return self.to_quest_object(quest_data)

    def ensure_min_available(self, min_count: int = 3) -> List[Quest]:
        all_types = list(self.actions.keys())
        if not all_types:
            return []

        while len(self.seeds["available"]) < min_count:
            used_seeds = self.seeds["available"] | set(self.seeds["active"].keys()) | self.seeds["completed"]
            seed = None

            for _ in range(100):
                quest_type = random.choice(all_types)
                candidate = self.generate_seed(quest_type)
                if candidate not in used_seeds:
                    seed = candidate
                    break

            if seed is None:
                break

            self.seeds["available"].add(seed)

        return self.get_available_quests()

    def get_available_quests(self) -> List[Quest]:
        return [self.get_quest_from_seed(seed) for seed in self.seeds["available"]]

    def mark_as_active(self, seed: int, heroes: Optional[List[int]] = None, turns_left: int = 1) -> None:
        if seed in self.seeds["available"]:
            self.seeds["available"].remove(seed)

        self.seeds["active"][seed] = {
            "turns_left": max(1, turns_left),
            "heroes": heroes or [],
        }

    def complete_quest(self, seed: int) -> None:
        self.seeds["active"].pop(seed, None)
        self.seeds["available"].discard(seed)
        self.seeds["completed"].add(seed)

    # ============================================================
    # TEXT HELPERS
    # ============================================================

    def _generate_description(self, quest_type: str, verb: dict, subject: dict, location: dict, sub_location: dict, modifier: dict) -> dict:
        fragments_root = self.text_fragments.get("description", {})
        type_fragments = fragments_root.get(quest_type, {})
        result = {}

        for lang in self.SUPPORTED_LANGUAGES:
            intro_tpl = self._pick_fragment(type_fragments, "intro", lang, required=False)
            context_tpl = self._pick_fragment(type_fragments, "objective_context", lang, required=False)
            objective_tpl = self._pick_fragment(type_fragments, "objective", lang, required=False)
            detail_tpl = self._pick_fragment(type_fragments, "detail", lang, required=False)
            pressure_tpl = self._pick_fragment(type_fragments, "pressure", lang, required=False)

            subject_phrase = self._compose_subject_phrase(quest_type, subject, modifier, lang)
            sub = self._get_location_with_preposition(sub_location, "de", lang)
            loc = self._get_location_with_preposition(location, "em", lang)

            location_text = f"{sub} {loc}"

            text_parts = []
            if intro_tpl:
                text_parts.append(intro_tpl.strip())
            if objective_tpl:
                if context_tpl:
                    phrase = f"{objective_tpl.strip()} {subject_phrase} {context_tpl} {location_text}."
                else:
                    phrase = f"{objective_tpl.strip()} {subject_phrase} {location_text}."
                
                text_parts.append(phrase.strip())
            if detail_tpl:
                text_parts.append(
                    detail_tpl.format(
                        verb=self._localize(verb, lang),
                        subject=self._get_subject_text(subject, lang),
                        modifier=self._get_modifier_form(modifier, subject, lang),
                        subject_phrase=subject_phrase,
                        location=location_text,
                    ).strip()
                )
            if pressure_tpl:
                text_parts.append(pressure_tpl.strip())

            result[lang] = " ".join(part for part in text_parts if part).strip()

        return result

    def _generate_conclusion(self, quest_type: str, subject: Dict, location: Dict, sub_location: Dict, modifier: Dict) -> Dict[str, Dict[str, str]]:
        pt_subject = self._get_subject_text(subject, "pt") or "alvos"
        en_subject = self._get_subject_text(subject, "en") or "targets"
        es_subject = self._get_subject_text(subject, "es") or en_subject

        pt_modifier = self._get_modifier_form(modifier, subject, "pt")
        en_modifier = self._get_modifier_form(modifier, subject, "en")
        es_modifier = self._get_modifier_form(modifier, subject, "es") or en_modifier

        pt_location = self._compose_location_phrase(location, sub_location, "pt") or "na região"
        en_location = self._compose_location_phrase(location, sub_location, "en") or "in the region"
        es_location = self._compose_location_phrase(location, sub_location, "es") or en_location

        return {
            "success": {
                "pt": f"A operação contra {pt_subject} {pt_modifier} {pt_location} foi concluída com sucesso.".strip(),
                "en": f"The operation against the {en_modifier} {en_subject} {en_location} was completed successfully.".strip(),
                "es": f"La operación contra {es_subject} {es_modifier} {es_location} fue completada con éxito.".strip(),
            },
            "failure": {
                "pt": f"A missão envolvendo {pt_subject} {pt_modifier} {pt_location} falhou.".strip(),
                "en": f"The mission involving the {en_modifier} {en_subject} {en_location} has failed.".strip(),
                "es": f"La misión relacionada con {es_subject} {es_modifier} {es_location} ha fracasado.".strip(),
            },
        }

    def _localize(self, data: dict, lang: str) -> str:
        value = data.get(lang) or data.get("pt") or data.get("en") or ""
        if isinstance(value, dict):
            return value.get("text", "")
        return value

    def _pick_fragment(self, fragments: dict, group: str, lang: str, required: bool = True) -> str:
        options = fragments.get(group, [])
        if not options:
            return ""
        chosen = random.choice(options)
        return chosen.get(lang) or chosen.get("pt") or chosen.get("en") or ""

    def _compose_subject_phrase(self, quest_type: str, subject: dict, modifier: dict, lang: str) -> str:
        subject_text = self._get_subject_text(subject, lang)
        modifier_text = self._get_modifier_form(modifier, subject, lang)

        action = self.actions.get(quest_type, {})
        use_article = action.get("use_indefinite_article", False)
        grammar = self._get_subject_grammar(subject, lang)
        number = grammar.get("number", "singular")

        forms = modifier.get("forms", {}).get(lang, {})
        placement = "after"
        if "default_before" in forms:
            placement = "before"
        elif "default_after" in forms:
            placement = "after"
        elif lang == "en":
            placement = "before"

        if modifier_text:
            if placement == "before":
                core = f"{modifier_text}{subject_text}".strip() if lang in {"zh", "ja"} else f"{modifier_text} {subject_text}".strip()
            else:
                core = f"{subject_text} {modifier_text}".strip()
        else:
            core = subject_text

        if use_article and number == "singular":
            article = self._get_indefinite_article(subject, lang)
            if article and lang not in {"zh", "ja"}:
                return f"{article} {core}".strip()

        return core

    def _get_subject_grammar(self, subject: dict, lang: str) -> dict:
        value = subject.get(lang, {})
        return value if isinstance(value, dict) else {}

    def _get_subject_text(self, subject: dict, lang: str) -> str:
        subject_data = subject.get(lang) or subject.get("pt") or subject.get("en")
        if isinstance(subject_data, str):
            return subject_data
        if isinstance(subject_data, dict):
            return subject_data.get("text", "")
        return ""

    def _get_indefinite_article(self, subject: dict, lang: str) -> str:
        grammar = self._get_subject_grammar(subject, lang)
        return grammar.get("article_indefinite", "")

    def _get_modifier_form(self, modifier: dict, subject: dict, lang: str) -> str:
        forms = modifier.get("forms", {})
        lang_forms = forms.get(lang, {})

        if lang in {"pt", "es"}:
            grammar = self._get_subject_grammar(subject, lang)
            gender = grammar.get("gender", "m")
            number = grammar.get("number", "singular")
            key = f"{gender}_{number}"
            return lang_forms.get(key, "")

        if "default_before" in lang_forms:
            return lang_forms["default_before"]
        if "default_after" in lang_forms:
            return lang_forms["default_after"]
        return ""

    def _compose_location_phrase(self, location: dict, sub_location: dict, lang: str) -> str:
        loc_text = self._localize(location, lang)
        sub_text = self._localize(sub_location, lang)

        if not sub_text:
            return loc_text
        if not loc_text:
            return sub_text

        if lang == "pt":
            return f"{sub_text} {loc_text.replace('nos ', 'dos ').replace('no ', 'do ').replace('na ', 'da ').replace('nas ', 'das ')}"
        return f"{sub_text} {loc_text}"

    # ============================================================
    # VALIDATION / SELECTION
    # ============================================================

    def _is_valid_subject_for_action(self, quest_type: str, subject: Dict) -> bool:
        allowed_categories = self.action_subject_rules.get(quest_type)
        if not allowed_categories:
            return True

        subject_category = subject.get("category")
        if not subject_category:
            return False

        return subject_category in allowed_categories

    def _get_subject_data_for_action(self, quest_type: str, party_level: int, subject_key: Optional[str] = None) -> Dict:
        if subject_key is not None:
            subject = self.subjects.get(subject_key)
            if not subject:
                raise ValueError(f"Subject '{subject_key}' não existe")
            if not self._is_valid_subject_for_action(quest_type, subject):
                raise ValueError(f"Subject '{subject_key}' incompatível com '{quest_type}'")

            subject_copy = dict(subject)
            subject_copy["key"] = subject_key
            return subject_copy

        candidates = []
        for key, subject in self.subjects.items():
            if not self._is_valid_subject_for_action(quest_type, subject):
                continue

            min_level = subject.get("min_level", 1)
            max_level = subject.get("max_level", 99)
            if party_level < min_level:
                continue

            weight = subject.get("weight", 10)
            if party_level > max_level:
                weight = max(1, weight // 4)

            subject_copy = dict(subject)
            subject_copy["key"] = key
            candidates.append((subject_copy, weight))

        if not candidates:
            raise ValueError(f"Nenhum subject válido para '{quest_type}' no nível {party_level}")

        return self._weighted_choice(candidates)

    def _get_sub_location_for_subject(self, subject: Dict, sub_location_key: Optional[str] = None) -> Dict:
        subject_key = subject.get("key", "?")
        # Grupos permitidos pelo sujeito, ex: ["cave", "mine", "fields", "camp"]
        allowed_group_keys = subject.get("locations", [])

        if not allowed_group_keys:
            raise ValueError(f"Subject '{subject_key}' sem grupos de sub_location definidos")

        valid_sub_locations = []
        
        # Percorre apenas os grupos que o sujeito permite
        for group_key in allowed_group_keys:
            sub_location_group = self.sub_location_groups_raw.get(group_key, {})
            
            for key, sub_location_data in sub_location_group.items():
                # Criamos o objeto completo da sub-localização
                sub_loc = dict(sub_location_data)
                sub_loc["key"] = key
                sub_loc["type"] = group_key # Aqui salvamos se é 'mine', 'farm', etc.
                valid_sub_locations.append(sub_loc)

        if not valid_sub_locations:
            raise ValueError(f"Nenhuma sub_location encontrada para os grupos {allowed_group_keys} do subject '{subject_key}'")

        # Se uma chave específica foi pedida (ex: via semente), valida se ela está na lista de permitidas
        if sub_location_key is not None:
            for sl in valid_sub_locations:
                if sl["key"] == sub_location_key:
                    return sl
            raise ValueError(f"Sub-location '{sub_location_key}' não é permitida para o subject '{subject_key}'")

        # Escolha ponderada entre as opções válidas para o bicho
        weighted_sub_locations = [(sl, sl.get("weight", 10)) for sl in valid_sub_locations]
        return self._weighted_choice(weighted_sub_locations)

    def _get_location_for_sub_location(self, sub_location: Dict, location_key: Optional[str] = None) -> Dict:
        valid_keys = sub_location.get("locations", [])

        if not valid_keys:
            raise ValueError(f"Sub-location '{sub_location.get('key', '')}' sem locations definidas")

        if location_key is not None:
            if location_key not in valid_keys:
                raise ValueError(
                    f"Location '{location_key}' incompatível com sub-location '{sub_location.get('key', '')}'"
                )
            chosen_key = location_key
        else:
            chosen_key = random.choice(valid_keys)

        location = dict(self.locations[chosen_key])
        location["key"] = chosen_key
        return location

    def _is_valid_modifier_for_subject(self, modifier: Dict, subject: Dict) -> bool:
        modifier_key = modifier.get("key")
        if not modifier_key or modifier_key == "none":
            return True

        subject_category = subject.get("category")
        if not subject_category:
            return True

        # Nova lógica: busca quais modificadores são permitidos para a categoria do sujeito
        allowed_modifiers = self.modifier_subject_rules.get(subject_category)
        
        # Se não houver regra específica para a categoria, podemos assumir que todos são permitidos
        # ou manter uma lista restrita. Seguindo sua sugestão, se houver uma lista, validamos nela.
        if allowed_modifiers is None:
            return True

        return modifier_key in allowed_modifiers


    def _get_modifier_for_subject(self, subject: Dict, modifier_key: Optional[str] = None, quest_type: Optional[str] = None) -> Dict:
        if modifier_key:
            modifier = dict(self.modifiers.get(modifier_key, {}))
            if not modifier:
                raise ValueError(f"Modifier '{modifier_key}' não existe")
            modifier["key"] = modifier_key

            if not self._is_valid_modifier_for_subject(modifier, subject):
                raise ValueError(
                    f"Modifier '{modifier_key}' é incompatível com subject category='{subject.get('category')}'"
                )
            return modifier

        subject_category = subject.get("category", "")
        
        # Verifica se a categoria do sujeito exige um modificador (não permite "none")
        # Podemos definir isso no weights.json em uma nova chave "mandatory_modifier_categories"
        # Ou simplesmente checar se a categoria existe em modifier_subject_rules e se queremos forçar.
        # Vou usar uma abordagem flexível: se a categoria estiver em 'mandatory_modifier_categories',
        # ignoramos o peso de 'none'.
        mandatory_categories = self.incompatible_modes.get("mandatory_modifier_categories", [])
        is_mandatory = subject_category in mandatory_categories

        action_rules = self.modifier_chance_by_action.get(quest_type or "", {})
        none_weight = action_rules.get("none", 80) if not is_mandatory else 0
        special_weight = action_rules.get("special", 20)
        
        roll_total = none_weight + special_weight
        
        # Se por algum motivo o total for 0 (ex: mandatory mas sem special_weight), 
        # garantimos que haverá um sorteio.
        if roll_total <= 0:
            roll_total = 100
            special_weight = 100

        roll = random.uniform(0, roll_total)

        if not is_mandatory and roll <= none_weight:
            modifier = dict(self.modifiers["none"])
            modifier["key"] = "none"
            return modifier

        valid_modifiers = []
        for key, mod in self.modifiers.items():
            if key == "none":
                continue
            mod_copy = dict(mod)
            mod_copy["key"] = key
            if self._is_valid_modifier_for_subject(mod_copy, subject):
                valid_modifiers.append((mod_copy, mod_copy.get("weight", 10)))

        if not valid_modifiers:
            modifier = dict(self.modifiers["none"])
            modifier["key"] = "none"
            return modifier

        return self._weighted_choice(valid_modifiers)

    # ============================================================
    # UTILS
    # ============================================================

    @staticmethod
    def _clamp(value: int, min_value: int, max_value: int) -> int:
        return max(min_value, min(max_value, value))

    def _weighted_choice(self, items: list[tuple[dict, int]]) -> dict:
        total = sum(weight for _, weight in items)
        roll = random.uniform(0, total)
        current = 0

        for item, weight in items:
            current += weight
            if roll <= current:
                return item

        return items[-1][0]

    def _weighted_choice_simple(self, choices: list[tuple[object, int]]):
        total = sum(weight for _, weight in choices)
        roll = random.uniform(0, total)
        current = 0

        for value, weight in choices:
            current += weight
            if roll <= current:
                return value

        return choices[-1][0]

    def _get_max_heroes(self, max_heroes: Optional[int], avg_level: int = 1) -> int:
        if max_heroes is not None:
            return self._clamp(max_heroes, 1, 4)

        choices = [(int(k), v) for k, v in self.max_heroes_weights.items()]
        if not choices:
            return random.randint(1, 4)

        level_bias = min(max(avg_level - 1, 0), 3)

        adjusted = []
        for heroes_count, weight in choices:
            # Curva mais suave e previsível
            scale = 1 + (level_bias * 0.25 * (heroes_count - 1))
            adjusted.append((heroes_count, weight * scale))

        return self._clamp(self._weighted_choice_simple(adjusted), 1, 4)

    def _generate_context(self, subject, location, sub_location, modifier):
        result = {}

        for lang in self.SUPPORTED_LANGUAGES:
            enemy_block = {
                "details": self._localize_context_list(subject, "details", lang),
                "behavior": self._localize_context_list(subject, "behavior", lang),
                "attack": self._localize_context_list(subject, "attack", lang),
                "modifier": self._localize_context_list(modifier, "modifier", lang),
            }

            # 🧪 AQUI A MÁGICA ACONTECE
            self._apply_modifier_context_localized(enemy_block, modifier, lang)

            result[lang] = {
                "enemy": enemy_block,
                "place": {
                    "landmark": self._localize_context_list(location, "landmark", lang),
                    "feeling": self._localize_context_list(location, "feeling", lang),
                    "details": self._localize_context_list(sub_location, "details", lang),
                    "history": self._localize_context_list(sub_location, "history", lang),
                }
            }

        return result

    def _localize_context_list(self, data: dict, category: str, lang: str) -> list[str]:
        context = data.get("context", {})
        entries = context.get(category, [])

        result = []
        for entry in entries:
            if isinstance(entry, str):
                result.append(entry)
            elif isinstance(entry, dict):
                text = entry.get(lang) or entry.get("pt") or entry.get("en")
                if text:
                    result.append(text)

        return result

    def _apply_modifier_context_localized(self, enemy_block: dict, modifier: dict, lang: str):
        context = modifier.get("context", {})

        mapping = {
            "details_add": "details",
            "attack_add": "attack",
            "behavior_add": "behavior"
        }

        for mod_key, target_key in mapping.items():
            if mod_key not in context:
                continue

            additions = []
            for entry in context[mod_key]:
                if isinstance(entry, str):
                    additions.append(entry)
                elif isinstance(entry, dict):
                    text = entry.get(lang) or entry.get("pt") or entry.get("en")
                    if text:
                        additions.append(text)

            enemy_block.setdefault(target_key, [])
            enemy_block[target_key].extend(additions)

    def _get_location_with_preposition(self, sub_location: dict, preposition: str, lang: str) -> str:
        if self.lm:
            return self.lm.get_with_preposition(sub_location, preposition, lang)
        
        # Fallback se o LanguageManager não estiver disponível
        data = sub_location.get(lang, {})
        if isinstance(data, str): return data
        return data.get("text") or data.get("base") or ""

    # ============================================================
    # SCOUT
    # ============================================================

    def generate_escort_quest(self, avg_level: int, direction: str = None) -> Quest:
        direction = direction or random.choice(["levar", "trazer"])

        # Sorteia um camp com NPCs
        camp = self._pick_escort_camp()
        npc_group = self._pick_npc_from_camp(camp)

        # Sorteia inimigo para o report (quem atacou no caminho)
        subject = self._pick_subject_for_action("fight", avg_level)
        modifier = self._pick_modifier_for_subject(subject)

        # Location baseada no camp
        location = self._get_location_for_sub_location(camp)

        # Duration baseada na distância se disponível
        camp_key = camp.get("key", "")
        distance = getattr(self, "map_graph", None) and self.map_graph.get_distance_to(camp_key)
        duration = max(2, distance) if distance and distance > 0 else random.randint(2, 4)

        context = {
            "location_key": camp_key,
            "location_type": "camp",
            "action_type": "escort",
            "escort_direction": direction,
            "escort_npc": npc_group,
            "enemy": self._compose_subject_phrase("fight", subject, modifier, self.language),
            "enemy_type": self._get_modifier_form(modifier, subject, self.language),
            "subject_category": subject.get("category", "unknown"),
            "narrative": self._generate_context(subject, location, camp, modifier),
        }

        seed = self._generate_seed(
            action_id=self._get_action_id("escort", direction),
            subject_id=subject.get("id", 0),
            location_id=location.get("id", 0),
            sub_location_id=camp.get("id", 0),
            modifier_id=modifier.get("id", 0),
        )

        difficulty = self._calculate_difficulty(subject, modifier, camp, avg_level)

        return Quest(
            id=seed,
            name=self._compose_escort_name(direction, npc_group, camp),
            description=self._compose_escort_description(direction, npc_group, camp, subject, modifier),
            type="escort",
            max_heroes=self._get_max_heroes(None, avg_level),
            duration=duration,
            difficulty=difficulty,
            expired_at=random.randint(3, 6),
            available_from_turn=0,
            rewards=self._calculate_rewards(difficulty, duration),
            required_quests=[],
            context=context,
            language=self.language,
        )

    def _compose_escort_name(self, direction, npc_group, camp) -> str:
        camp_name = self._get_lang_value(camp, self.language)
        if direction == "levar":
            return f"Escoltar {npc_group} até {camp_name}"
        return f"Resgatar {npc_group} de {camp_name}"

    def _compose_escort_description(self, direction, npc_group, camp, subject, modifier) -> str:
        camp_name = self._get_lang_value(camp, self.language)
        enemy_name = self._compose_subject_phrase("fight", subject, modifier, self.language)
        if direction == "levar":
            return (
                f"Um grupo de {npc_group} precisa chegar a {camp_name}. "
                f"Foram avistados {enemy_name} no caminho — precisamos de proteção."
            )
        return (
            f"{npc_group} estão presos em {camp_name}. "
            f"Há relatos de {enemy_name} bloqueando a rota de volta."
        )

if __name__ == "__main__":
 
    # from kivy.app import App
    # from kivy.uix.boxlayout import BoxLayout
    # from kivy.uix.label import Label
    # from kivy.uix.button import Button
    # from kivy.uix.scrollview import ScrollView
    # class SimpleApp(App):
    #     def build(self):
    #         self.proc = ProceduralQuestSystem(language="pt")
    #         # Create a vertical layout
    #         layout = BoxLayout(orientation='vertical', padding=20, spacing=10)

    #         # Initialize the Label
    #         self.my_label = Label(
    #             text="Name",
    #             halign="left",
    #             valign="top",
    #             text_size=(600, 20),
    #             font_size='20sp',
    #             size_hint_y=None,
    #             )
    #         self.my_label_2 = Label(
    #             text="description",
    #             halign="left",
    #             valign="top",
    #             text_size=(600, 100),
    #             font_size='20sp',
    #             size_hint_y=None,
    #             )
    #         self.my_label_4 = Label(
    #             text="Difficulty",
    #             halign="left",
    #             valign="top",
    #             text_size=(600, None),
    #             font_size='20sp',
    #             size_hint_y=None,
    #             )
    #         self.my_label_4.bind(
    #             texture_size=lambda instance, value: setattr(instance, 'height', value[1])
    #         )            
    #         self.my_label_4.bind(
    #             size=lambda instance, value: setattr(instance, 'text_size', (value[0] - 20, None))
    #         )

    #         self.scroll_label = ScrollView(size_hint=(1, 1))
    #         self.scroll_label.add_widget(self.my_label_4)

    #         layout.add_widget(self.my_label)
    #         layout.add_widget(self.my_label_2)
    #         layout.add_widget(self.scroll_label)

    #         # Initialize the Button and bind it to a function
    #         btn = Button(text="Click Me", size_hint_y=None, height=50)
    #         btn.bind(on_press=self.on_button_click)
    #         layout.add_widget(btn)

    #         return layout

    #     def on_button_click(self, instance):
    #         quest = self.proc.generate_quest_of_type("fight", 1)
    #         # Update label text when button is pressed
    #         self.my_label.text = f"Quest: {quest.name}"
    #         self.my_label_2.text = f"Description: {quest.description}"
    #         self.my_label_4.text = f"Difficulty: {quest.context}"

    # if __name__ == "__main__":
    #     SimpleApp().run()


    print("=" * 70)
    print("🎲 PROCEDURAL QUEST SYSTEM - TESTE")
    print("=" * 70)

    proc = ProceduralQuestSystem(language="pt")

    for _ in range(20):
        print("─" * 70)
        quest = proc.generate_quest_of_type("fight", 1)
        print(f"ID: {quest.id}")
        print(f"Nome: {quest.name}")
        print(f"Descrição: {quest.description}")
        # print(f"Dificuldade: {quest.difficulty}, max_heroes: {quest.max_heroes}, xp: {quest.rewards}, duration: {quest.duration} turns")
        print(f"Context: {quest.context}")