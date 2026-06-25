# ════════════════════════════════════════════════════════════════
# 💾 SAVE_MANAGER.PY - COM SUPORTE A QUESTS PROCEDURAIS
# ════════════════════════════════════════════════════════════════

import json
import os

SAVE_DIR = "saves"

def save_game(manager, filename):
    os.makedirs(SAVE_DIR, exist_ok=True)
    path = os.path.join(SAVE_DIR, filename)
    
    # ════════════════════════════════════════════════════════════
    # QUESTS ATIVAS (handcrafted + procedural)
    # ════════════════════════════════════════════════════════════
    active_quests_save = {}
    for qid, qdata in manager.active_quests.items():
        key = str(qid)
        active_quests_save[key] = {
            "turns_left": int(qdata.get("turns_left", 0)),
            "heroes": [h.id for h in qdata.get("heroes", [])],
        }
    
    # ════════════════════════════════════════════════════════════
    # QUESTS COMPLETADAS
    # ════════════════════════════════════════════════════════════
    completed_quests_save = {
        str(qid): list(hids)
        for qid, hids in getattr(manager, "completed_quests", {}).items()
    }
    
    # ════════════════════════════════════════════════════════════
    # QUESTS AVAILABILITY
    # ════════════════════════════════════════════════════════════
    quests_availability = {
        str(q.id): getattr(q, "available_since_turn", None)
        for q in manager.quest_registry.values()
        if getattr(q, "available_since_turn", None) is not None
    }
    
    # ════════════════════════════════════════════════════════════
    # DADOS COMPLETOS
    # ════════════════════════════════════════════════════════════
    data = {
        "current_turn": int(getattr(manager, "current_turn", 0)),
        "completed_quests": completed_quests_save,
        "failed_quests": list(manager.failed_quests),
        "unlocked_heroes": list(manager.hero_manager.unlocked_heroes),
        "heroes": [
            {
                "id": h.id,
                "xp": getattr(h, "xp", 0),
                "status": getattr(h, "status", "idle"),
            }
            for h in manager.hero_manager.all_heroes
        ],
        "active_quests": active_quests_save,
        "quests_availability": quests_availability,
        
    }
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    print(f"💾 Jogo salvo em: {path}")
    

def load_game(manager, filename):
    path = os.path.join(SAVE_DIR, filename)
    
    if not os.path.exists(path):
        print(f"⚠️  Save '{filename}' não encontrado.")
        return False
    
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    manager.current_turn = data.get("current_turn", getattr(manager, "current_turn", 1))

    def _to_int_if_possible(x):
        try:
            return int(x)
        except Exception:
            return x
    
    # ════════════════════════════════════════════════════════════
    # QUESTS COMPLETADAS
    # ════════════════════════════════════════════════════════════
    raw_completed = data.get("completed_quests", {})
    manager.completed_quests = {
        _to_int_if_possible(qid): set(_to_int_if_possible(h) for h in hlist)
        for qid, hlist in raw_completed.items()
    }
    
    # ════════════════════════════════════════════════════════════
    # QUESTS FALHADAS
    # ════════════════════════════════════════════════════════════
    manager.failed_quests = set(_to_int_if_possible(x) for x in data.get("failed_quests", []))
    
    # ════════════════════════════════════════════════════════════
    # HERÓIS
    # ════════════════════════════════════════════════════════════
    manager.hero_manager.unlocked_heroes = set(_to_int_if_possible(x) for x in data.get("unlocked_heroes", []))
    
    for hero_data in data.get("heroes", []):
        hid = _to_int_if_possible(hero_data.get("id"))
        hero = manager.hero_manager.get_hero_by_id(hid)
        if hero:
            hero.xp = hero_data.get("xp", getattr(hero, "xp", 0))
            hero.status = hero_data.get("status", getattr(hero, "status", "idle"))
    
    # ════════════════════════════════════════════════════════════
    # QUESTS ATIVAS (handcrafted)
    # ════════════════════════════════════════════════════════════
    manager.active_quests = {}
    for qid_key, qdata in data.get("active_quests", {}).items():
        try:
            qid = int(qid_key)
        except Exception:
            qid = qid_key
        
        quest = manager.get_quest(qid)
        if quest is None:
            print(f"⚠️  Quest '{qid}' não existe - pulando")
            continue
        
        heroes_list = []
        for hid in qdata.get("heroes", []):
            hid_conv = _to_int_if_possible(hid)
            hero_obj = manager.hero_manager.get_hero_by_id(hid_conv)
            if hero_obj:
                heroes_list.append(hero_obj)
                hero_obj.status = "on_mission"
        
        manager.active_quests[qid] = {
            "turns_left": int(qdata.get("turns_left", quest.duration)),
            "heroes": heroes_list,
        }
    
    # ════════════════════════════════════════════════════════════
    # QUESTS AVAILABILITY
    # ════════════════════════════════════════════════════════════
    quests_data = data.get("quests_availability") or data.get("quests", {})
    
    for qid_key, turn_value in quests_data.items():
        try:
            qid = int(qid_key)
        except Exception:
            qid = qid_key
        
        quest = manager.get_quest(qid)

        if quest:
            if isinstance(turn_value, int):
                quest.available_since_turn = turn_value
            elif isinstance(turn_value, dict):
                quest.available_since_turn = turn_value.get("available_since_turn", None)

    # ════════════════════════════════════════════════════════════
    # FINALIZAÇÃO
    # ════════════════════════════════════════════════════════════
    
    # Revalida quests
    manager._revalidate_available_quests()
    
    # Marca assistente
    if hasattr(manager, 'assistant'):
        manager.assistant.first_time = False
    
    # print(f"📂 Jogo carregado de: {path}")
    return True


