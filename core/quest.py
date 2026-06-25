import json
from pathlib import Path
from typing import List, Dict, Optional


class Quest:
    def __init__(
        self,
        id: str,
        name: Dict[str, str],
        description: Dict[str, str],
        type: str,
        max_heroes: int,
        expired_at: int,
        available_from_turn: int,
        duration: int,
        difficulty: int,
        rewards: Dict[str, int],
        required_quests: List[str],
        forbidden_quests: List[str] = None,
        required_fail_quests: List[str] = None,
        return_on_fail: bool = False,
        is_repeatable: int = None,
        required_perks: List[str] = None,
        forbidden_heroes: List[str] = None,
        available_since_turn=None,
        language: str = "en",
        context: dict | None = None,
        conclusion: dict | None = None,
    ):
        self.id = id
        self.language = language

        self._name_data = name or {}
        self._description_data = description or {}

        self.type = type or []
        self.max_heroes = max_heroes
        self.expired_at = expired_at
        self.available_from_turn = available_from_turn
        self.duration = duration
        self.difficulty = difficulty
        self.rewards = rewards
        self.required_quests = required_quests
        self.forbidden_quests = forbidden_quests
        self.required_fail_quests = required_fail_quests
        self.return_on_fail = return_on_fail
        self.is_repeatable = is_repeatable
        self.required_perks = required_perks or []
        self.forbidden_heroes = forbidden_heroes or []
        self.available_since_turn = available_since_turn

        self.remaining_turns = None
        self.conclusion = conclusion or {}
        self.context = context or {}

    # -------------------- Métodos auxiliares --------------------

    def _get_lang_value(self, value):

        if isinstance(value, dict):
            return (
                value.get(self.language)
                or value.get("en")
                or next(iter(value.values()))
            )

        return value

    def _get_lang_list(self, value):
        """Retorna lista traduzida se houver versões por idioma."""
        if isinstance(value, dict):
            return value.get(self.language, [])
        return value or []

    def __str__(self) -> str:
        return (
            f"Id: {self.id}\n"
            f"Quest: {self.name}\n"
            f"Descrição: {self.description}\n"
            f"Tipo: {self.type}\n"
            f"Qtd herois: {self.max_heroes}\n"
            f"Expira em: {self.expired_at}\n"
            f"Duração: {self.duration} turnos\n"
            f"Turnos Restantes: {self.remaining_turns}\n"
            f"Dificuldade: {self.difficulty}\n"
            f"Recompensas: {self.rewards}\n"
            f"Pré-requisitos: {', '.join(str(q) for q in self.required_quests) if self.required_quests else 'Nenhum'}"
            f"\nforbidden_quests: {', '.join(str(q) for q in self.forbidden_quests) if self.forbidden_quests else 'Nenhum'}"
            f"\nFailed Quests: {', '.join(str(q) for q in self.required_fail_quests) if self.required_fail_quests else 'Nenhum'}"
            f"\nRrequired_perks: {', '.join(str(q) for q in self.required_perks) if self.required_perks  else 'Nenhum'}"
            f"\nForbidden Heroes: {', '.join(str(q) for q in self.forbidden_heroes) if self.forbidden_heroes else 'Nenhum'}"
            f"\nIniciada no turno: {self.available_since_turn}"
        )

    def is_expired(self, current_turn: int) -> bool:
        if self.available_since_turn is None:
            return False
        return (current_turn - self.available_since_turn) >= self.expired_at

    def add_travel_delay(self, extra_turns: int, reason: str = "") -> None:
        if extra_turns > 0:
            self.remaining_turns += extra_turns
            if reason:
                print(f"⏳ [{self.name}] +{extra_turns} turnos: {reason}")

    # 🔹 Carrega quests de acordo com o idioma
    @staticmethod
    def load_quests(language="en", quests_folder="data/quests") -> List["Quest"]:
        folder_path = Path(quests_folder)
        
        if not folder_path.exists():
            print(f"⚠️ Pasta '{quests_folder}' não encontrada!")
            return []
        
        quests = []
        
        # Busca todos os arquivos .json na pasta
        for json_file in sorted(folder_path.glob("*.json")):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    hero_data = json.load(f)
                
                # Cria o herói com o idioma especificado
                quest = Quest(language=language, **hero_data)
                quests.append(quest)
                
            except Exception as e:
                print(f"❌ Erro ao carregar '{json_file.name}': {e}")
                continue
        return quests

    @staticmethod
    def get_quest_by_name(name: str, language: str = "en") -> Optional["Quest"]:
        quests = Quest.load_quests(language)
        for q in quests:
            if q.name.lower() == name.lower():
                return q
        return None

    @property
    def name(self):
        return self._get_lang_value(self._name_data)

    @property
    def description(self):
        return self._get_lang_value(self._description_data)
