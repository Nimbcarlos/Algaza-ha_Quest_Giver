from typing import Dict, List, Optional, Tuple, Set
from collections import deque
import heapq

MAP_EDGES: List[Tuple[str, str, Optional[str], int]] = [
 
    # ── Goldenreach Plains — hub central ─────────────────────────────────────
    # Livre — adjacentes geográficos
    ("goldenreach_plains",              "olympos_peak_base",                None,                       1),
    ("goldenreach_plains",              "whispering_elwyn",                 None,                       1),
    # Pontes permanentes
    ("goldenreach_plains",              "evergreen_kokiri",                 "golden_block_span",        2),
    ("goldenreach_plains",              "azurewind_prairie",                "golden_wind_bridge",       2),
    ("goldenreach_plains",              "fields_of_endless_strife_west",    "three_battles_bridge",     2),
    ("goldenreach_plains",              "blightgrass_fields_west",          "dead_harvest_bridge",      2),
 
    # ── Whispering Elwyn ─────────────────────────────────────────────────────
    ("whispering_elwyn",                "evergreen_kokiri",                 "kokiri_root_bridge",       1),
 
    # ── Blightgrass Fields ───────────────────────────────────────────────────
    # Passagem interna — scarecrow_passage divide blightgrass em oeste/leste
    ("blightgrass_fields_west",         "blightgrass_fields_east",          "scarecrow_passage",        1),
    # Pontes e conexões
    ("blightgrass_fields_west",         "fields_of_endless_strife_west",    "dry_canal_crossing",       2),
    ("blightgrass_fields_east",         "howling_crown_range",              "blightcrown_ascent",       2),
    ("blightgrass_fields_east",         "spine_of_the_worldshard",          "blight_worldshard_climb",  2),
    ("blightgrass_fields_east",         "the_tarnished_expanse",            None,                       1),
    ("blightgrass_fields_east",         "stagnant_fens",                    None,                       1),
 
    # ── Fields of Endless Strife ─────────────────────────────────────────────
    # Passagem interna — broken_promise_bridge divide endless strife em oeste/leste
    ("fields_of_endless_strife_west",   "fields_of_endless_strife_east",    "broken_promise_bridge",    1),
    # Livre — adjacentes ao sul
    ("fields_of_endless_strife_west",   "fields_of_broken_grace",           None,                       1),
    ("fields_of_endless_strife_west",   "fungal_zangarmarsh",               None,                       1),
    ("fields_of_endless_strife_west",   "shadowed_limgrave",                None,                       1),
    ("fields_of_endless_strife_east",   "misty_swamp_planet",               None,                       1),
    ("fields_of_endless_strife_east",   "stagnant_fens",                    None,                       1),


    # ── Fields of Broken Grace ───────────────────────────────────────────────
    ("fields_of_broken_grace",          "shadowed_limgrave",                None,                       1),
 
    # ── Montanhas — Olympos Peak ─────────────────────────────────────────────
    ("olympos_peak_base",               "olympos_peak_plateau",             "olympos_ascent_stairway",  3),
    ("olympos_peak_plateau",            "mount_chillyard_passage",          "olympos_chillyard_trail",  3),
 
    # ── Montanhas — Mount Chillyard ──────────────────────────────────────────
    ("mount_chillyard_passage",         "mount_chillyard_gorge",            None,                       1),
    ("mount_chillyard_gorge",           "mount_chillyard_summit",           "chillyard_frost_span",     3),
    ("mount_chillyard_gorge",           "great_jura_wilds",                 "chillyard_border_pass",    2),
    ("mount_chillyard_summit",          "howling_crown_range",              "monarch_crown_link",       3),
 
    # ── Montanhas — Howling Crown / Throat of Rotghar ────────────────────────
    ("howling_crown_range",             "throat_of_rotghar",                "rotghar_throat_path",      3),
    ("throat_of_rotghar",               "great_jura_wilds",                 "rothgar_jurah_descent",    3),
    ("throat_of_rotghar",               "spine_of_the_worldshard",          None,                       1),
 
    # ── Spine of the Worldshard ──────────────────────────────────────────────
    ("spine_of_the_worldshard",         "petrified_caelum",                 "worldshard_caelum_gate",   2),
    ("spine_of_the_worldshard",         "ashen_summit_of_khar",             None,                       1),
 
    # ── Great Jura Wilds ─────────────────────────────────────────────────────
    ("great_jura_wilds",                "petrified_caelum",                 None,                       1),
 
    # ── Sul — Tarnished / Fens / Swamps ──────────────────────────────────────
    ("the_tarnished_expanse",           "stagnant_fens",                    None,                       3),
    ("the_tarnished_expanse",           "quagmire_of_despair",              "slow_drowning_bridge",     2),
    ("stagnant_fens",                   "misty_swamp_planet",               None,                       3),
    ("fungal_zangarmarsh",              "marshes_of_the_fallen",            None,                       3),
    ("fungal_zangarmarsh",              "misty_swamp_planet",               None,                       1),
    ("misty_swamp_planet",              "quagmire_of_despair",              None,                       3),
    ("toxic_bayou",                     "sunken_wilderness",                None,                       1),
    ("quagmire_of_despair",             "sunken_wilderness",                None,                       1),
]
 
