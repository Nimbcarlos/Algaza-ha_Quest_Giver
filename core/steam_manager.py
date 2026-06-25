from core.steamworks_wrapper import STEAMWORKS

class SteamManager:
    def __init__(self):
        self.steam = None
        self.is_initialized = False
        self.achievements_unlocked = set()
        self._initialize_steam()

    # ════════════════════════════════════════════════════════════════
    # INICIALIZAÇÃO
    # ════════════════════════════════════════════════════════════════
    def _initialize_steam(self):
        try:
            self.steam = STEAMWORKS()

            if self.steam.initialize():
                self.is_initialized = True

                # 🔥 ESSENCIAL
                self.steam.UserStats.RequestCurrentStats(self.steam)
            else:
                self.is_initialized = False

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.is_initialized = False

    # ════════════════════════════════════════════════════════════════
    # ACHIEVEMENTS
    # ════════════════════════════════════════════════════════════════
    def unlock_achievement(self, achievement_id: str):
        """Desbloqueia um achievement."""
        if not self.is_initialized:
            return False

        if achievement_id in self.achievements_unlocked:
            return False

        try:
            result = self.steam.UserStats.SetAchievement(self.steam, achievement_id)
            
            if result:
                if self.steam.UserStats.StoreStats(self.steam):
                    self.achievements_unlocked.add(achievement_id)
                    return True

            return False

        except Exception as e:
        #    print(f"[SteamManager] ❌ Erro ao desbloquear achievement: {e}")
            import traceback
            traceback.print_exc()
            return False

    # ════════════════════════════════════════════════════════════════
    # STATS
    # ════════════════════════════════════════════════════════════════
    def set_stat(self, stat_name: str, value: int):
        """Define uma stat inteira."""
        if not self.is_initialized:
            return False

        try:
        #    print(f"[SteamManager] 🔄 Atualizando stat: {stat_name} = {value}")
            
            # ✅ CORRIGIDO: Usa Users.SetStatInt (que você adicionou no steamworks.py)
            result = self.steam.Users.SetStatInt(self.steam, stat_name, value)
            
            if result:
                if self.steam.UserStats.StoreStats(self.steam):
                    return True
            
            return False

        except Exception as e:
            import traceback
            traceback.print_exc()
            return False

    def get_stat(self, stat_name: str) -> int:
        """Retorna o valor de uma stat."""
        if not self.is_initialized:
            return 0

        try:
            # ✅ CORRIGIDO: Usa Users.GetStatInt
            value = self.steam.Users.GetStatInt(self.steam, stat_name)
        #    print(f"[SteamManager] 📊 GetStatInt({stat_name}) = {value}")
            return value
        except Exception as e:
        #    print(f"[SteamManager] ⚠️  Erro ao ler stat {stat_name}: {e}")
            return 0

    # ════════════════════════════════════════════════════════════════
    # CALLBACKS
    # ════════════════════════════════════════════════════════════════
    def run_callbacks(self):
        """Processa callbacks do Steam (chame no loop principal)."""
        if self.is_initialized and self.steam:
            try:
                self.steam.run_callbacks()
            except:
                pass

    # ════════════════════════════════════════════════════════════════
    # SHUTDOWN
    # ════════════════════════════════════════════════════════════════
    def shutdown(self):
        """Finaliza o Steam."""
        if self.is_initialized and self.steam:
            try:
            #    print("[SteamManager] 🔄 Finalizando Steam...")
                self.steam.shutdown()
            #    print("[SteamManager] ✅ Steam finalizado")
            except Exception as e:
               print(f"[SteamManager] ⚠️  Erro ao finalizar: {e}")

    # ════════════════════════════════════════════════════════════════
    # INTEGRAÇÃO COM O JOGO
    # ════════════════════════════════════════════════════════════════
    def on_quest_resolved(self, quest, heroes, result):
        """Callback quando quest é resolvida."""
    #    print(f"\n[SteamManager] 📋 Quest {quest.id} resolvida: {result}")
        
        # ──────────────────────────────────────────────────────────
        # ATUALIZA STATS
        # ──────────────────────────────────────────────────────────
        if result == "success":
            # Pega stat atual e incrementa
            total = self.get_stat(Stats.QUESTS_COMPLETED) + 1

            self.set_stat(Stats.QUESTS_COMPLETED, total)
            
        #    print(f"[SteamManager] 📊 Total de quests completas: {total}")
            
            # ──────────────────────────────────────────────────────
            # ACHIEVEMENTS DE CONTAGEM
            # ──────────────────────────────────────────────────────
            if total == 1:
                self.unlock_achievement(Achievements.FIRST_QUEST)
            elif total == 10:
                self.unlock_achievement(Achievements.COMPLETE_10_QUESTS)
            elif total == 50:
                self.unlock_achievement(Achievements.COMPLETE_50_QUESTS)
            elif total == 100:
                self.unlock_achievement(Achievements.COMPLETE_100_QUESTS)
        
        elif result == "failure":
            total = self.get_stat(Stats.QUESTS_FAILED) + 1
            self.set_stat(Stats.QUESTS_FAILED, total)

        # ──────────────────────────────────────────────────────────
        # ACHIEVEMENTS DE HERÓIS
        # ──────────────────────────────────────────────────────────
        for hero in heroes:
            if hero.level >= 5:
                ach_id = f"HERO_{hero.id}_LEVEL_5"
                self.unlock_achievement(ach_id)
            
            if hero.level >= 10:
                ach_id = f"HERO_{hero.id}_LEVEL_10"
                self.unlock_achievement(ach_id)

        # ──────────────────────────────────────────────────────────
        # ACHIEVEMENTS ESPECÍFICOS DA QUEST
        # ──────────────────────────────────────────────────────────
        if hasattr(quest, "achievement") and quest.achievement:
            self.unlock_achievement(quest.achievement)

        self._check_hidden_events(quest, heroes, result)

    # ════════════════════════════════════════════════════════════════
    # EVENTOS ESPECIAIS
    # ════════════════════════════════════════════════════════════════
    def _check_hidden_events(self, quest, heroes, result):
        """Verifica achievements secretos."""
        if quest.id == 9999999999:
            for hero in heroes:
                if hero.id == "1":
                    self.unlock_achievement("QUEST_999_WITH_HERO_1")


