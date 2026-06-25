# # core/dialogue_manager.py
# import json
# import random
# import os
# from core.language_manager import LanguageManager
# import re

# class SafeDict(dict):
#     """Dicionário que retorna a própria chave se ela não for encontrada, evitando KeyError no .format()"""
#     def __missing__(self, key):
#         return f"{{{key}}}"

# class DialogueManager:
#     def __init__(self, language="en"):
#         self.language = language
#         self.lm = LanguageManager()
#         self.heroes_folder = "data/heroes/dialogues"

#     def set_language(self, language):
#         self.language = language

#     def _load_quest_dialogue(self, quest_id: str) -> dict:
#         quest_id_formatted = str(quest_id).zfill(3)
    
#         path = os.path.join("data/quests", f"{quest_id_formatted}.json")
#         if not os.path.exists(path):
#             print(f"[DialogueManager] Quest dialogue não encontrado: {path}")
#             return {}
#         try:
#             with open(path, "r", encoding="utf-8") as f:
#                 return json.load(f)
#         except Exception as e:
#             print(f"[DialogueManager] Erro ao carregar quest {quest_id}: {e}")
#             return {}

#     def _load_hero_dialogue(self, hero_id: str) -> dict:
#         path = os.path.join(self.heroes_folder, f"{hero_id}.json")
#         if not os.path.exists(path):
#             print(f"[DialogueManager] Arquivo de diálogos não encontrado: {path}")
#             return {}
#         try:
#             with open(path, "r", encoding="utf-8") as f:
#                 return json.load(f)
#         except Exception as e:
#             print(f"[DialogueManager] Erro ao carregar {path}: {e}")
#             return {}

#     def _resolve_context(self, context):
#         if isinstance(context, dict):
#             resolved = {}
#             for key, value in context.items():
#                 resolved[key] = self._resolve_context(value)
#             return resolved

#         elif isinstance(context, list):
#             return [self._resolve_context(v) for v in context]

#         else:
#             return context

#     def _resolve_perk(self, heroes: list, context: dict) -> str | None:
#         """Retorna o primeiro perk da party que esteja nos perks usados na quest."""
#         used_perks = context.get("perks", [])
#         party_perks = {perk for h in heroes for perk in getattr(h, "perks", [])}
#         for perk in used_perks:
#             if perk in party_perks:
#                 return perk
#         return None

#     # ─────────────────────────────────────────────────────────────────────
#     # 🎯 FUNÇÃO UNIFICADA
#     # ─────────────────────────────────────────────────────────────────────
#     def show_quest_dialogue(self, heroes, quest_id, result, quest_type="fight", context=None) -> list:

#         quest_id   = str(quest_id)
#         result     = result.lower()
#         quest_type = (quest_type[0] if isinstance(quest_type, list) else quest_type or "fight").lower()
#         context    = context or {}

#         resolved_ctx = self._resolve_context(context)
#         dynamic_bits = self._build_dynamic_bits(resolved_ctx)
#         resolved_ctx.update(dynamic_bits)
#         self._fill_grammatical_keys(resolved_ctx)   # extrai método auxiliar (ver abaixo)
#         safe_ctx = SafeDict(resolved_ctx)

#         # ── FAILURE → caminho curto ───────────────────────────────────────
#         if result == "failure":
#             return self._build_failure_dialogue(heroes, quest_id, safe_ctx)

#         # ── SUCCESS → caminho completo existente ──────────────────────────
#         return self._build_success_dialogue(heroes, quest_id, quest_type, safe_ctx, resolved_ctx)

#     def _fill_grammatical_keys(self, resolved_ctx):
#         """Garante que todas as chaves gramaticais existam no contexto."""
#         grammatical_keys = [
#             "do_enemy", "no_enemy", "ao_enemy", "o_enemy", "um_enemy",
#             "da_place", "na_place", "a_place", "ao_place", "place",
#             "enemy", "location"
#         ]
#         for k in grammatical_keys:
#             if k not in resolved_ctx:
#                 if k == "enemy":
#                     resolved_ctx[k] = resolved_ctx.get("enemy_type") or self.lm.t("enemy_fallback")
#                 elif k in ("location", "place"):
#                     resolved_ctx[k] = resolved_ctx.get("location_key") or self.lm.t("location_fallback")
#                 else:
#                     base = "enemy" if "enemy" in k else "place"
#                     resolved_ctx[k] = resolved_ctx.get(base, "")

#     def _build_failure_dialogue(self, heroes, quest_id, safe_ctx) -> list:
#         """
#         Gera o diálogo de falha adaptando o texto se o herói estava em uma 
#         missão Solo ou em Grupo, tratando corretamente as tags gramaticais.
#         """
#         ROLE_ORDER = {"tank": 0, "dps": 1, "healer": 2}
#         ordered_heroes = sorted(heroes, key=lambda h: ROLE_ORDER.get((h.role or "").lower(), 99))
        
#         if not ordered_heroes:
#             return [{"id": "assistant", "text": self.lm.t("failure_fallback")}]

#         # Determina a modalidade da equipe
#         is_solo = len(heroes) == 1
#         failure_mode = "solo" if is_solo else "group"

#         # Limpa o safe_ctx de possíveis dicionários de localização/idiomas remanescentes
#         cleaned_ctx = {}
#         for k, v in safe_ctx.items():
#             if isinstance(v, dict):
#                 if self.language in v:
#                     cleaned_ctx[k] = v[self.language]
#                 elif "pt" in v:
#                     cleaned_ctx[k] = v["pt"]
#                 else:
#                     cleaned_ctx[k] = str(v)
#             else:
#                 cleaned_ctx[k] = v
#         safe_ctx.update(cleaned_ctx)

#         # Seleciona o herói âncora do diálogo
#         anchor = ordered_heroes[0]
#         hero_id = str(anchor.id)
#         hero_data = self._load_hero_dialogue(hero_id)
        
#         if hero_data:
#             failure_root = hero_data.get("dialogue_blocks", {}).get("failure", {})
            
#             # 1. Tenta buscar a lista de textos baseado no modo (solo ou group)
#             failure_texts = failure_root.get(failure_mode, {}).get(self.language)
            
#             # 2. FALLBACK: Se não achar a nova estrutura estruturada, busca o formato antigo
#             if not failure_texts and isinstance(failure_root.get(self.language), list):
#                 failure_texts = failure_root.get(self.language)
#                 print(f"[DialogueManager] Usando fallback antigo de falha para o herói {hero_id}")

#             # Se encontrou falas válidas, renderiza uma aleatória
#             if isinstance(failure_texts, list) and failure_texts:
#                 raw = random.choice(failure_texts)
#                 text = raw.format(**safe_ctx)
#                 return [{"id": hero_id, "text": text}]

#         return [{"id": hero_id, "text": self.lm.t("failure_fallback")}]

#     def _build_success_dialogue(self, heroes, quest_id, quest_type, safe_ctx, resolved_ctx) -> list:
#         ROLE_ORDER = {"tank": 0, "dps": 1, "healer": 2}
#         ordered_heroes = sorted(heroes, key=lambda h: ROLE_ORDER.get((h.role or "").lower(), 99))

#         if not ordered_heroes:
#             return [{"id": "assistant", "text": self.lm.t("assistant_fallback_basic_report")}]

