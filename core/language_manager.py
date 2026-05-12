import json

class LanguageManager:
    def __init__(self, lang_file="data/lang.json", config_file="config.json"):
        self.lang_file = lang_file
        self.config_file = config_file
        self.translations = self._load_translations()
        self.language = self._load_language()

    def _load_translations(self):
        try:
            with open(self.lang_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _load_language(self):
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            return config.get("language", "en")
        except (FileNotFoundError, json.JSONDecodeError):
            return "en"

    def set_language(self, lang_code: str):
        """Muda o idioma e salva no config sem apagar os outros dados."""
        self.language = lang_code

        try:
            # 🔹 Lê o conteúdo atual do config.json
            with open(self.config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Se o arquivo não existir ou estiver corrompido, recria um novo
            config = {}

        # 🔹 Atualiza apenas o idioma
        config["language"] = lang_code

        # 🔹 Salva de volta o arquivo completo
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)

    def t(self, key: str) -> str:
        """Traduz uma chave interna (ex: 'strength' → 'Força')."""
        entry = self.translations.get(key)
        if entry is None:
            return key
        text = entry.get(self.language)
        if text is None:
            return key
        return text

    def rt(self, text: str) -> str:
        """Tradução reversa — obtém a chave interna a partir do texto traduzido."""
        for key, langs in self.translations.items():
            if langs.get(self.language) == text:
                return key
        return text  # se não encontrar, retorna o original

    def get_with_preposition(self, item_data: dict, preposition: str, lang: str = None) -> str:
        """
        Retorna o texto do item com a preposição ou artigo correto.
        Suporta: 'o' (definido), 'um' (indefinido), 'em', 'de', 'a', 'com'.
        """
        lang = lang or self.language
        data = item_data.get(lang, {})
        
        if isinstance(data, str):
            return data

        # 1. Tenta versão pronta no JSON (ex: "with_em", "with_o", "with_um")
        key = f"with_{preposition}"
        base = data.get("base") or data.get("text", "")

        if key in data:
            return f"{data[key]} {base}".strip()

        if not base:
            return ""

        # Lógica automática para Português
        if lang == "pt":
            gender = item_data.get("gender", "m")
            number = item_data.get("number", "singular")

            # Artigos
            if preposition == "o":
                if number == "plural": return f"os {base}" if gender == "m" else f"as {base}"
                return f"o {base}" if gender == "m" else f"a {base}"
            
            if preposition == "um":
                if number == "plural": return f"uns {base}" if gender == "m" else f"umas {base}"
                return f"um {base}" if gender == "m" else f"uma {base}"

            # Preposições
            if preposition == "em":
                if number == "plural": return f"nos {base}" if gender == "m" else f"nas {base}"
                return f"no {base}" if gender == "m" else f"na {base}"

            if preposition == "de":
                if number == "plural": return f"dos {base}" if gender == "m" else f"das {base}"
                return f"do {base}" if gender == "m" else f"da {base}"

            if preposition == "a":
                if number == "plural": return f"aos {base}" if gender == "m" else f"às {base}"
                return f"ao {base}" if gender == "m" else f"à {base}"
            
            if preposition == "com":
                return f"com {base}"

        # Lógica automática para Espanhol
        elif lang == "es":
            gender = item_data.get("gender", "m")
            number = item_data.get("number", "singular")

            # Artigos
            if preposition == "o":
                if number == "plural": return f"los {base}" if gender == "m" else f"las {base}"
                return f"el {base}" if gender == "m" else f"la {base}"
            
            if preposition == "um":
                if number == "plural": return f"unos {base}" if gender == "m" else f"unas {base}"
                return f"un {base}" if gender == "m" else f"una {base}"

            # Preposições
            if preposition == "em":
                if number == "plural": return f"en los {base}" if gender == "m" else f"en las {base}"
                return f"en el {base}" if gender == "m" else f"en la {base}"

            if preposition == "de":
                if number == "plural": return f"de los {base}" if gender == "m" else f"de las {base}"
                # Contração: de + el = del
                return f"del {base}" if gender == "m" else f"de la {base}"

            if preposition == "a":
                if number == "plural": return f"a los {base}" if gender == "m" else f"a las {base}"
                # Contração: a + el = al
                return f"al {base}" if gender == "m" else f"a la {base}"
            
            if preposition == "com":
                return f"con {base}"

        return base

    def get_subject_text(self, subject: dict, lang: str = None) -> str:
        """Retorna apenas o texto base do sujeito no idioma especificado."""
        lang = lang or self.language
        subject_data = subject.get(lang) or subject.get("pt") or subject.get("en")
        if isinstance(subject_data, str):
            return subject_data
        if isinstance(subject_data, dict):
            return subject_data.get("text", "")
        return ""