class MapGraph:
    STARTING_LOCATION = "goldenreach_plains"

    def __init__(self, bridges_data: Dict = None):
        self.blocked_bridges: Set[str] = set()
        self._simulated_blocks: Set[str] = set()
        self.graph: Dict = self._build_graph()
        # Mapeia bridge_key para os dois nós que ela conecta
        self.bridge_endpoints: Dict[str, Tuple[str, str]] = self._map_bridges()

    def _build_graph(self) -> Dict:
        graph: Dict = {}
        for origin, destination, bridge, distance in MAP_EDGES:
            graph.setdefault(origin, {"connections": []})
            graph.setdefault(destination, {"connections": []})
            graph[origin]["connections"].append(
                {"destination": destination, "bridge": bridge, "distance": distance}
            )
            graph[destination]["connections"].append(
                {"destination": origin, "bridge": bridge, "distance": distance}
            )
        return graph

    def _map_bridges(self) -> Dict[str, Tuple[str, str]]:
        mapping = {}
        for origin, destination, bridge, _ in MAP_EDGES:
            if bridge:
                mapping[bridge] = (origin, destination)
        return mapping

    # ── Estado das arestas ────────────────────────────────────────────────────

    def block_bridge(self, bridge_key: str) -> List[str]:
        self.blocked_bridges.add(bridge_key)
        blocked_areas = self.get_locations_blocked_by(bridge_key)
        return blocked_areas

    def unblock_bridge(self, bridge_key: str) -> List[str]:
        previously_blocked = self.get_locations_blocked_by(bridge_key)
        self.blocked_bridges.discard(bridge_key)
        print(f"🔓 Desbloqueada: {bridge_key} → regiões reabertas: {previously_blocked or ['nenhuma']}")
        return previously_blocked

    def is_bridge_blocked(self, bridge_key: str) -> bool:
        return bridge_key in self.blocked_bridges

    def get_blocked_bridges(self) -> List[str]:
        return list(self.blocked_bridges)

    # ── Travessia ─────────────────────────────────────────────────────────────

    def _can_cross(self, conn: Dict, simulated: bool = False) -> bool:
        key = conn.get("bridge")
        if key is None:
            return True
        if simulated and key in self._simulated_blocks:
            return False
        return key not in self.blocked_bridges

    # ── Acessibilidade ────────────────────────────────────────────────────────

    def is_location_accessible(self, target: str) -> bool:
        # Se for uma ponte, verificamos se pelo menos um dos lados é acessível
        if target in self.bridge_endpoints:
            node_a, node_b = self.bridge_endpoints[target]
            # Uma ponte é acessível se pudermos chegar em QUALQUER um dos seus lados
            return self._check_node_accessibility(node_a) or self._check_node_accessibility(node_b)
        
        return self._check_node_accessibility(target)

    def _check_node_accessibility(self, node: str) -> bool:
        if node == self.STARTING_LOCATION:
            return True
        if node not in self.graph:
            return False

        visited = {self.STARTING_LOCATION}
        queue = deque([self.STARTING_LOCATION])
        while queue:
            current = queue.popleft()
            for conn in self.graph.get(current, {}).get("connections", []):
                dest = conn["destination"]
                if not self._can_cross(conn) or dest in visited:
                    continue
                if dest == node:
                    return True
                visited.add(dest)
                queue.append(dest)
        return False

    def get_blocking_bridge(self, target: str) -> Optional[str]:
        if target == self.STARTING_LOCATION or self.is_location_accessible(target):
            return None
        
        # Se o alvo for uma ponte bloqueada que isolou uma área, 
        # o "bloqueio" é ela mesma.
        if target in self.bridge_endpoints and self.is_bridge_blocked(target):
            return target

        # Busca BFS para encontrar o primeiro bloqueio no caminho
        # Se for ponte, testamos o nó mais próximo
        search_target = target
        if target in self.bridge_endpoints:
            search_target = self.bridge_endpoints[target][0]

        visited = {self.STARTING_LOCATION}
        queue = deque([(self.STARTING_LOCATION, None)])
        while queue:
            current, first_block = queue.popleft()
            for conn in self.graph.get(current, {}).get("connections", []):
                dest = conn["destination"]
                key = conn.get("bridge")
                if dest in visited:
                    continue
                visited.add(dest)

                block_on_path = first_block or (
                    key if key and self.is_bridge_blocked(key) else None
                )
                if dest == search_target:
                    return block_on_path
                
                # Continua a busca apenas se o caminho estiver livre ou se já encontramos um bloqueio anterior
                # (para encontrar o PRIMEIRO bloqueio)
                if self._can_cross(conn):
                    queue.append((dest, block_on_path))
        return None

    # ── Distância ─────────────────────────────────────────────────────────────

    def get_distance_to(self, target: str) -> int:
        """
        Calcula a menor distância até o alvo considerando bloqueios.
        Se target for uma ponte, retorna a distância até o lado mais próximo dela.
        """
        if target == self.STARTING_LOCATION:
            return 0
            
        # Dijkstra para encontrar o caminho mais curto respeitando bloqueios
        distances = {self.STARTING_LOCATION: 0}
        pq = [(0, self.STARTING_LOCATION)]
        
        target_nodes = {target}
        if target in self.bridge_endpoints:
            target_nodes = set(self.bridge_endpoints[target])

        min_dist_to_target = float('inf')

        while pq:
            d, u = heapq.heappop(pq)
            
            if d > distances.get(u, float('inf')):
                continue
                
            if u in target_nodes:
                min_dist_to_target = min(min_dist_to_target, d)
                # Não paramos aqui porque pode haver um caminho mais curto para outro nó do target
            
            for conn in self.graph.get(u, {}).get("connections", []):
                v = conn["destination"]
                if not self._can_cross(conn):
                    continue
                    
                weight = conn.get("distance", 1)
                if d + weight < distances.get(v, float('inf')):
                    distances[v] = d + weight
                    heapq.heappush(pq, (distances[v], v))
        
        # Retorna -1 se o alvo for inalcançável (não 0, para não confundir com o ponto de partida)
        return int(min_dist_to_target) if min_dist_to_target != float('inf') else -1
   
    def get_distance_between(self, origin: str, target: str) -> int:
        if origin == target:
            return 0

        if not self.is_location_accessible(origin) or not self.is_location_accessible(target):
            return -1

        distances = {origin: 0}
        pq = [(0, origin)]  # (custo, nó)

        while pq:
            current_cost, current = heapq.heappop(pq)

            if current_cost > distances.get(current, float("inf")):
                continue

            if current == target:
                return current_cost  # pode retornar cedo 👍

            for conn in self.graph.get(current, {}).get("connections", []):
                if not self._can_cross(conn):
                    continue

                dest = conn["destination"]
                new_cost = current_cost + conn.get("distance", 1)

                if new_cost < distances.get(dest, float("inf")):
                    distances[dest] = new_cost
                    heapq.heappush(pq, (new_cost, dest))

        return -1
   
    # ── Impacto de bloqueio ───────────────────────────────────────────────────

    def get_locations_blocked_by(self, edge_key: str) -> List[str]:
        if not edge_key:
            return []

        # Estado antes do bloqueio
        currently_accessible = set(self.get_accessible_locations())
        
        # Simula o bloqueio
        self._simulated_blocks.add(edge_key)
        accessible_without = set(self._get_accessible_simulated())
        self._simulated_blocks.discard(edge_key)

        # Áreas que eram acessíveis e deixaram de ser
        return sorted(list(currently_accessible - accessible_without))

    def _get_accessible_simulated(self) -> List[str]:
        accessible = {self.STARTING_LOCATION}
        queue = deque([self.STARTING_LOCATION])
        while queue:
            current = queue.popleft()
            for conn in self.graph.get(current, {}).get("connections", []):
                dest = conn["destination"]
                if dest in accessible or not self._can_cross(conn, simulated=True):
                    continue
                accessible.add(dest)
                queue.append(dest)
        return list(accessible)

    # ── Utilitários ───────────────────────────────────────────────────────────

    def get_accessible_locations(self) -> List[str]:
        # Retorna todos os nós e pontes acessíveis
        accessible = []
        # Checa nós
        for loc in self.graph:
            if self._check_node_accessibility(loc):
                accessible.append(loc)
        return accessible

    def get_next_bridges(self) -> List[Dict]:
        next_bridges = []
        seen = set()
        accessible_nodes = set(self.get_accessible_locations())
        
        for bridge, (node_a, node_b) in self.bridge_endpoints.items():
            if not self.is_bridge_blocked(bridge):
                continue
            
            # Se um lado é acessível e o outro não, é uma ponte candidata a expansão
            if (node_a in accessible_nodes and node_b not in accessible_nodes) or \
               (node_b in accessible_nodes and node_a not in accessible_nodes):
                
                from_node = node_a if node_a in accessible_nodes else node_b
                to_node = node_b if from_node == node_a else node_a
                
                next_bridges.append({"bridge": bridge, "from": from_node, "to": to_node})
        
        return next_bridges

# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    g = MapGraph()

    print("\n=== Bloqueando slow_drowning_bridge ===")
    blocked = g.block_bridge("slow_drowning_bridge")
    print("quagmire acessível:", g.is_location_accessible("quagmire_of_despair"))
    print("Bloqueio de quagmire:", g.get_blocking_bridge("quagmire_of_despair"))
    print("Distância para quagmire:", g.get_distance_to("quagmire_of_despair"))

    print("\n=== Impacto hipotético de dead_harvest_bridge ===")
    print("get_locations_blocked_by:", g.get_locations_blocked_by("dead_harvest_bridge"))

    print("\n=== get_next_bridges com dead_harvest bloqueada ===")
    g.block_bridge("dead_harvest_bridge")
    print([b["bridge"] for b in g.get_next_bridges()])
    
    print(g.get_distance_between("evergreen_kokiri", "quagmire_of_despair"))