#         anchor_id = str(ordered_heroes[0].id)
#         party_key = "alone" if len(ordered_heroes) == 1 else "group"
#         matched_perk = self._resolve_perk(ordered_heroes, resolved_ctx)

#         quest_dialogue = self._load_quest_dialogue(quest_id)
#         conclusion_root = quest_dialogue.get("conclusion", {}).get("success", {})
#         conclusion_texts = (
#             conclusion_root.get(matched_perk or "default", {}).get(self.language)
#             or conclusion_root.get("default", {}).get(self.language)
#         )

#         falas = []
#         narrative_data = resolved_ctx.get("narrative", {})

#         for index, hero in enumerate(ordered_heroes):
#             hero_id = str(hero.id)
#             hero_data = self._load_hero_dialogue(hero_id)
#             if not hero_data: continue

#             blocks = hero_data.get("dialogue_blocks", {})
#             hero_narrative = blocks.get("narrative", {})
#             parts = []

#             # ── ARRIVED (Anchor only)
#             if hero_id == anchor_id:
#                 arrived_texts = blocks.get("arrived", {}).get(party_key, {}).get(self.language)
#                 if isinstance(arrived_texts, list) and arrived_texts:
#                     parts.append(random.choice(arrived_texts).format(**safe_ctx))

#             # ── PLACE NARRATIVE
#             place_categories = ["history", "feeling", "landmark", "details"]
#             random.shuffle(place_categories)
#             for cat in place_categories:
#                 hero_place_tpls = hero_narrative.get("place", {}).get(cat, {}).get(self.language)
#                 fragments = narrative_data.get("place", {}).get(cat, [])
#                 if hero_place_tpls and fragments:
#                     tpl = random.choice(hero_place_tpls)
#                     frag = random.choice(fragments)
#                     parts.append(tpl.replace("{fragment}", frag).format(**safe_ctx))
#                     break

#             # ── ACTION
#             action_texts = blocks.get("action", {}).get(quest_type, {}).get(party_key, {}).get(self.language)
#             if isinstance(action_texts, list) and action_texts:
#                 parts.append(random.choice(action_texts).format(**safe_ctx))

#             # ── ENEMY NARRATIVE
#             enemy_categories = ["details", "attack"]
#             random.shuffle(enemy_categories)
#             for cat in enemy_categories:
#                 hero_enemy_tpls = hero_narrative.get("enemy", {}).get(cat, {}).get(self.language)
#                 fragments = narrative_data.get("enemy", {}).get(cat, [])
#                 if hero_enemy_tpls and fragments:
#                     tpl = random.choice(hero_enemy_tpls)
#                     frag = random.choice(fragments)
#                     parts.append(tpl.replace("{fragment}", frag).format(**safe_ctx))
#                     break

#             # ── OTHERS (Interaction)
#             if len(ordered_heroes) > 1:
#                 others_block = blocks.get("others", {})
#                 candidates = [h for h in ordered_heroes if h.id != hero.id]
#                 random.shuffle(candidates)
#                 for other in candidates:
#                     other_texts = others_block.get(str(other.id), {}).get(party_key, {}).get(self.language)
#                     if isinstance(other_texts, list) and other_texts:
#                         text = random.choice(other_texts).replace("{hero_name}", getattr(other, "name", f"hero_{other.id}"))
#                         parts.append(text.format(**safe_ctx))
#                         break

#             # ── CONCLUSION (Last hero only)
#             if index == len(ordered_heroes) - 1:
#                 if isinstance(conclusion_texts, list) and conclusion_texts:
#                     parts.append(random.choice(conclusion_texts).format(**safe_ctx))

#             if parts:
#                 falas.append({"id": hero_id, "text": " ".join(parts)})

#         return falas or [{"id": "assistant", "text": self.lm.t("assistant_fallback_basic_report")}]

#     # def show_quest_dialogue(
#     #     self,
#     #     heroes: list,
#     #     quest_id: str,
#     #     result: str,
#     #     quest_type: str = "fight",
#     #     context: dict | None = None
#     # ) -> list:

#     #     quest_id  = str(quest_id)
#     #     result    = result.lower()

#     #     if isinstance(quest_type, list):
#     #         quest_type = quest_type[0] if quest_type else "fight"
#     #     quest_type = quest_type.lower()

#     #     if context is None:
#     #         context = {}

#     #     resolved_ctx = self._resolve_context(context)

#     #     # Injeta bits dinâmicos (enemy_detail, place_detail, etc) para uso no .format()
#     #     dynamic_bits = self._build_dynamic_bits(resolved_ctx)
#     #     resolved_ctx.update(dynamic_bits)
        
#     #     # Garante que todas as chaves gramaticais existam para evitar KeyError
#     #     # Adicionada a chave 'place' que estava faltando e causando erro
#     #     grammatical_keys = [
#     #         "do_enemy", "no_enemy", "ao_enemy", "o_enemy", "um_enemy",
#     #         "da_place", "na_place", "a_place", "ao_place", "place",
#     #         "enemy", "location"
#     #     ]
#     #     for k in grammatical_keys:
#     #         if k not in resolved_ctx:
#     #             # Tenta fallback para chaves básicas
#     #             if k == "enemy": 
#     #                 resolved_ctx[k] = resolved_ctx.get("enemy_type") or (self.lm.t("enemy_fallback") if hasattr(self.lm, 't') else "enemy")
#     #             elif k in ["location", "place"]: 
#     #                 resolved_ctx[k] = resolved_ctx.get("location_key") or (self.lm.t("location_fallback") if hasattr(self.lm, 't') else "location")
#     #             else: 
#     #                 # Para chaves gramaticais (preposições), se não for PT/ES, o fallback deve ser a própria palavra ou vazio
#     #                 base_key = "enemy" if "enemy" in k else "place"
#     #                 resolved_ctx[k] = resolved_ctx.get(base_key, "")

#     #     # Converte para SafeDict para proteção extra contra chaves inesperadas
#     #     safe_ctx = SafeDict(resolved_ctx)

#     #     # ── Ordenação narrativa: tank → dps → healer ──────────────────
#     #     ROLE_ORDER = {"tank": 0, "dps": 1, "healer": 2}
#     #     ordered_heroes = sorted(
#     #         heroes,
#     #         key=lambda h: ROLE_ORDER.get((h.role or "").lower(), 99)
#     #     )

#     #     if not ordered_heroes:
#     #         return [{"id": "assistant", "text": self.lm.t("assistant_fallback_basic_report")}]

#     #     # ── Herói âncora (primeiro na ordem narrativa) ────────────────
#     #     anchor_id  = str(ordered_heroes[0].id)
#     #     party_key  = "alone" if len(ordered_heroes) == 1 else "group"
#     #     matched_perk = self._resolve_perk(ordered_heroes, context)

#     #     # ── Carrega conclusão da quest ────────────────────────────────
#     #     quest_dialogue   = self._load_quest_dialogue(quest_id)
#     #     conclusion_root  = quest_dialogue.get("conclusion", {}).get(result, {})
#     #     conclusion_texts = (
#     #         conclusion_root.get(matched_perk or "default", {}).get(self.language)
#     #         or conclusion_root.get("default", {}).get(self.language)
#     #     )

#     #     falas = []

#     #     for index, hero in enumerate(ordered_heroes):
#     #         hero_id   = str(hero.id)
#     #         hero_data = self._load_hero_dialogue(hero_id)
#     #         if not hero_data:
#     #             continue

