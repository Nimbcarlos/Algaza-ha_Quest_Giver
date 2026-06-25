import json

class LanguageManager:
    # Idiomas suportados pelo jogo.
    # Usado para validação em set_language() e exposição para a UI.
    SUPPORTED_LANGUAGES = {"pt", "en", "es", "ru", "zh", "ja"}

    # Estrutura declarativa de artigos por idioma.
    # Idiomas sem lógica declarativa implementada (en, ru, zh, ja) não precisam de entrada aqui —
    # get_with_preposition() retorna o base diretamente para eles.
    # Nota: EN tem artigos (a/an/the), RU tem casos, JA tem partículas, ZH usa classificadores.
    # A lógica para esses idiomas pode ser adicionada aqui futuramente sem alterar o motor.
    ARTICLES = {
        "pt": {
            "o":  {("m", "singular"): "o",  ("f", "singular"): "a",   ("m", "plural"): "os",  ("f", "plural"): "as"},
            "um": {("m", "singular"): "um", ("f", "singular"): "uma", ("m", "plural"): "uns", ("f", "plural"): "umas"},
        },
        "es": {
            "o":  {("m", "singular"): "el", ("f", "singular"): "la",  ("m", "plural"): "los", ("f", "plural"): "las"},
            "um": {("m", "singular"): "un", ("f", "singular"): "una", ("m", "plural"): "unos", ("f", "plural"): "unas"},
        },
    }

    # Estrutura declarativa de contrações (preposição + artigo definido).
    CONTRACTIONS = {
        "pt": {
            ("de", "o"): "do",  ("de", "a"): "da",  ("de", "os"): "dos", ("de", "as"): "das",
            ("em", "o"): "no",  ("em", "a"): "na",  ("em", "os"): "nos", ("em", "as"): "nas",
            ("a",  "a"): "à",   ("a",  "as"): "às", ("a",  "o"): "ao",  ("a",  "os"): "aos",
            ("com", ""): "com",
        },
        "es": {
            ("de",  "el"): "del",    ("de",  "la"): "de la",  ("de",  "los"): "de los", ("de",  "las"): "de las",
            ("en",  "el"): "en el",  ("en",  "la"): "en la",  ("en",  "los"): "en los", ("en",  "las"): "en las",
            ("a",   "el"): "al",     ("a",   "la"): "a la",   ("a",   "los"): "a los",  ("a",   "las"): "a las",
            ("con", ""): "con",
        },
    }

    # Ordem de fallback usada em get_subject_text() quando o idioma ativo não está disponível.
    FALLBACK_LANGS = ("pt", "en")

    def __init__(self, lang_file="data/lang.json", config_file="config.json"):
        self.lang_file = lang_file
        self.config_file = config_file
        self.translations = self._load_translations()
        self.language = self._load_language()

    # ─── Carregamento ────────────────────────────────────────────────────────────

    def _load_translations(self) -> dict:
        try:
            with open(self.lang_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            # Arquivo corrompido: não mata o boot, mas avisa para facilitar debug.
            print(f"[LanguageManager] Aviso: '{self.lang_file}' está corrompido. Traduções ignoradas.")
            return {}

    def _load_language(self) -> str:
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            lang = config.get("language", "en")
            # Config antiga pode ter um código inválido; fallback silencioso para "en".
            return lang if lang in self.SUPPORTED_LANGUAGES else "en"
        except (FileNotFoundError, json.JSONDecodeError):
            return "en"

    # ─── Configuração ─────────────────────────────────────────────────────────────

    def set_language(self, lang_code: str):
        """Define o idioma ativo e persiste no config.json.

        Raises:
            ValueError: se lang_code não estiver em SUPPORTED_LANGUAGES.
        """
        lang_code = lang_code.strip().lower()
        if lang_code not in self.SUPPORTED_LANGUAGES:
            raise ValueError(
                f"[LanguageManager] Idioma '{lang_code}' não suportado. "
                f"Opções: {sorted(self.SUPPORTED_LANGUAGES)}"
            )
        self.language = lang_code
        self._update_config({"language": lang_code})

    def _update_config(self, updates: dict):
        """Lê o config existente, mescla updates e salva. Preserva outras chaves."""
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            config = {}
        config.update(updates)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)

    # ─── Tradução ─────────────────────────────────────────────────────────────────

    def t(self, key: str, fallback_lang: str = "en") -> str:
        """Retorna a tradução de key no idioma ativo.

        Tenta, em ordem:
          1. Idioma ativo (self.language)
          2. fallback_lang (padrão: "en")
          3. A própria chave (último recurso — visível na UI como sinal de chave faltando)
        """
        entry = self.translations.get(key)
        if entry is None:
            return key
        return (
            entry.get(self.language)
            or entry.get(fallback_lang)
            or key
        )

    # ─── Texto com preposição/artigo ──────────────────────────────────────────────

    def get_with_preposition(self, item_data: dict, preposition: str, lang: str = None) -> str:
        """Retorna o nome do item precedido da preposição/artigo correto para o idioma.

        Constrói a noun phrase completa: modificador + base.
        (Candidato a rename: build_noun_phrase() / format_noun() quando a API estabilizar.)

        Prioridade:
          1. Exceção manual no JSON (campo with_<preposição>)
             → deve conter APENAS o modificador (ex: "with_de": "do")
             → resultado final: "{modificador} {base}"  →  "do castelo"
          2. Lógica declarativa via ARTICLES + CONTRACTIONS
          3. Fallback: base sem modificador
        """
        lang = lang or self.language
        data = item_data.get(lang, {})

        if isinstance(data, str):
            return data

        base = data.get("base") or data.get("text", "")
        if not base:
            return ""

        # 1. Exceção manual no JSON
        # with_* deve conter APENAS o modificador.
        # Exemplos válidos no JSON:
        #   "with_de": "do"       → "do castelo"
        #   "with_em": "no"       → "no castelo"
        # Nunca coloque a frase completa no with_* — isso causaria duplicação do base.
        manual_key = f"with_{preposition}"
        if manual_key in data:
            return f"{data[manual_key]} {base}".strip()

        # 2. Lógica declarativa (apenas idiomas com entradas em ARTICLES)
        lang_articles = self.ARTICLES.get(lang, {})
        lang_contractions = self.CONTRACTIONS.get(lang, {})

        if lang_articles:
            gender = data.get("gender") or item_data.get("gender", "m")
            number = data.get("number") or item_data.get("number", "singular")

            # Caso: preposição é na verdade um artigo direto ("o castelo", "um castelo")
            if preposition in lang_articles:
                art = lang_articles[preposition].get((gender, number), "")
                return f"{art} {base}".strip()

            # Caso: preposição real → resolve contração com artigo definido
            art_def = lang_articles.get("o", {}).get((gender, number), "")
            contracted = lang_contractions.get((preposition, art_def))
            if contracted:
                return f"{contracted} {base}".strip()

            # Fallback: preposições sem contração (ex: "com", "con")
            fallback_prep = lang_contractions.get((preposition, ""), preposition)
            return f"{fallback_prep} {base}".strip()

        # Idiomas sem lógica declarativa implementada (en, ru, zh, ja): retorna base sem modificador
        return base

    # ─── Texto de sujeito ─────────────────────────────────────────────────────────

    def get_subject_text(self, subject: dict, lang: str = None) -> str:
        """Retorna o texto de um sujeito no idioma ativo, com fallback configurável."""
        lang = lang or self.language
        seen = set()
        langs_to_try = []
        for candidate in (lang,) + self.FALLBACK_LANGS:
            if candidate not in seen:
                seen.add(candidate)
                langs_to_try.append(candidate)
        for candidate in langs_to_try:
            data = subject.get(candidate)
            if data is None:
                continue
            if isinstance(data, str):
                return data
            if isinstance(data, dict):
                text = data.get("text", "")
                if text:
                    return text
        return ""