# ════════════════════════════════════════════════════════════════
# SINGLETON
# ════════════════════════════════════════════════════════════════

_steam_manager = None

def get_steam_manager():
    global _steam_manager
    if _steam_manager is None:
        _steam_manager = SteamManager()
    return _steam_manager


# ════════════════════════════════════════════════════════════════
# ACHIEVEMENTS
# ════════════════════════════════════════════════════════════════

class Achievements:
    """IDs dos achievements do jogo."""
    
    # Quests
    FIRST_QUEST = "FIRST_QUEST"
    COMPLETE_10_QUESTS = "COMPLETE_10_QUESTS"
    COMPLETE_50_QUESTS = "COMPLETE_50_QUESTS"
    COMPLETE_100_QUESTS = "COMPLETE_100_QUESTS"
    
    # Heróis
    HERO_1_LEVEL_5 = "HERO_1_LEVEL_5"
    HERO_1_LEVEL_10 = "HERO_1_LEVEL_10"
    HERO_2_LEVEL_5 = "HERO_2_LEVEL_5"
    HERO_2_LEVEL_10 = "HERO_2_LEVEL_10"
    HERO_3_LEVEL_5 = "HERO_3_LEVEL_5"
    HERO_3_LEVEL_10 = "HERO_3_LEVEL_10"
    HERO_4_LEVEL_5 = "HERO_4_LEVEL_5"
    HERO_4_LEVEL_10 = "HERO_4_LEVEL_10"
    HERO_5_LEVEL_5 = "HERO_5_LEVEL_5"
    HERO_5_LEVEL_10 = "HERO_5_LEVEL_10"
    HERO_6_LEVEL_5 = "HERO_6_LEVEL_5"
    HERO_6_LEVEL_10 = "HERO_6_LEVEL_10"
    HERO_7_LEVEL_5 = "HERO_7_LEVEL_5"
    HERO_7_LEVEL_10 = "HERO_7_LEVEL_10"
    HERO_8_LEVEL_5 = "HERO_8_LEVEL_5"
    HERO_8_LEVEL_10 = "HERO_8_LEVEL_10"
    HERO_9_LEVEL_5 = "HERO_9_LEVEL_5"
    HERO_9_LEVEL_10 = "HERO_9_LEVEL_10"
    HERO_10_LEVEL_5 = "HERO_10_LEVEL_5"
    HERO_10_LEVEL_10 = "HERO_10_LEVEL_10"
    HERO_11_LEVEL_5 = "HERO_11_LEVEL_5"
    HERO_11_LEVEL_10 = "HERO_11_LEVEL_10"
    HERO_12_LEVEL_5 = "HERO_12_LEVEL_5"
    HERO_12_LEVEL_10 = "HERO_12_LEVEL_10"
    HERO_13_LEVEL_5 = "HERO_13_LEVEL_5"
    HERO_13_LEVEL_10 = "HERO_13_LEVEL_10"
    HERO_14_LEVEL_5 = "HERO_14_LEVEL_5"
    HERO_14_LEVEL_10 = "HERO_14_LEVEL_10"
    HERO_15_LEVEL_5 = "HERO_15_LEVEL_5"
    HERO_15_LEVEL_10 = "HERO_15_LEVEL_10"
    
    # Outros
    SURVIVE_100_TURNS = "SURVIVE_100_TURNS"


# ════════════════════════════════════════════════════════════════
# STATS
# ════════════════════════════════════════════════════════════════

class Stats:
    """IDs das stats do jogo."""
    QUESTS_COMPLETED = "QUESTS_COMPLETED"
    QUESTS_FAILED = "QUESTS_FAILED"
    TOTAL_TURNS_PLAYED = "TOTAL_TURNS_PLAYED"
    TOTAL_PLAYTIME = "TOTAL_PLAYTIME"


# ════════════════════════════════════════════════════════════════
# TESTE
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
#    print("Testando SteamManager...")
    
    steam = get_steam_manager()
    
    if steam.is_initialized:
    #    print("\n✅ Steam OK! Testando...")
        
        # Testa stat
    #    print("\n1. Testando stats:")
        steam.set_stat(Stats.QUESTS_COMPLETED, 1)
        value = steam.get_stat(Stats.QUESTS_COMPLETED)
    #    print(f"   Stat lida: {value}")
        
        # Testa achievement
    #    print("\n2. Testando achievement:")
        steam.unlock_achievement(Achievements.FIRST_QUEST)
        
        steam.shutdown()
    else:
       print("\n❌ Steam não inicializado")
    #    print("Verifique:")
    #    print("  1. Steam está rodando?")
    #    print("  2. steam_appid.txt existe?")
    #    print("  3. steam_api64.dll está na pasta?")
       