#     #         blocks = hero_data.get("dialogue_blocks", {})
#     #         parts  = []

#     #         narrative_data = resolved_ctx.get("narrative", {})
#     #         # No novo formato, place/enemy estão dentro de um bloco 'narrative' no JSON do herói
#     #         hero_narrative = blocks.get("narrative", {})
                
#     #         # ── ARRIVED: apenas o herói âncora fala ao chegar ─────────
#     #         if hero_id == anchor_id:
#     #             arrived_texts = (
#     #                 blocks.get("arrived", {})
#     #                       .get(party_key, {})
#     #                       .get(self.language)
#     #             )
#     #             if isinstance(arrived_texts, list) and arrived_texts:
#     #                 parts.append(random.choice(arrived_texts).format(**safe_ctx))

#     #         # 1. Escolhe uma categoria de 'place' (history, feeling, landmark, details)
#     #         place_categories = ["history", "feeling", "landmark", "details"]
#     #         random.shuffle(place_categories)
#     #         for cat in place_categories:
#     #             hero_place_tpls = hero_narrative.get("place", {}).get(cat, {}).get(self.language)
#     #             fragments = narrative_data.get("place", {}).get(cat, [])
#     #             if hero_place_tpls and fragments:
#     #                 tpl = random.choice(hero_place_tpls)
#     #                 frag = random.choice(fragments)
#     #                 parts.append(tpl.replace("{fragment}", frag).format(**safe_ctx))
#     #                 break


#     #         # ── ACTION: escolhido pelo tipo da quest ──────────────────
#     #         action_texts = (
#     #             blocks.get("action", {})
#     #                   .get(quest_type, {})
#     #                   .get(party_key, {})
#     #                   .get(self.language)
#     #         )
#     #         if isinstance(action_texts, list) and action_texts:
#     #             parts.append(random.choice(action_texts).format(**safe_ctx))

#     #         # 2. Escolhe uma categoria de 'enemy' (details, attack)
#     #         enemy_categories = ["details", "attack"]
#     #         random.shuffle(enemy_categories)
#     #         for cat in enemy_categories:
#     #             hero_enemy_tpls = hero_narrative.get("enemy", {}).get(cat, {}).get(self.language)
#     #             fragments = narrative_data.get("enemy", {}).get(cat, [])
#     #             if hero_enemy_tpls and fragments:
#     #                 tpl = random.choice(hero_enemy_tpls)
#     #                 frag = random.choice(fragments)
#     #                 parts.append(tpl.replace("{fragment}", frag).format(**safe_ctx))
#     #                 break

#     #         # ── OTHERS: menção a outros heróis da party ───────────────
#     #         if len(ordered_heroes) > 1:
#     #             others_block = blocks.get("others", {})
#     #             candidates = [h for h in ordered_heroes if h.id != hero.id]
#     #             random.shuffle(candidates)

#     #             for other in candidates:
#     #                 other_texts = (
#     #                     others_block.get(str(other.id), {})
#     #                                 .get(party_key, {})
#     #                                 .get(self.language)
#     #                 )
#     #                 if isinstance(other_texts, list) and other_texts:
#     #                     text = random.choice(other_texts).replace(
#     #                         "{hero_name}", getattr(other, "name", f"hero_{other.id}")
#     #                     )
#     #                     parts.append(text.format(**safe_ctx))
#     #                     break

#     #         # ── CONCLUSION: apenas o último herói da party ────────────
#     #         if index == len(ordered_heroes) - 1:
#     #             if isinstance(conclusion_texts, list) and conclusion_texts:
#     #                 parts.append(random.choice(conclusion_texts).format(**safe_ctx))

#     #         if parts:
#     #             falas.append({"id": hero_id, "text": " ".join(parts)})

#     #     return falas or [{"id": "assistant", "text": self.lm.t("assistant_fallback_basic_report")}]

#     # ─────────────────────────────────────────────────────────────────────
#     # 🎯 DIÁLOGO INICIAL (início da quest)
#     # ─────────────────────────────────────────────────────────────────────
#     def get_start_dialogue(self, heroes: list, relation_counters: dict = None) -> list:
#         if relation_counters is None:
#             relation_counters = {}

#         falas = []

#         for hero in heroes:
#             hero_id   = str(hero.id)
#             hero_data = self._load_hero_dialogue(hero_id)
#             if not hero_data:
#                 continue

#             start_data   = hero_data.get("start_dialogues", {})
#             chosen_text  = None

#             # Prioridade 1: cadeia de relação com outro herói
#             chains = start_data.get("chains", {})
#             for other in heroes:
#                 if other.id == hero.id:
#                     continue
#                 other_key = str(other.id)
#                 if other_key not in chains:
#                     continue
#                 counter      = relation_counters.get(hero_id, {}).get(other_key, 0)
#                 lang_block   = chains[other_key].get(str(counter), {})
#                 chain_texts  = lang_block.get(self.language)
#                 if isinstance(chain_texts, list) and chain_texts:
#                     chosen_text = random.choice(chain_texts)
#                     break

#             # Prioridade 2: texto padrão
#             if not chosen_text:
#                 default_texts = start_data.get("default", {}).get(self.language)
#                 if isinstance(default_texts, list) and default_texts:
#                     chosen_text = random.choice(default_texts)

#             if chosen_text:
#                 falas.append({"id": hero_id, "text": chosen_text})

#         return falas or [{"id": "assistant", "text": self.lm.t("assistant_fallback_silent_start")}]
    
#     def _pick_from_context(self, ctx_list):
#         if isinstance(ctx_list, list) and ctx_list:
#             return random.choice(ctx_list)
#         return ""

#     def _build_dynamic_bits(self, resolved_ctx):
#         narrative = resolved_ctx.get("narrative", {})

#         enemy = narrative.get("enemy", {})
#         place = narrative.get("place", {})

#         # Obtém dados dos sujeitos/locais para concordância
#         # Note: 'enemy_data' e 'sub_loc_data' precisariam ser passados no context
#         # Se não estiverem lá, o LM usará a lógica padrão de string
#         enemy_data = resolved_ctx.get("enemy_data", {})
#         sub_loc_data = resolved_ctx.get("sub_location_data", {})

#         bits = {
#             "enemy_detail": self._pick_from_context(enemy.get("details", [])),
#             "enemy_attack": self._pick_from_context(enemy.get("attack", [])),
#             "place_detail": self._pick_from_context(place.get("details", [])),
#             "place_feeling": self._pick_from_context(place.get("feeling", [])),
#             "place_history": self._pick_from_context(place.get("history", [])),
#         }

#         # Adiciona versões com preposição se os dados estiverem disponíveis
#         if enemy_data:
#             bits["do_enemy"] = self.lm.get_with_preposition(enemy_data, "de")
#             bits["no_enemy"] = self.lm.get_with_preposition(enemy_data, "em")
#             bits["ao_enemy"] = self.lm.get_with_preposition(enemy_data, "a")
#             bits["o_enemy"] = self.lm.get_with_preposition(enemy_data, "o")
#             bits["um_enemy"] = self.lm.get_with_preposition(enemy_data, "um")
        
#         if sub_loc_data:
#             bits["da_place"] = self.lm.get_with_preposition(sub_loc_data, "de")
#             bits["na_place"] = self.lm.get_with_preposition(sub_loc_data, "em")
#             bits["a_place"] = self.lm.get_with_preposition(sub_loc_data, "a")

