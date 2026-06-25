"""
steamworks.py
Wrapper DIRETO para Steam API via ctypes (sem SteamworksPy)
"""
import ctypes
import platform
import os


class STEAMWORKS:
    def __init__(self):
        self.loaded = False
        self.steam_api = None
        self._load_library()
    
    def _load_library(self):
        """Carrega a Steam API diretamente"""
        try:
            system = platform.system()
            
            if system == "Windows":
                # Adiciona o diretório atual ao PATH do Windows
                current_dir = os.path.abspath(os.getcwd())
                os.environ['PATH'] = current_dir + os.pathsep + os.environ.get('PATH', '')
                
                # Adiciona ao DLL search path (Python 3.8+)
                if hasattr(os, 'add_dll_directory'):
                    os.add_dll_directory(current_dir)
                
                # Usa caminho completo
                if platform.architecture()[0] == '64bit':
                    lib_name = "steam_api64.dll"
                else:
                    lib_name = "steam_api.dll"
                
                lib_path = os.path.join(current_dir, lib_name)
                
                if not os.path.exists(lib_path):
                    raise FileNotFoundError(f"DLL não encontrada: {lib_path}")
                
                # print(f"[Steamworks] Tentando carregar: {lib_path}")
                
                # Carrega com caminho completo
                self.steam_api = ctypes.CDLL(lib_path, winmode=0)
                
            elif system == "Linux":
                self.steam_api = ctypes.CDLL("./libsteam_api.so")
                
            elif system == "Darwin":
                self.steam_api = ctypes.CDLL("./libsteam_api.dylib")
            
        except Exception as e:
            print(f"[Steamworks] ❌ Erro ao carregar Steam API: {e}")
            print(f"[Steamworks] Diretório: {os.getcwd()}")
            print(f"[Steamworks] Arquivos DLL na pasta:")
            for f in os.listdir('.'):
                if f.endswith('.dll'):
                    print(f"    - {f}")
            self.steam_api = None
    
    def initialize(self):
        """Inicializa o Steamworks"""
        if not self.steam_api:
            print("[Steamworks] Steam API não carregada")
            return False
        
        try:
            # Chama SteamAPI_Init() diretamente
            init_func = self.steam_api.SteamAPI_Init
            init_func.restype = ctypes.c_bool
            
            result = init_func()
            self.loaded = result
           
            return result
            
        except Exception as e:
            print(f"[Steamworks] Erro ao inicializar: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_callbacks(self):
        """Processa callbacks do Steam"""
        if not self.loaded or not self.steam_api:
            return
        
        try:
            self.steam_api.SteamAPI_RunCallbacks()
        except:
            pass
    
    def shutdown(self):
        """Desliga o Steamworks"""
        if not self.loaded or not self.steam_api:
            return
        
        try:
            self.steam_api.SteamAPI_Shutdown()
            print("[Steamworks] Desligado")
            self.loaded = False
        except Exception as e:
            print(f"[Steamworks] Erro ao desligar: {e}")
    
    # ==================== HELPERS ====================
    def _get_user_stats(self):
        """Retorna o ponteiro para ISteamUserStats"""
        if not self.loaded:
            return None
        try:
            # Usa a função flat API
            func = self.steam_api.SteamAPI_SteamUserStats_v012
            func.restype = ctypes.c_void_p
            ptr = func()
            return ptr if ptr else None
        except AttributeError:
            # Fallback: tenta outra versão
            try:
                func = self.steam_api.SteamUserStats
                func.restype = ctypes.c_void_p
                return func()
            except:
                print("[Steamworks] Não foi possível obter UserStats")
                return None
    
    def _get_user(self):
        """Retorna o ponteiro para ISteamUser"""
        if not self.loaded:
            return None
        try:
            # Usa a função flat API
            func = self.steam_api.SteamAPI_SteamUser_v023
            func.restype = ctypes.c_void_p
            ptr = func()
            return ptr if ptr else None
        except AttributeError:
            # Fallback
            try:
                func = self.steam_api.SteamUser
                func.restype = ctypes.c_void_p
                return func()
            except:
                print("[Steamworks] Não foi possível obter User")
                return None
    
    # ==================== USER STATS (Achievements) ====================
    class UserStats:
        @staticmethod
        def SetAchievement(steamworks_instance, achievement_name):
            """Desbloqueia um achievement"""
            if not steamworks_instance.loaded:
                return False
            
            try:
                # Chama diretamente a função C++
                # bool SetAchievement(const char *pchName)
                func = steamworks_instance.steam_api.SteamAPI_ISteamUserStats_SetAchievement
                func.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
                func.restype = ctypes.c_bool
                
                user_stats = steamworks_instance._get_user_stats()
                if not user_stats:
                    print("[Steamworks] UserStats não disponível")
                    return False
                
                return func(user_stats, achievement_name.encode('utf-8'))
                
            except Exception as e:
                print(f"[Steamworks] Erro SetAchievement: {e}")
                return False
        
        @staticmethod
        def StoreStats(steamworks_instance):
            """Salva stats no Steam"""
            if not steamworks_instance.loaded:
                return False
            
            try:
                func = steamworks_instance.steam_api.SteamAPI_ISteamUserStats_StoreStats
                func.argtypes = [ctypes.c_void_p]
                func.restype = ctypes.c_bool
                
                user_stats = steamworks_instance._get_user_stats()
                if not user_stats:
                    return False
                
                return func(user_stats)
                
            except Exception as e:
                print(f"[Steamworks] Erro StoreStats: {e}")
                return False

        @staticmethod
        def RequestCurrentStats(steamworks_instance):
            if not steamworks_instance.loaded:
                return False

            try:
                func = steamworks_instance.steam_api.SteamAPI_ISteamUserStats_RequestCurrentStats
                func.argtypes = [ctypes.c_void_p]
                func.restype = ctypes.c_bool

                user_stats = steamworks_instance._get_user_stats()
                if not user_stats:
                    return False

                return func(user_stats)

            except Exception as e:
                print(f"[Steamworks] Erro RequestCurrentStats: {e}")
                return False

    # ==================== USER (Steam ID) ====================
    class Users:
        @staticmethod
        def GetSteamID(steamworks_instance):
            """Retorna o Steam ID do usuário"""
            if not steamworks_instance.loaded:
                return 0
            
            try:
                func = steamworks_instance.steam_api.SteamAPI_ISteamUser_GetSteamID
                func.argtypes = [ctypes.c_void_p]
                func.restype = ctypes.c_uint64
                
                user = steamworks_instance._get_user()
                if not user:
                    return 0
                
                return func(user)
                
            except Exception as e:
                print(f"[Steamworks] Erro GetSteamID: {e}")
                return 0

        @staticmethod
        def SetStatInt(steamworks_instance, stat_name, value):
            """Define uma stat inteira"""
            if not steamworks_instance.loaded:
                return False

            try:
                func = steamworks_instance.steam_api.SteamAPI_ISteamUserStats_SetStatInt32
                func.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int32]
                func.restype = ctypes.c_bool

                user_stats = steamworks_instance._get_user_stats()
                if not user_stats:
                    print("[Steamworks] UserStats não disponível")
                    return False

                return func(user_stats, stat_name.encode("utf-8"), int(value))

            except Exception as e:
                print(f"[Steamworks] Erro SetStatInt: {e}")
                return False

        @staticmethod
        def GetStatInt(steamworks_instance, stat_name):
            """Lê uma stat inteira"""
            if not steamworks_instance.loaded:
                return 0

            try:
                func = steamworks_instance.steam_api.SteamAPI_ISteamUserStats_GetStatInt32
                func.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.POINTER(ctypes.c_int32)]
                func.restype = ctypes.c_bool

                user_stats = steamworks_instance._get_user_stats()
                if not user_stats:
                    print("[Steamworks] UserStats não disponível")
                    return 0

                value = ctypes.c_int32()
                ok = func(user_stats, stat_name.encode("utf-8"), ctypes.byref(value))

                if ok:
                    return value.value
                return 0

            except Exception as e:
                print(f"[Steamworks] Erro GetStatInt: {e}")
                return 0

# Teste rápido
if __name__ == "__main__":
    print("Testando Steam API...")
    steam = STEAMWORKS()
    
    if steam.initialize():
        print(f"✅ Steam ID: {steam.Users.GetSteamID(steam)}")
        
        # Testa achievement
        if steam.UserStats.SetAchievement(steam, "TEST_ACH"):
            steam.UserStats.StoreStats(steam)
            print("✅ Achievement testado")
        
        steam.shutdown()
    else:
        print("❌ Falha ao conectar com Steam")