# ════════════════════════════════════════════════════════════════
# FUNÇÕES AUXILIARES
# ════════════════════════════════════════════════════════════════

def list_saves():
    """Lista todos os arquivos de save disponíveis."""
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)
        return []
    
    files = [f for f in os.listdir(SAVE_DIR) if f.endswith('.json')]
    
    files.sort(
        key=lambda f: os.path.getmtime(os.path.join(SAVE_DIR, f)),
        reverse=True
    )
    
    return files


def delete_save(filename):
    """Deleta um arquivo de save."""
    filepath = os.path.join(SAVE_DIR, filename)
    
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"✅ Save '{filename}' deletado com sucesso")
            return True
        else:
            print(f"⚠️  Arquivo '{filename}' não encontrado")
            return False
    except Exception as e:
        print(f"❌ Erro ao deletar save: {e}")
        return False


def get_save_info(filename):
    """Obtém informações sobre um save."""
    filepath = os.path.join(SAVE_DIR, filename)
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # ✅ Conta procedurais também
        procedural_count = (
            len(data.get('procedural_available', [])) +
            len(data.get('procedural_active', {})) +
            len(data.get('procedural_completed', []))
        )
        
        return {
            'turn': data.get('current_turn', 0),
            'completed_quests': len(data.get('completed_quests', [])),
            'active_quests': len(data.get('active_quests', {})),
            'failed_quests': len(data.get('failed_quests', [])),
            'procedural_quests': procedural_count,  # ✅ Novo
        }
    except Exception as e:
        print(f"Erro ao ler info do save '{filename}': {e}")
        return None


def get_latest_save():
    """Retorna o save mais recente."""
    saves = list_saves()
    return saves[0] if saves else None



def save_state(manager, filename):
    """Alias de save_game — compatibilidade com save.save_state(qm, filename)."""
    return save_game(manager, filename)


def load_state(manager, filename):
    """Alias de load_game — compatibilidade com save.load_state(qm, filename)."""
    return load_game(manager, filename)


def _save_state_OLD(self) -> dict:  # mantido só para referência, não usar
    """
    Salva estado do QuestManager.
    
    UNIFICADO: Salva fixas e procedurais juntas!
    """
    return {
        "completed_quests": list(self.completed_quests),  # ✅ IDs (int ou str)
        "failed_quests": list(self.failed_quests),
        "active_quests": {
            str(qid): {
                "heroes": [h.id for h in data["heroes"]],
                "turns_left": data["turns_left"]
            }
            for qid, data in self.active_quests.items()
        },
        "current_turn": self.current_turn,
        
        # ✅ SALVA POOL DE PROCEDURAIS
    }
 
 
def _load_state_OLD(self, filename):  # mantido só para referência, não usar
    path = os.path.join(SAVE_DIR, filename)
    
    if not os.path.exists(path):
        print(f"⚠️  Save '{filename}' não encontrado.")
        return False
    
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    
    # ✅ CARREGA COMPLETED (FIXAS E PROCEDURAIS JUNTAS)
    self.completed_quests = set(data.get("completed_quests", []))
    self.failed_quests = set(data.get("failed_quests", []))
    self.current_turn = data.get("current_turn", 1)
    
    # ✅ RECONSTRÓI POOL DE PROCEDURAIS
    procedural_seeds = data.get("procedural_pool", [])
    for seed in procedural_seeds:
        quest = self.get_quest(seed)  # Reconstrói da seed
        if quest:
            self.procedural_pool[seed] = quest
    
    # ✅ CARREGA PROGRESSO DO MAPA
    map_progress = data.get("map_progress", {})
    unlocked = map_progress.get("unlocked_bridges", [])
    for bridge_key in unlocked:
        self.proc_gen.map_graph.unlock_bridge(bridge_key)
    
    # ✅ CARREGA ACTIVE QUESTS
    active = data.get("active_quests", {})
    for qid_str, data in active.items():
        # Converte ID de volta (int se for número, str se não)
        try:
            qid = int(qid_str)
        except ValueError:
            qid = qid_str
        
        # Reconstrói lista de heróis
        heroes = [self.get_hero(hid) for hid in data.get("heroes", [])]
        heroes = [h for h in heroes if h]  # Remove None
        
        self.active_quests[qid] = {
            "heroes": heroes,
            "turns_left": data.get("turns_left", 0)
        }