#         return bits

# if __name__ == "__main__":
#     import os
    
#     # Mock simples de herói
#     class MockHero:
#         def __init__(self, id, role="tank", perks=None):
#             self.id = id
#             self.name = f"Hero_{id}"
#             self.role = role
#             self.perks = perks or []
    
#     def load_quest_context(quest_id):
#         """Carrega o context automático da quest"""
#         path = os.path.join("data/quests", f"{quest_id}.json")
#         if os.path.exists(path):
#             try:
#                 with open(path, "r", encoding="utf-8") as f:
#                     data = json.load(f)
#                     return data.get("context", {})
#             except:
#                 pass
#         return {}
    
#     def quick_test():
#         dm = DialogueManager(language="pt")
        
#         print("\n" + "="*60)
#         print("🧪 TESTE RÁPIDO DE DIÁLOGOS")
#         print("="*60)
        
#         # ─────────────────────────────────────────────────
#         # 📝 INPUT DOS DADOS
#         # ─────────────────────────────────────────────────
#         print("\n📌 Digite os IDs dos heróis (separados por vírgula):")
#         print("   Exemplo: 1,2,3")
#         hero_ids = input("   IDs: ").strip()
        
#         print("\n📌 Digite o ID da quest:")
#         quest_id = input("   Quest ID: ").strip()
        
#         print("\n📌 Digite o resultado (success/failure):")
#         result = input("   Resultado: ").strip() or "success"
        
#         print("\n📌 Digite o tipo da quest (fight/thievery/diplomacy/etc):")
#         print("   (deixe vazio para auto-detectar)")
#         quest_type = input("   Tipo: ").strip()
        
#         # ─────────────────────────────────────────────────
#         # 🔧 PROCESSAMENTO
#         # ─────────────────────────────────────────────────
        
#         # Cria heróis
#         heroes = []
#         roles = ["tank", "dps", "healer"]
#         for idx, hid in enumerate(hero_ids.split(",")):
#             hid = hid.strip()
#             if hid:
#                 role = roles[idx % len(roles)]
#                 heroes.append(MockHero(hid, role))
        
#         if not heroes:
#             print("\n❌ Nenhum herói especificado!")
#             return
        
#         # Carrega context da quest automaticamente
#         context = load_quest_context(quest_id)
        
#         # Auto-detecta tipo se não especificado
#         if not quest_type:
#             quest_path = os.path.join("data/quests", f"{quest_id}.json")
#             try:
#                 with open(quest_path, "r", encoding="utf-8") as f:
#                     quest_data = json.load(f)
#                     quest_type = quest_data.get("type", "fight")
#                     if isinstance(quest_type, list):
#                         quest_type = quest_type[0]
#             except:
#                 quest_type = "fight"
        
#         # ─────────────────────────────────────────────────
#         # ✨ EXECUTA O TESTE
#         # ─────────────────────────────────────────────────
#         print("\n" + "="*60)
#         print("📤 EXECUTANDO...")
#         print("="*60)
#         print(f"Heróis: {[h.id for h in heroes]}")
#         print(f"Quest: {quest_id}")
#         print(f"Tipo: {quest_type}")
#         print(f"Resultado: {result}")
#         print(f"Context: {bool(context)}")
        
#         try:
#             falas = dm.show_quest_dialogue(
#                 heroes=heroes,
#                 quest_id=quest_id,
#                 result=result,
#                 quest_type=quest_type,
#                 context=context
#             )
            
#             print("\n" + "="*60)
#             print("📝 RESULTADO:")
#             print("="*60)
            
#             for fala in falas:
#                 print(f"\n[Hero {fala['id']}]")
#                 print(f"{fala['text']}")
            
#             print("\n" + "="*60)
            
#         except Exception as e:
#             print(f"\n❌ ERRO: {e}")
#             import traceback
#             traceback.print_exc()
    
#     # ═══════════════════════════════════════════════════
#     # LOOP PRINCIPAL
#     # ═══════════════════════════════════════════════════
#     while True:
#         try:
#             quick_test()
            
#             print("\n")
#             continuar = input("Testar novamente? (s/n): ").strip().lower()
#             if continuar != 's':
#                 print("\n👋 Saindo...")
#                 break
                
#         except KeyboardInterrupt:
#             print("\n\n👋 Saindo...")
#             break
#         except Exception as e:
#             print(f"\n❌ Erro inesperado: {e}")
#             import traceback
#             traceback.print_exc()
#             break

# core/dialogue_manager.py
import json
import random
import os
from core.language_manager import LanguageManager
import re

class SafeDict(dict):
    """
    Dicionário que retorna a própria chave se ela não for encontrada,
    evitando KeyError no .format().

    Também funciona como a CAMADA FINAL de detecção de tags desconhecidas:
    o linter estático em _lint_dialogue_dict não consegue distinguir
    {enemy_attack} (categoria real do JSON da quest) de {enemy_color}
    (erro de digitação) porque categorias de subject/enemy são dinâmicas
    por design. Mas em runtime, quando o .format() de fato roda, SE a
    chave não está no dict resolvido, é garantidamente porque ninguém
    a gerou — então avisamos aqui, uma vez por chave por sessão.
    """
    _warned_keys = set()   # nível de classe: compartilhado entre instâncias da mesma run

    def __missing__(self, key):
        if key not in SafeDict._warned_keys:
            print(
                f"[DialogueManager][WARNING] Tag '{{{key}}}' não encontrada no "
                f"contexto resolvido — provavelmente erro de digitação no JSON "
                f"de diálogo, ou categoria que essa quest específica não gerou. "
                f"Aparecerá literal '{{{key}}}' no texto exibido ao jogador."
            )
            SafeDict._warned_keys.add(key)
        return f"{{{key}}}"


# ════════════════════════════════════════════════════════════════
# LINTER DE TAGS GRAMATICAIS PT/ES
# ════════════════════════════════════════════════════════════════
# Essas tags só fazem sentido em idiomas com contração preposição+
# artigo (PT: "do"=de+o, "ao"=a+o, "na"=em+a; ES similar). Em idiomas
# sem contração (EN/RU/JA/ZH) o template deve usar {subject}/{place}
# puro e escrever a frase completa — ver aviso em _build_dynamic_bits.
GRAMMATICAL_TAGS = {
    "do_subject", "no_subject", "ao_subject", "o_subject", "um_subject",
    "do_enemy",   "no_enemy",   "ao_enemy",   "o_enemy",   "um_enemy",
    "da_place",   "na_place",   "a_place",    "ao_place",
}
NO_CONTRACTION_LANGS = {"en", "ru", "ja", "zh"}
ALL_DIALOGUE_LANGS = NO_CONTRACTION_LANGS | {"pt", "es"}

# ════════════════════════════════════════════════════════════════
# LINTER DE TAGS "enemy" FORA DE CONTEXTO DE COMBATE
# ════════════════════════════════════════════════════════════════
# {enemy}/{enemy_detail}/{enemy_attack}/{do_enemy}... só fazem sentido
# semântico em quests de "fight" (a ÚNICA categoria que de fato tem um
# inimigo). Em "stealth", "escort", "investigation", "diplomacy",
# "gathering" etc. o termo correto é sempre {subject} — usar {enemy}
# nesses tipos costuma ser cópia-e-cola de um template de fight sem
# adaptar, e o "subject" continua funcionando por baixo (alias), então
# o erro passa despercebido até alguém ler o texto gerado em jogo.
#
# Tipos de quest sem allow-list aqui (ex: tipos custom futuros) não são
# checados — só avisamos para os tipos conhecidos abaixo.
ENEMY_TAG_ALLOWED_TYPES = {"fight"}
_ENEMY_TAG_PATTERN = re.compile(r"\benemy\w*\b")

