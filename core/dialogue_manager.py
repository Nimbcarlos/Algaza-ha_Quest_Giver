# core/dialogue_manager.py
import json
import random
import os
from core.language_manager import LanguageManager


class SafeDict(dict):
    """Dicionário que retorna a própria chave se ela não for encontrada, evitando KeyError no .format()"""
    def __missing__(self, key):
        return f"{{{key}}}"

class DialogueManager:
    def __init__(self, language="en"):
        self.language = language
        self.lm = LanguageManager()
        self.heroes_folder = "data/heroes/dialogues"

    def set_language(self, language):
        self.language = language

    def _load_quest_dialogue(self, quest_id: str) -> dict:
        quest_id_formatted = str(quest_id).zfill(3)
    
        path = os.path.join("data/quests", f"{quest_id_formatted}.json")
        if not os.path.exists(path):
            print(f"[DialogueManager] Quest dialogue não encontrado: {path}")
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[DialogueManager] Erro ao carregar quest {quest_id}: {e}")
            return {}

    def _load_hero_dialogue(self, hero_id: str) -> dict:
        path = os.path.join(self.heroes_folder, f"{hero_id}.json")
        if not os.path.exists(path):
            print(f"[DialogueManager] Arquivo de diálogos não encontrado: {path}")
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[DialogueManager] Erro ao carregar {path}: {e}")
            return {}

    def _resolve_context(self, context):
        if isinstance(context, dict):
            resolved = {}
            for key, value in context.items():
                resolved[key] = self._resolve_context(value)
            return resolved

        elif isinstance(context, list):
            return [self._resolve_context(v) for v in context]

        else:
            return context

    def _resolve_perk(self, heroes: list, context: dict) -> str | None:
        """Retorna o primeiro perk da party que esteja nos perks usados na quest."""
        used_perks = context.get("perks", [])
        party_perks = {perk for h in heroes for perk in getattr(h, "perks", [])}
        for perk in used_perks:
            if perk in party_perks:
                return perk
        return None

    # ─────────────────────────────────────────────────────────────────────
    # 🎯 FUNÇÃO UNIFICADA
    # ─────────────────────────────────────────────────────────────────────
    def show_quest_dialogue(
        self,
        heroes: list,
        quest_id: str,
        result: str,
        quest_type: str = "fight",
        context: dict | None = None
    ) -> list:

        quest_id  = str(quest_id)
        result    = result.lower()

        if isinstance(quest_type, list):
            quest_type = quest_type[0] if quest_type else "fight"
        quest_type = quest_type.lower()

        if context is None:
            context = {}

        resolved_ctx = self._resolve_context(context)
        
        # Injeta bits dinâmicos (enemy_detail, place_detail, etc) para uso no .format()
        dynamic_bits = self._build_dynamic_bits(resolved_ctx)
        resolved_ctx.update(dynamic_bits)
        
        # Garante que todas as chaves gramaticais existam para evitar KeyError
        grammatical_keys = ["do_enemy", "no_enemy", "ao_enemy", "da_place", "na_place", "enemy", "location"]
        for k in grammatical_keys:
            if k not in resolved_ctx:
                # Tenta fallback para chaves básicas
                if k == "enemy": resolved_ctx[k] = resolved_ctx.get("enemy_type") or "inimigo"
                elif k == "location": resolved_ctx[k] = resolved_ctx.get("location_key") or "local"
                else: resolved_ctx[k] = resolved_ctx.get("enemy") or resolved_ctx.get("location") or ""

        # Converte para SafeDict para proteção extra contra chaves inesperadas
        safe_ctx = SafeDict(resolved_ctx)

        # ── Ordenação narrativa: tank → dps → healer ──────────────────
        ROLE_ORDER = {"tank": 0, "dps": 1, "healer": 2}
        ordered_heroes = sorted(
            heroes,
            key=lambda h: ROLE_ORDER.get((h.role or "").lower(), 99)
        )

        if not ordered_heroes:
            return [{"id": "assistant", "text": self.lm.t("assistant_fallback_basic_report")}]

        # ── Herói âncora (primeiro na ordem narrativa) ────────────────
        anchor_id  = str(ordered_heroes[0].id)
        party_key  = "alone" if len(ordered_heroes) == 1 else "group"
        matched_perk = self._resolve_perk(ordered_heroes, context)

        # ── Carrega conclusão da quest ────────────────────────────────
        quest_dialogue   = self._load_quest_dialogue(quest_id)
        conclusion_root  = quest_dialogue.get("conclusion", {}).get(result, {})
        conclusion_texts = (
            conclusion_root.get(matched_perk or "default", {}).get(self.language)
            or conclusion_root.get("default", {}).get(self.language)
        )

        falas = []

        for index, hero in enumerate(ordered_heroes):
            hero_id   = str(hero.id)
            hero_data = self._load_hero_dialogue(hero_id)
            if not hero_data:
                continue

            blocks = hero_data.get("dialogue_blocks", {})
            parts  = []

            narrative_data = resolved_ctx.get("narrative", {})
            # No novo formato, place/enemy estão dentro de um bloco 'narrative' no JSON do herói
            hero_narrative = blocks.get("narrative", {})
                
            # ── ARRIVED: apenas o herói âncora fala ao chegar ─────────
            if hero_id == anchor_id:
                arrived_texts = (
                    blocks.get("arrived", {})
                          .get(party_key, {})
                          .get(self.language)
                )
                if isinstance(arrived_texts, list) and arrived_texts:
                    parts.append(random.choice(arrived_texts).format(**safe_ctx))

            # 1. Escolhe uma categoria de 'place' (history, feeling, landmark, details)
            place_categories = ["history", "feeling", "landmark", "details"]
            random.shuffle(place_categories)
            for cat in place_categories:
                hero_place_tpls = hero_narrative.get("place", {}).get(cat, {}).get(self.language)
                fragments = narrative_data.get("place", {}).get(cat, [])
                if hero_place_tpls and fragments:
                    tpl = random.choice(hero_place_tpls)
                    frag = random.choice(fragments)
                    parts.append(tpl.replace("{fragment}", frag).format(**safe_ctx))
                    break


            # ── ACTION: escolhido pelo tipo da quest ──────────────────
            action_texts = (
                blocks.get("action", {})
                      .get(quest_type, {})
                      .get(party_key, {})
                      .get(self.language)
            )
            if isinstance(action_texts, list) and action_texts:
                parts.append(random.choice(action_texts).format(**safe_ctx))

            # 2. Escolhe uma categoria de 'enemy' (details, attack)
            enemy_categories = ["details", "attack"]
            random.shuffle(enemy_categories)
            for cat in enemy_categories:
                hero_enemy_tpls = hero_narrative.get("enemy", {}).get(cat, {}).get(self.language)
                fragments = narrative_data.get("enemy", {}).get(cat, [])
                if hero_enemy_tpls and fragments:
                    tpl = random.choice(hero_enemy_tpls)
                    frag = random.choice(fragments)
                    parts.append(tpl.replace("{fragment}", frag).format(**safe_ctx))
                    break

            # ── OTHERS: menção a outros heróis da party ───────────────
            if len(ordered_heroes) > 1:
                others_block = blocks.get("others", {})
                candidates = [h for h in ordered_heroes if h.id != hero.id]
                random.shuffle(candidates)

                for other in candidates:
                    other_texts = (
                        others_block.get(str(other.id), {})
                                    .get(party_key, {})
                                    .get(self.language)
                    )
                    if isinstance(other_texts, list) and other_texts:
                        text = random.choice(other_texts).replace(
                            "{hero_name}", getattr(other, "name", f"hero_{other.id}")
                        )
                        parts.append(text.format(**safe_ctx))
                        break

            # ── CONCLUSION: apenas o último herói da party ────────────
            if index == len(ordered_heroes) - 1:
                if isinstance(conclusion_texts, list) and conclusion_texts:
                    parts.append(random.choice(conclusion_texts).format(**safe_ctx))

            if parts:
                falas.append({"id": hero_id, "text": " ".join(parts)})

        return falas or [{"id": "assistant", "text": self.lm.t("assistant_fallback_basic_report")}]

    # ─────────────────────────────────────────────────────────────────────
    # 🎯 DIÁLOGO INICIAL (início da quest)
    # ─────────────────────────────────────────────────────────────────────
    def get_start_dialogue(self, heroes: list, relation_counters: dict = None) -> list:
        if relation_counters is None:
            relation_counters = {}

        falas = []

        for hero in heroes:
            hero_id   = str(hero.id)
            hero_data = self._load_hero_dialogue(hero_id)
            if not hero_data:
                continue

            start_data   = hero_data.get("start_dialogues", {})
            chosen_text  = None

            # Prioridade 1: cadeia de relação com outro herói
            chains = start_data.get("chains", {})
            for other in heroes:
                if other.id == hero.id:
                    continue
                other_key = str(other.id)
                if other_key not in chains:
                    continue
                counter      = relation_counters.get(hero_id, {}).get(other_key, 0)
                lang_block   = chains[other_key].get(str(counter), {})
                chain_texts  = lang_block.get(self.language)
                if isinstance(chain_texts, list) and chain_texts:
                    chosen_text = random.choice(chain_texts)
                    break

            # Prioridade 2: texto padrão
            if not chosen_text:
                default_texts = start_data.get("default", {}).get(self.language)
                if isinstance(default_texts, list) and default_texts:
                    chosen_text = random.choice(default_texts)

            if chosen_text:
                falas.append({"id": hero_id, "text": chosen_text})

        return falas or [{"id": "assistant", "text": self.lm.t("assistant_fallback_silent_start")}]
    
    def _pick_from_context(self, ctx_list):
        if isinstance(ctx_list, list) and ctx_list:
            return random.choice(ctx_list)
        return ""

    def _build_dynamic_bits(self, resolved_ctx):
        narrative = resolved_ctx.get("narrative", {})

        enemy = narrative.get("enemy", {})
        place = narrative.get("place", {})

        # Obtém dados dos sujeitos/locais para concordância
        # Note: 'enemy_data' e 'sub_loc_data' precisariam ser passados no context
        # Se não estiverem lá, o LM usará a lógica padrão de string
        enemy_data = resolved_ctx.get("enemy_data", {})
        sub_loc_data = resolved_ctx.get("sub_location_data", {})

        bits = {
            "enemy_detail": self._pick_from_context(enemy.get("details", [])),
            "enemy_attack": self._pick_from_context(enemy.get("attack", [])),
            "place_detail": self._pick_from_context(place.get("details", [])),
            "place_feeling": self._pick_from_context(place.get("feeling", [])),
            "place_history": self._pick_from_context(place.get("history", [])),
        }

        # Adiciona versões com preposição se os dados estiverem disponíveis
        if enemy_data:
            bits["do_enemy"] = self.lm.get_with_preposition(enemy_data, "de")
            bits["no_enemy"] = self.lm.get_with_preposition(enemy_data, "em")
            bits["ao_enemy"] = self.lm.get_with_preposition(enemy_data, "a")
            bits["o_enemy"] = self.lm.get_with_preposition(enemy_data, "o")
            bits["um_enemy"] = self.lm.get_with_preposition(enemy_data, "um")
        
        if sub_loc_data:
            bits["da_place"] = self.lm.get_with_preposition(sub_loc_data, "de")
            bits["na_place"] = self.lm.get_with_preposition(sub_loc_data, "em")
            bits["a_place"] = self.lm.get_with_preposition(sub_loc_data, "a")

        return bits