# ════════════════════════════════════════════════════════════════
# LINTER DE TAGS DESCONHECIDAS
# ════════════════════════════════════════════════════════════════
# Qualquer {tag} usada num template que o DialogueManager nunca vai
# preencher passa direto pelo SafeDict e aparece literalmente na tela
# do jogador (ex: "Vi {enemy_color} se aproximando."). Como as
# categorias de subject/enemy são dinâmicas (vêm do JSON da quest,
# não são fixas em código), validamos por uma combinação de:
#   a) chaves literais sempre geradas (KNOWN_LITERAL_TAGS)
#   b) prefixos dinâmicos conhecidos (KNOWN_DYNAMIC_PREFIXES) — cobre
#      subject_<categoria>/enemy_<categoria> sem precisar listar toda
#      categoria de antemão
# Isso é uma rede de segurança "best effort": ela não conhece as
# categorias exatas que cada quest JSON vai gerar, mas pega o erro
# mais comum, que é digitar uma palavra que não existe em NENHUM
# padrão conhecido (ex: enemy_color, place_landmark_typo).
KNOWN_LITERAL_TAGS = {
    # genéricos sempre presentes
    "subject", "enemy", "place", "location", "fragment", "hero_name",
    # place — fixos, sempre os mesmos
    "place_detail", "place_feeling", "place_history",
    "da_place", "na_place", "a_place", "ao_place",
    # subject/enemy — preposições fixas (PT/ES)
    "do_subject", "no_subject", "ao_subject", "o_subject", "um_subject",
    "do_enemy",   "no_enemy",   "ao_enemy",   "o_enemy",   "um_enemy",
}
KNOWN_DYNAMIC_PREFIXES = (
    "subject_",   # subject_detail, subject_attack, subject_behavior, subject_<qualquer categoria do JSON>
    "enemy_",     # alias retrocompatível dos mesmos
)


def _is_known_tag(tag: str) -> bool:
    if tag in KNOWN_LITERAL_TAGS:
        return True
    return any(tag.startswith(prefix) for prefix in KNOWN_DYNAMIC_PREFIXES)


_TAG_PATTERN = re.compile(r"\{([^{}]+)\}")


def _lint_dialogue_dict(data, source_label, _path="", _quest_type=None):
    """
    Varre recursivamente um dict de diálogo carregado do JSON aplicando
    duas regras:

    1) tags PT/ES (ex: {ao_enemy}) dentro de listas de texto de idiomas
       sem contração (en/ru/ja/zh) — sempre errado, em qualquer quest_type.

    2) tags {enemy*} dentro de blocos de quest_type que não seja "fight"
       (ex: dialogue_blocks.action.escort.*) — provável cópia indevida
       de template de combate, deveria usar {subject*}.

    Roda só uma vez por arquivo (no load), nunca em runtime por fala —
    custo desprezível, pega erro de conteúdo antes de aparecer em jogo.

    _quest_type rastreia em qual chave de "action" estamos, para a
    regra 2 — ex: dialogue_blocks.action.escort.alone.en → quest_type="escort"
    """
    if isinstance(data, dict):
        for key, value in data.items():
            new_path = f"{_path}.{key}" if _path else key

            # detecta entrada em dialogue_blocks.action.<quest_type>
            next_quest_type = _quest_type
            if _path.endswith("dialogue_blocks.action") or _path == "action":
                next_quest_type = key

            if key in ALL_DIALOGUE_LANGS and isinstance(value, list):
                for text in value:
                    if not isinstance(text, str):
                        continue

                    # regra 1: tag PT/ES em idioma sem contração
                    if key in NO_CONTRACTION_LANGS:
                        for tag in _TAG_PATTERN.findall(text):
                            if tag in GRAMMATICAL_TAGS:
                                print(
                                    f"[DialogueManager][WARNING] Tag gramatical PT/ES "
                                    f"'{{{tag}}}' usada em idioma '{key}' "
                                    f"({source_label} → {new_path}): {text!r}"
                                )

                    # regra 2: {enemy*} fora de quest_type=fight
                    if (_quest_type and _quest_type not in ENEMY_TAG_ALLOWED_TYPES
                            and _ENEMY_TAG_PATTERN.search(text)):
                        print(
                            f"[DialogueManager][WARNING] Tag '{{enemy*}}' usada em "
                            f"quest_type='{_quest_type}' (não é fight) — prefira "
                            f"'{{subject*}}'. ({source_label} → {new_path}): {text!r}"
                        )

                    # regra 3: tag desconhecida — provavelmente nunca será
                    # preenchida pelo DialogueManager e vai vazar literal
                    # pro jogador (ex: {enemy_color}, {place_landmark_typo})
                    for tag in _TAG_PATTERN.findall(text):
                        # {fragment(categoria)} não é tag de .format(), é
                        # resolvida manualmente por regex antes — ignora aqui
                        if tag.startswith("fragment(") and tag.endswith(")"):
                            continue
                        if not _is_known_tag(tag):
                            print(
                                f"[DialogueManager][WARNING] Tag desconhecida "
                                f"'{{{tag}}}' — não será preenchida pelo "
                                f"DialogueManager e pode vazar literal no jogo. "
                                f"({source_label} → {new_path}): {text!r}"
                            )
            else:
                _lint_dialogue_dict(value, source_label, new_path, next_quest_type)
    elif isinstance(data, list):
        for item in data:
            _lint_dialogue_dict(item, source_label, _path, _quest_type)