if __name__ == "__main__":
    import os
    
    # Mock simples de herói
    class MockHero:
        def __init__(self, id, role="tank", perks=None):
            self.id = id
            self.name = f"Hero_{id}"
            self.role = role
            self.perks = perks or []
    
    def load_quest_context(quest_id):
        """Carrega o context automático da quest"""
        path = os.path.join("data/quests", f"{quest_id}.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("context", {})
            except:
                pass
        return {}
    
    def quick_test():
        dm = DialogueManager(language="pt")
        
        print("\n" + "="*60)
        print("🧪 TESTE RÁPIDO DE DIÁLOGOS")
        print("="*60)
        
        # ─────────────────────────────────────────────────
        # 📝 INPUT DOS DADOS
        # ─────────────────────────────────────────────────
        print("\n📌 Digite os IDs dos heróis (separados por vírgula):")
        print("   Exemplo: 1,2,3")
        hero_ids = input("   IDs: ").strip()
        
        print("\n📌 Digite o ID da quest:")
        quest_id = input("   Quest ID: ").strip()
        
        print("\n📌 Digite o resultado (success/failure):")
        result = input("   Resultado: ").strip() or "success"
        
        print("\n📌 Digite o tipo da quest (fight/thievery/diplomacy/etc):")
        print("   (deixe vazio para auto-detectar)")
        quest_type = input("   Tipo: ").strip()
        
        # ─────────────────────────────────────────────────
        # 🔧 PROCESSAMENTO
        # ─────────────────────────────────────────────────
        
        # Cria heróis
        heroes = []
        roles = ["tank", "dps", "healer"]
        for idx, hid in enumerate(hero_ids.split(",")):
            hid = hid.strip()
            if hid:
                role = roles[idx % len(roles)]
                heroes.append(MockHero(hid, role))
        
        if not heroes:
            print("\n❌ Nenhum herói especificado!")
            return
        
        # Carrega context da quest automaticamente
        context = load_quest_context(quest_id)
        
        # Auto-detecta tipo se não especificado
        if not quest_type:
            quest_path = os.path.join("data/quests", f"{quest_id}.json")
            try:
                with open(quest_path, "r", encoding="utf-8") as f:
                    quest_data = json.load(f)
                    quest_type = quest_data.get("type", "fight")
                    if isinstance(quest_type, list):
                        quest_type = quest_type[0]
            except:
                quest_type = "fight"
        
        # ─────────────────────────────────────────────────
        # ✨ EXECUTA O TESTE
        # ─────────────────────────────────────────────────
        print("\n" + "="*60)
        print("📤 EXECUTANDO...")
        print("="*60)
        print(f"Heróis: {[h.id for h in heroes]}")
        print(f"Quest: {quest_id}")
        print(f"Tipo: {quest_type}")
        print(f"Resultado: {result}")
        print(f"Context: {bool(context)}")
        
        try:
            falas = dm.show_quest_dialogue(
                heroes=heroes,
                quest_id=quest_id,
                result=result,
                quest_type=quest_type,
                context=context
            )
            
            print("\n" + "="*60)
            print("📝 RESULTADO:")
            print("="*60)
            
            for fala in falas:
                print(f"\n[Hero {fala['id']}]")
                print(f"{fala['text']}")
            
            print("\n" + "="*60)
            
        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
    
    # ═══════════════════════════════════════════════════
    # LOOP PRINCIPAL
    # ═══════════════════════════════════════════════════
    while True:
        try:
            quick_test()
            
            print("\n")
            continuar = input("Testar novamente? (s/n): ").strip().lower()
            if continuar != 's':
                print("\n👋 Saindo...")
                break
                
        except KeyboardInterrupt:
            print("\n\n👋 Saindo...")
            break
        except Exception as e:
            print(f"\n❌ Erro inesperado: {e}")
            import traceback
            traceback.print_exc()
            break