class DialogueManager:
    def __init__(self, language="en"):
        self.language = language
        self.lm = LanguageManager()
        self.heroes_folder = "data/heroes/dialogues"
        self._linted_files = set()   # cache: arquivos já validados nesta sessão

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
                data = json.load(f)
            if path not in self._linted_files:
                _lint_dialogue_dict(data, source_label=f"quest:{quest_id}")
                self._linted_files.add(path)
            return data
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
                data = json.load(f)
            # lint só roda uma vez por arquivo por sessão — custo desprezível
            if path not in self._linted_files:
                _lint_dialogue_dict(data, source_label=f"hero:{hero_id}")
                self._linted_files.add(path)
            return data
        except Exception as e:
            print(f"[DialogueManager] Erro ao carregar {path}: {e}")
            return {}

    def _resolve_context(self, context):
        if isinstance(context, dict):
            # rede de segurança: se o dict for um bloco de idiomas cru
            # (ex: {"pt": "...", "en": "...", ...}), já resolve pro idioma atual
            lang_keys = {"pt", "en", "es", "ru", "zh", "ja"}
            if context and set(context.keys()).issubset(lang_keys):
                return context.get(self.language) or context.get("en") or ""

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
    def show_quest_dialogue(self, heroes, quest_id, result, quest_type="fight", context=None) -> list:

        quest_id   = str(quest_id)
        result     = result.lower()
        quest_type = (quest_type[0] if isinstance(quest_type, list) else quest_type or "fight").lower()
        context    = context or {}

        resolved_ctx = self._resolve_context(context)
        dynamic_bits = self._build_dynamic_bits(resolved_ctx)
        resolved_ctx.update(dynamic_bits)
        self._fill_grammatical_keys(resolved_ctx)   # extrai método auxiliar (ver abaixo)
        safe_ctx = SafeDict(resolved_ctx)

        # ── FAILURE → caminho curto ───────────────────────────────────────
        if result == "failure":
            return self._build_failure_dialogue(heroes, quest_id, safe_ctx)

        # ── SUCCESS → caminho completo existente ──────────────────────────
        return self._build_success_dialogue(heroes, quest_id, quest_type, safe_ctx, resolved_ctx)

    def _fill_grammatical_keys(self, resolved_ctx):
        """
        Garante que todas as chaves gramaticais existam no contexto.

        'subject' é o termo genérico do elemento central da quest —
        funciona para fight (enemy), stealth (challenge), thievery
        (target_item), diplomacy (faction), etc. 'enemy' é mantido
        como alias de 'subject' só para não quebrar quests de fight
        já escritas; novo conteúdo deve usar 'subject' diretamente.
        """
        # unifica subject/enemy: o que existir vira a fonte da verdade
        if "subject" not in resolved_ctx and "enemy" in resolved_ctx:
            resolved_ctx["subject"] = resolved_ctx["enemy"]
        if "enemy" not in resolved_ctx and "subject" in resolved_ctx:
            resolved_ctx["enemy"] = resolved_ctx["subject"]

        grammatical_keys = [
            "do_subject", "no_subject", "ao_subject", "o_subject", "um_subject",
            "do_enemy", "no_enemy", "ao_enemy", "o_enemy", "um_enemy",
            "da_place", "na_place", "a_place", "ao_place", "place",
            "subject", "enemy", "location"
        ]
        for k in grammatical_keys:
            if k not in resolved_ctx:
                if k in ("subject", "enemy"):
                    fallback = resolved_ctx.get("subject_type") or resolved_ctx.get("enemy_type")
                    resolved_ctx[k] = fallback or self.lm.t("enemy_fallback")
                elif k in ("location", "place"):
                    resolved_ctx[k] = resolved_ctx.get("location_key") or self.lm.t("location_fallback")
                else:
                    if "subject" in k:
                        base = "subject"
                    elif "enemy" in k:
                        base = "enemy"
                    else:
                        base = "place"
                    resolved_ctx[k] = resolved_ctx.get(base, "")

    def _build_failure_dialogue(self, heroes, quest_id, safe_ctx) -> list:
        """
        Gera o diálogo de falha adaptando o texto se o herói estava em uma 
        missão Solo ou em Grupo, tratando corretamente as tags gramaticais.
        """
        ROLE_ORDER = {"tank": 0, "dps": 1, "healer": 2}
        ordered_heroes = sorted(heroes, key=lambda h: ROLE_ORDER.get((h.role or "").lower(), 99))
        
        if not ordered_heroes:
            return [{"id": "assistant", "text": self.lm.t("failure_fallback")}]

        # Determina a modalidade da equipe
        is_solo = len(heroes) == 1
        failure_mode = "solo" if is_solo else "group"

        # Limpa o safe_ctx de possíveis dicionários de localização/idiomas remanescentes
        cleaned_ctx = {}
        for k, v in safe_ctx.items():
            if isinstance(v, dict):
                if self.language in v:
                    cleaned_ctx[k] = v[self.language]
                elif "pt" in v:
                    cleaned_ctx[k] = v["pt"]
                else:
                    cleaned_ctx[k] = str(v)
            else:
                cleaned_ctx[k] = v
        safe_ctx.update(cleaned_ctx)

        # Seleciona o herói âncora do diálogo
        anchor = ordered_heroes[0]
        hero_id = str(anchor.id)
        hero_data = self._load_hero_dialogue(hero_id)
        
        if hero_data:
            failure_root = hero_data.get("dialogue_blocks", {}).get("failure", {})
            
            # 1. Tenta buscar a lista de textos baseado no modo (solo ou group)
            failure_texts = failure_root.get(failure_mode, {}).get(self.language)
            
            # 2. FALLBACK: Se não achar a nova estrutura estruturada, busca o formato antigo
            if not failure_texts and isinstance(failure_root.get(self.language), list):
                failure_texts = failure_root.get(self.language)
                print(f"[DialogueManager] Usando fallback antigo de falha para o herói {hero_id}")

            # Se encontrou falas válidas, renderiza uma aleatória
            if isinstance(failure_texts, list) and failure_texts:
                raw = random.choice(failure_texts)
                text = raw.format_map(safe_ctx)
                return [{"id": hero_id, "text": text}]

        return [{"id": hero_id, "text": self.lm.t("failure_fallback")}]

    def _build_success_dialogue(self, heroes, quest_id, quest_type, safe_ctx, resolved_ctx) -> list:
        ROLE_ORDER = {"tank": 0, "dps": 1, "healer": 2}
        ordered_heroes = sorted(heroes, key=lambda h: ROLE_ORDER.get((h.role or "").lower(), 99))

        if not ordered_heroes:
            return [{"id": "assistant", "text": self.lm.t("assistant_fallback_basic_report")}]

        anchor_id = str(ordered_heroes[0].id)
        party_key = "alone" if len(ordered_heroes) == 1 else "group"
        matched_perk = self._resolve_perk(ordered_heroes, resolved_ctx)

        quest_dialogue = self._load_quest_dialogue(quest_id)
        conclusion_root = quest_dialogue.get("conclusion", {}).get("success", {})
        conclusion_texts = (
            conclusion_root.get(matched_perk or "default", {}).get(self.language)
            or conclusion_root.get("default", {}).get(self.language)
        )

        falas = []
        narrative_data = resolved_ctx.get("narrative", {})

        for index, hero in enumerate(ordered_heroes):
            hero_id = str(hero.id)
            hero_data = self._load_hero_dialogue(hero_id)
            if not hero_data: continue

            blocks = hero_data.get("dialogue_blocks", {})
            hero_narrative = blocks.get("narrative", {})
            parts = []

            # ── ARRIVED (Anchor only)
            if hero_id == anchor_id:
                arrived_texts = blocks.get("arrived", {}).get(party_key, {}).get(self.language)
                if isinstance(arrived_texts, list) and arrived_texts:
                    parts.append(random.choice(arrived_texts).format_map(safe_ctx))

                # ── START_SUBJECT (reação à categoria do subject, anchor only)
                # Dá personalidade sem precisar escrever diálogo por quest —
                # uma reação genérica por categoria ("slime", "undead",
                # "humanoid"...) cobre toda quest procedural daquela categoria.
                subject_category = resolved_ctx.get("subject_category") or resolved_ctx.get("enemy_category")
                if subject_category:
                    start_subject_texts = (
                        blocks.get("start_subject", {})
                              .get(subject_category, {})
                              .get(self.language)
                    )
                    if isinstance(start_subject_texts, list) and start_subject_texts:
                        parts.append(random.choice(start_subject_texts).format_map(safe_ctx))

            # ── PLACE NARRATIVE
            place_categories = ["history", "feeling", "landmark", "details"]
            random.shuffle(place_categories)
            for cat in place_categories:
                hero_place_tpls = hero_narrative.get("place", {}).get(cat, {}).get(self.language)
                fragments = narrative_data.get("place", {}).get(cat, [])
                if hero_place_tpls and fragments:
                    tpl = random.choice(hero_place_tpls)
                    frag = random.choice(fragments)
                    parts.append(tpl.replace("{fragment}", frag).format_map(safe_ctx))
                    break

            # ── ACTION
            action_texts = blocks.get("action", {}).get(quest_type, {}).get(party_key, {}).get(self.language)
            if isinstance(action_texts, list) and action_texts:
                parts.append(random.choice(action_texts).format_map(safe_ctx))

            # ── SUBJECT NARRATIVE ──────────────────────────────────
            # 'subject' é o termo genérico (enemy em fight, challenge em
            # stealth, target_item em thievery, faction em diplomacy...).
            # Não assumimos categorias fixas como antes ("details", "attack")
            # porque nem todo subject tem "attack" — descobrimos quais
            # categorias o JSON do herói E o contexto da quest têm em comum.
            hero_subject_block = hero_narrative.get("subject") or hero_narrative.get("enemy", {})
            ctx_subject_block  = narrative_data.get("subject") or narrative_data.get("enemy", {})

            available_categories = [
                cat for cat, fragments in ctx_subject_block.items()
                if fragments and hero_subject_block.get(cat, {}).get(self.language)
            ]
            random.shuffle(available_categories)

            for cat in available_categories:
                hero_tpls = hero_subject_block.get(cat, {}).get(self.language)
                fragments = ctx_subject_block.get(cat, [])
                if hero_tpls and fragments:
                    tpl  = random.choice(hero_tpls)
                    frag = random.choice(fragments)
                    parts.append(tpl.replace("{fragment}", frag).format_map(safe_ctx))
                    break

            # ── OTHERS (Interaction)
            if len(ordered_heroes) > 1:
                others_block = blocks.get("others", {})
                candidates = [h for h in ordered_heroes if h.id != hero.id]
                random.shuffle(candidates)
                for other in candidates:
                    other_texts = others_block.get(str(other.id), {}).get(party_key, {}).get(self.language)
                    if isinstance(other_texts, list) and other_texts:
                        text = random.choice(other_texts).replace("{hero_name}", getattr(other, "name", f"hero_{other.id}"))
                        parts.append(text.format_map(safe_ctx))
                        break

            # ── CONCLUSION (Last hero only)
            if index == len(ordered_heroes) - 1:
                if isinstance(conclusion_texts, list) and conclusion_texts:
                    parts.append(random.choice(conclusion_texts).format_map(safe_ctx))

            if parts:
                falas.append({"id": hero_id, "text": " ".join(parts)})

        return falas or [{"id": "assistant", "text": self.lm.t("assistant_fallback_basic_report")}]

    # def show_quest_dialogue(
    #     self,
    #     heroes: list,
    #     quest_id: str,
    #     result: str,
    #     quest_type: str = "fight",
    #     context: dict | None = None
    # ) -> list:

    #     quest_id  = str(quest_id)
    #     result    = result.lower()

    #     if isinstance(quest_type, list):
    #         quest_type = quest_type[0] if quest_type else "fight"
    #     quest_type = quest_type.lower()

    #     if context is None:
    #         context = {}

    #     resolved_ctx = self._resolve_context(context)

    #     # Injeta bits dinâmicos (enemy_detail, place_detail, etc) para uso no .format()
    #     dynamic_bits = self._build_dynamic_bits(resolved_ctx)
    #     resolved_ctx.update(dynamic_bits)
        
    #     # Garante que todas as chaves gramaticais existam para evitar KeyError
    #     # Adicionada a chave 'place' que estava faltando e causando erro
    #     grammatical_keys = [
    #         "do_enemy", "no_enemy", "ao_enemy", "o_enemy", "um_enemy",
    #         "da_place", "na_place", "a_place", "ao_place", "place",
    #         "enemy", "location"
    #     ]
    #     for k in grammatical_keys:
    #         if k not in resolved_ctx:
    #             # Tenta fallback para chaves básicas
    #             if k == "enemy": 
    #                 resolved_ctx[k] = resolved_ctx.get("enemy_type") or (self.lm.t("enemy_fallback") if hasattr(self.lm, 't') else "enemy")
    #             elif k in ["location", "place"]: 
    #                 resolved_ctx[k] = resolved_ctx.get("location_key") or (self.lm.t("location_fallback") if hasattr(self.lm, 't') else "location")
    #             else: 
    #                 # Para chaves gramaticais (preposições), se não for PT/ES, o fallback deve ser a própria palavra ou vazio
    #                 base_key = "enemy" if "enemy" in k else "place"
    #                 resolved_ctx[k] = resolved_ctx.get(base_key, "")

    #     # Converte para SafeDict para proteção extra contra chaves inesperadas
    #     safe_ctx = SafeDict(resolved_ctx)

    #     # ── Ordenação narrativa: tank → dps → healer ──────────────────
    #     ROLE_ORDER = {"tank": 0, "dps": 1, "healer": 2}
    #     ordered_heroes = sorted(
    #         heroes,
    #         key=lambda h: ROLE_ORDER.get((h.role or "").lower(), 99)
    #     )

    #     if not ordered_heroes:
    #         return [{"id": "assistant", "text": self.lm.t("assistant_fallback_basic_report")}]

    #     # ── Herói âncora (primeiro na ordem narrativa) ────────────────
    #     anchor_id  = str(ordered_heroes[0].id)
    #     party_key  = "alone" if len(ordered_heroes) == 1 else "group"
    #     matched_perk = self._resolve_perk(ordered_heroes, context)

    #     # ── Carrega conclusão da quest ────────────────────────────────
    #     quest_dialogue   = self._load_quest_dialogue(quest_id)
    #     conclusion_root  = quest_dialogue.get("conclusion", {}).get(result, {})
    #     conclusion_texts = (
    #         conclusion_root.get(matched_perk or "default", {}).get(self.language)
    #         or conclusion_root.get("default", {}).get(self.language)
    #     )

    #     falas = []

    #     for index, hero in enumerate(ordered_heroes):
    #         hero_id   = str(hero.id)
    #         hero_data = self._load_hero_dialogue(hero_id)
    #         if not hero_data:
    #             continue

    #         blocks = hero_data.get("dialogue_blocks", {})
    #         parts  = []

    #         narrative_data = resolved_ctx.get("narrative", {})
    #         # No novo formato, place/enemy estão dentro de um bloco 'narrative' no JSON do herói
    #         hero_narrative = blocks.get("narrative", {})
                
    #         # ── ARRIVED: apenas o herói âncora fala ao chegar ─────────
    #         if hero_id == anchor_id:
    #             arrived_texts = (
    #                 blocks.get("arrived", {})
    #                       .get(party_key, {})
    #                       .get(self.language)
    #             )
    #             if isinstance(arrived_texts, list) and arrived_texts:
    #                 parts.append(random.choice(arrived_texts).format_map(safe_ctx))

    #         # 1. Escolhe uma categoria de 'place' (history, feeling, landmark, details)
    #         place_categories = ["history", "feeling", "landmark", "details"]
    #         random.shuffle(place_categories)
    #         for cat in place_categories:
    #             hero_place_tpls = hero_narrative.get("place", {}).get(cat, {}).get(self.language)
    #             fragments = narrative_data.get("place", {}).get(cat, [])
    #             if hero_place_tpls and fragments:
    #                 tpl = random.choice(hero_place_tpls)
    #                 frag = random.choice(fragments)
    #                 parts.append(tpl.replace("{fragment}", frag).format_map(safe_ctx))
    #                 break


    #         # ── ACTION: escolhido pelo tipo da quest ──────────────────
    #         action_texts = (
    #             blocks.get("action", {})
    #                   .get(quest_type, {})
    #                   .get(party_key, {})
    #                   .get(self.language)
    #         )
    #         if isinstance(action_texts, list) and action_texts:
    #             parts.append(random.choice(action_texts).format_map(safe_ctx))

    #         # 2. Escolhe uma categoria de 'enemy' (details, attack)
    #         enemy_categories = ["details", "attack"]
    #         random.shuffle(enemy_categories)
    #         for cat in enemy_categories:
    #             hero_enemy_tpls = hero_narrative.get("enemy", {}).get(cat, {}).get(self.language)
    #             fragments = narrative_data.get("enemy", {}).get(cat, [])
    #             if hero_enemy_tpls and fragments:
    #                 tpl = random.choice(hero_enemy_tpls)
    #                 frag = random.choice(fragments)
    #                 parts.append(tpl.replace("{fragment}", frag).format_map(safe_ctx))
    #                 break

    #         # ── OTHERS: menção a outros heróis da party ───────────────
    #         if len(ordered_heroes) > 1:
    #             others_block = blocks.get("others", {})
    #             candidates = [h for h in ordered_heroes if h.id != hero.id]
    #             random.shuffle(candidates)

    #             for other in candidates:
    #                 other_texts = (
    #                     others_block.get(str(other.id), {})
    #                                 .get(party_key, {})
    #                                 .get(self.language)
    #                 )
    #                 if isinstance(other_texts, list) and other_texts:
    #                     text = random.choice(other_texts).replace(
    #                         "{hero_name}", getattr(other, "name", f"hero_{other.id}")
    #                     )
    #                     parts.append(text.format_map(safe_ctx))
    #                     break

    #         # ── CONCLUSION: apenas o último herói da party ────────────
    #         if index == len(ordered_heroes) - 1:
    #             if isinstance(conclusion_texts, list) and conclusion_texts:
    #                 parts.append(random.choice(conclusion_texts).format_map(safe_ctx))

    #         if parts:
    #             falas.append({"id": hero_id, "text": " ".join(parts)})

    #     return falas or [{"id": "assistant", "text": self.lm.t("assistant_fallback_basic_report")}]

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
        """
        ⚠️ AVISO DE SEGURANÇA LINGUÍSTICA ⚠️
        Os bits com prefixo gramatical ({do_subject}, {ao_subject},
        {no_subject}, {da_place}, {na_place}...) só existem por causa de
        contrações de preposição+artigo do PT/ES ("do" = de+o, "ao" = a+o).

        Eles são gerados para TODOS os idiomas (não custa nada gerar),
        mas só devem aparecer em templates PT/ES. Em EN/RU/JA/ZH não
        existe contração equivalente — get_with_preposition() não tem
        como "traduzir" {ao_subject} de forma natural, então o valor
        cai de volta pra string crua tipo "to the goblin" ou pior,
        vaza a preposição PT junto. Templates EN/RU/JA/ZH devem usar
        {subject} puro e escrever a frase completa:

            PT: "Ataquei {o_subject}."
            EN: "I attacked the {subject}."   ← NUNCA "{ao_subject}"

        Isso não é validado em runtime de propósito (custo > benefício
        por enquanto); revisar manualmente ao escrever JSON de heróis
        em idiomas sem contração.
        """
        narrative = resolved_ctx.get("narrative", {})

        # 'subject' é o bloco genérico; 'enemy' é o nome legado usado
        # pelas quests de fight já escritas — aceitamos os dois.
        subject = narrative.get("subject") or narrative.get("enemy", {})
        place   = narrative.get("place", {})

        subject_data = (resolved_ctx.get("subject_data")
                         or resolved_ctx.get("enemy_data", {}))
        sub_loc_data = resolved_ctx.get("sub_location_data", {})

        bits = {}

        # gera um bit por categoria existente, sem assumir "details"/"attack"
        # fixos — um target_item pode ter só "details", um faction pode ter
        # "details"+"mood", um enemy de fight pode ter "details"+"attack"
        for cat, fragments in subject.items():
            value = self._pick_from_context(fragments)
            bits[f"subject_{cat}"] = value
            bits[f"enemy_{cat}"]   = value   # alias retrocompatível

        bits["place_detail"]  = self._pick_from_context(place.get("details", []))
        bits["place_feeling"] = self._pick_from_context(place.get("feeling", []))
        bits["place_history"] = self._pick_from_context(place.get("history", []))

        # Adiciona versões com preposição se os dados estiverem disponíveis
        if subject_data:
            for prep, prefix in [("de", "do"), ("em", "no"), ("a", "ao"), ("o", "o"), ("um", "um")]:
                val = self.lm.get_with_preposition(subject_data, prep)
                bits[f"{prefix}_subject"] = val
                bits[f"{prefix}_enemy"]   = val   # alias retrocompatível

        if sub_loc_data:
            bits["da_place"] = self.lm.get_with_preposition(sub_loc_data, "de")
            bits["na_place"] = self.lm.get_with_preposition(sub_loc_data, "em")
            bits["a_place"]  = self.lm.get_with_preposition(sub_loc_data, "a")

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

        print("\n" + "=" * 60)
        print("🧪 TESTE RÁPIDO")
        print("=" * 60)
        print("Formato:")
        print("heroes quest_id [success|failure] [tipo]")
        print("Ex:")
        print("1,2,3 001 success fight")
        print("1 132 failure")
        print("1,2 045")
        print()

        cmd = input("> ").strip()

        if not cmd:
            return

        parts = cmd.split()

        hero_ids = parts[0]

        if len(parts) >= 2:
            quest_id = parts[1]
        else:
            print("❌ Quest ID obrigatório")
            return

        result = parts[2] if len(parts) >= 3 else "success"
        quest_type = parts[3] if len(parts) >= 4 else ""

        heroes = []
        roles = ["tank", "dps", "healer"]

        for idx, hid in enumerate(hero_ids.split(",")):
            hid = hid.strip()
            if hid:
                heroes.append(
                    MockHero(
                        hid,
                        roles[idx % len(roles)]
                    )
                )

        if not heroes:
            print("❌ Nenhum herói informado")
            return

        context = load_quest_context(quest_id)

        if not quest_type:
            try:
                path = os.path.join(
                    "data/quests",
                    f"{quest_id}.json"
                )

                with open(path, "r", encoding="utf-8") as f:
                    quest_data = json.load(f)

                quest_type = quest_data.get("type", "fight")

                if isinstance(quest_type, list):
                    quest_type = quest_type[0]

            except Exception:
                quest_type = "fight"

        falas = dm.show_quest_dialogue(
            heroes=heroes,
            quest_id=quest_id,
            result=result,
            quest_type=quest_type,
            context=context
        )

        print("\n" + "=" * 60)

        for fala in falas:
            print(f"\n[{fala['id']}]")
            print(fala["text"])

        print("\n" + "=" * 60)

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