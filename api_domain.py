from typing import Dict, List, Optional, Tuple

DEPTHS = [68, 48, 38, 28]
MAX_LEN = 243
MIN_LEN = 40
DOOR_CLEAR = 80
MIN_CORRIDOR_WIDTH = 58  # Minimum corridor width in cm

HEIGHT_OPTIONS = [
    {"h": 300, "levels": [6]},
    {"h": 250, "levels": [5]},
    {"h": 200, "levels": [4]},
    {"h": 180, "levels": [4]},
    {"h": 160, "levels": [4]},
]

def round1(x: float) -> float:
    return round(x * 10) / 10.0

def validate_corridor_width(A: float, lenA: float, depthB: Optional[int], depthE: Optional[int], useB: bool, useE: bool) -> bool:
    """
    Valida que el pasillo tenga al menos MIN_CORRIDOR_WIDTH cm de ancho.
    
    Args:
        A: Longitud total del muro A
        lenA: Longitud de la repisa A
        depthB: Profundidad de la repisa B (si existe)
        depthE: Profundidad de la repisa E (si existe)
        useB: Si se usa el muro B
        useE: Si se usa el muro E
    
    Returns:
        True si el pasillo es válido, False en caso contrario
    """
    # Calcular el ancho disponible del pasillo
    # El pasillo disponible es siempre A menos las profundidades de las repisas laterales
    available_width = A
    
    # Restar las profundidades de las repisas laterales
    if useB and depthB:
        available_width -= depthB
    if useE and depthE:
        available_width -= depthE
    
    return available_width >= MIN_CORRIDOR_WIDTH

def adjust_shelf_widths_for_corridor(A: float, lenA: float, depthB: Optional[int], depthE: Optional[int], useB: bool, useE: bool) -> Tuple[Optional[int], Optional[int]]:
    """
    Ajusta automáticamente los anchos de las repisas B y E para cumplir con el pasillo mínimo.
    
    Args:
        A: Longitud total del muro A
        lenA: Longitud de la repisa A
        depthB: Profundidad original de la repisa B
        depthE: Profundidad original de la repisa E
        useB: Si se usa el muro B
        useE: Si se usa el muro E
    
    Returns:
        Tupla con las profundidades ajustadas (depthB_adj, depthE_adj)
    """
    # Calcular el ancho mínimo necesario para el pasillo
    min_corridor_needed = MIN_CORRIDOR_WIDTH
    # El espacio disponible para repisas es el ancho total menos el pasillo mínimo
    available_for_shelves = A - min_corridor_needed
    
    # Si no hay espacio suficiente para ninguna repisa, retornar None
    if available_for_shelves <= 0:
        return None, None
    
    # Si hay espacio pero es muy poco, usar el mínimo posible
    if available_for_shelves < 28:  # Mínimo para una repisa
        return None, None
    
    # Distribuir el espacio disponible entre las repisas
    depthB_adj = depthB
    depthE_adj = depthE
    
    if useB and useE and depthB and depthE:
        # Ambas repisas: distribuir proporcionalmente
        total_original = depthB + depthE
        if total_original > available_for_shelves:
            # Si no hay espacio para ambas repisas con mínimo, usar solo una
            if available_for_shelves < 56:  # 28 + 28 mínimo
                # Usar solo la repisa más grande
                if depthB >= depthE:
                    depthB_adj = min(depthB, available_for_shelves)
                    depthE_adj = None
                else:
                    depthE_adj = min(depthE, available_for_shelves)
                    depthB_adj = None
            else:
                # Reducir proporcionalmente
                ratio = available_for_shelves / total_original
                depthB_adj = max(28, int(depthB * ratio))  # Mínimo 28cm
                depthE_adj = max(28, int(depthE * ratio))  # Mínimo 28cm
                
                # Ajustar si aún no cumple
                while depthB_adj + depthE_adj > available_for_shelves:
                    if depthB_adj > depthE_adj:
                        depthB_adj = max(28, depthB_adj - 1)
                    else:
                        depthE_adj = max(28, depthE_adj - 1)
        else:
            # No hay necesidad de reducir
            depthB_adj = depthB
            depthE_adj = depthE
    
    elif useB and depthB:
        # Solo repisa B
        if depthB > available_for_shelves:
            depthB_adj = min(depthB, available_for_shelves)
        else:
            depthB_adj = depthB
        depthE_adj = None
    
    elif useE and depthE:
        # Solo repisa E
        if depthE > available_for_shelves:
            depthE_adj = min(depthE, available_for_shelves)
        else:
            depthE_adj = depthE
        depthB_adj = None
    
    return depthB_adj, depthE_adj

def calculate_waste(plan: List[Dict]) -> float:
    """
    Calcula la merma sobrante total para un plan de repisas.
    Si el largo > 121 cm, usa 243 cm como valor base.
    Si el largo <= 121 cm, usa 121 cm como valor base.
    """
    total_waste = 0.0
    for shelf in plan:
        length = shelf["length"]
        if length > 121:
            base_length = 243
        else:
            base_length = 121
        waste = base_length - length
        total_waste += waste
    return total_waste

def evaluate_plan_quality(plan: List[Dict]) -> Tuple[int, float, int, float]:
    """
    Evalúa la calidad de un plan de repisas.
    Retorna: (número_piezas, merma_total, número_cortes, longitud_total)
    Menor es mejor para todos los valores.
    """
    pieces = len(plan)
    waste = calculate_waste(plan)
    cuts = sum(1 for p in plan if p["length"] < MAX_LEN)
    total_len = sum(p["length"] for p in plan)
    return (pieces, waste, cuts, total_len)

def optimize_l_shape_planning(A: float, E: float, D: float, depthA: int, depthE: int, hl: Dict, useA: bool, useE: bool) -> Tuple[float, float, List[Dict]]:
    """
    Optimiza la planificación para forma L entre A y E evaluando dos estrategias:
    1) A completa y E reducido por la profundidad de A.
    2) E completa y A reducido por la profundidad de E.
    Devuelve los largos elegidos y un plan local de referencia.
    """
    if not useA or not useE or not depthA or not depthE:
        lenA = A if useA else 0.0
        lenE = usable_length_e(E, D, True) if useE else 0.0
        plan: List[Dict] = []
        if useA and depthA:
            plan.extend(build_shelves_for_wall("A", lenA, depthA, hl["height"], hl["levels"]))
        if useE and depthE:
            plan.extend(build_shelves_for_wall("E", lenE, depthE, hl["height"], hl["levels"]))
        return lenA, lenE, plan

    usableE = usable_length_e(E, D, True)

    # A siempre usa su longitud completa
    lenA = A
    lenE = max(0.0, usableE - depthA)
    
    # Validar que la longitud de E sea válida
    if not validate_shelf_length(lenE):
        # Si la longitud de E es menor al mínimo, no usar repisa E
        depthE = None
        lenE = 0.0
    else:
        # Validar pasillo - si no es válido, ajustar solo la profundidad de E
        if not validate_corridor_width(A, lenA, None, depthE, False, useE):
            # Ajustar solo la profundidad de E para cumplir el pasillo
            _, depthE_adj = adjust_shelf_widths_for_corridor(A, lenA, None, depthE, False, useE)
            if depthE_adj is not None:
                depthE = depthE_adj
                # Recalcular lenE con la nueva profundidad
                lenE = max(0.0, usableE - depthA)
                # Validar nuevamente que la longitud sea válida
                if not validate_shelf_length(lenE):
                    depthE = None
                    lenE = 0.0
            # Si no se puede ajustar, usar la profundidad mínima posible
            else:
                # Calcular la profundidad máxima posible para E
                max_depth_E = A - lenA - MIN_CORRIDOR_WIDTH
                if max_depth_E >= 28:  # Mínimo viable
                    depthE = int(max_depth_E)
                    # Recalcular lenE con la nueva profundidad
                    lenE = max(0.0, usableE - depthA)
                    # Validar nuevamente que la longitud sea válida
                    if not validate_shelf_length(lenE):
                        depthE = None
                        lenE = 0.0
                else:
                    # Si no hay espacio para E, no usar repisa E
                    depthE = None
                    lenE = 0.0
    
    # Construir el plan
    plan: List[Dict] = []
    if useA and depthA:
        plan.extend(build_shelves_for_wall("A", lenA, depthA, hl["height"], hl["levels"]))
    if useE and depthE:
        plan.extend(build_shelves_for_wall("E", lenE, depthE, hl["height"], hl["levels"]))
    
    return lenA, lenE, plan

def pick_max_le(options: List[int], limit: float) -> Optional[int]:
    for v in options:
        if v <= limit:
            return v
    return None

def pick_height_and_levels(room_height: float) -> Optional[Dict[str, int]]:
    usable = room_height - 30
    sorted_opts = sorted(HEIGHT_OPTIONS, key=lambda o: o["h"], reverse=True)
    for opt in sorted_opts:
        if opt["h"] <= usable:
            return {"height": opt["h"], "levels": max(opt["levels"])}
    return None

def pack_lengths(target: float) -> List[float]:
    if target <= 0:
        return []
    if target <= MAX_LEN:
        # Si la longitud total es menor al mínimo, no crear repisa
        if target < MIN_LEN:
            return []
        return [round1(target)]
    n_full = int(target // MAX_LEN)
    rem = target - n_full * MAX_LEN
    if rem == 0:
        return [MAX_LEN] * n_full
    # Solo incluir el remanente si es mayor o igual al mínimo
    if rem >= MIN_LEN:
        return [MAX_LEN] * n_full + [round1(rem)]
    else:
        # Si el remanente es menor al mínimo, no incluirlo
        return [MAX_LEN] * n_full

def max_depth_per_wall(C: float, D: float) -> Dict[str, Optional[int]]:
    # When C=0 or D=0, there are no space restrictions, use maximum depth
    b = pick_max_le(DEPTHS, C if C > 0 else float("inf"))
    e = pick_max_le(DEPTHS, D if D > 0 else float("inf"))
    a = pick_max_le(DEPTHS, float("inf"))
    return {"A": a, "B": b, "E": e}

def usable_length_e(E: float, D: float, use_e: bool) -> float:
    if not use_e:
        return E
    # When D=0, there are no space restrictions, use full length
    if D == 0:
        return E
    return E

def usable_length_b(B: float, C: float, use_b: bool) -> float:
    if not use_b:
        return B
    # When C=0, there are no space restrictions, use full length
    if C == 0:
        return B
    return B

def build_shelves_for_wall(wall: str, usable_len: float, depth: int, height: int, levels: int) -> List[Dict]:
    pieces = pack_lengths(usable_len)
    return [{"wall": wall, "length": l, "depth": depth, "height": height, "levels": levels} for l in pieces]

def validate_shelf_length(length: float) -> bool:
    """
    Valida que la longitud de una repisa sea válida (mayor o igual al mínimo).
    """
    return length >= MIN_LEN

def generate_depth_combinations(C: float, D: float) -> List[Dict[str, int]]:
    """
    Genera todas las combinaciones posibles de profundidades para los muros.
    
    Args:
        C: Restricción de espacio para el muro B
        D: Restricción de espacio para el muro E
    
    Returns:
        Lista de diccionarios con todas las combinaciones válidas de profundidades
    """
    combinations = []
    
    # Obtener profundidades válidas para cada muro
    valid_depths_b = [d for d in DEPTHS if d <= C] if C > 0 else DEPTHS
    valid_depths_e = [d for d in DEPTHS if d <= D] if D > 0 else DEPTHS
    valid_depths_a = DEPTHS  # A no tiene restricciones de espacio
    
    # Generar todas las combinaciones
    for depth_a in valid_depths_a:
        for depth_b in valid_depths_b:
            for depth_e in valid_depths_e:
                combinations.append({
                    "A": depth_a,
                    "B": depth_b,
                    "E": depth_e
                })
    
    return combinations

def evaluate_combination(combination: Dict[str, int], A: float, B: float, C: float, D: float, E: float, 
                        walls: List[str], shape: str, hl: Dict) -> Dict:
    """
    Evalúa una combinación específica de profundidades.
    
    Returns:
        Diccionario con el resultado de la evaluación
    """
    depthA = combination["A"]
    depthB = combination["B"] 
    depthE = combination["E"]
    
    useA = "A" in walls
    useB = "B" in walls
    useE = "E" in walls
    
    # Calcular longitudes según la forma
    if shape == "L":
        if useA and useB and not useE:
            # Forma L con A y B
            lenA = A
            Bu = usable_length_b(B, C, True)
            lenB = max(0.0, Bu - depthA)
            
            # Validar longitudes mínimas
            validA = validate_shelf_length(lenA)
            validB = validate_shelf_length(lenB)
            
            # Validar pasillo
            corridor_valid = validate_corridor_width(A, lenA, depthB, None, useB, False)
            
            if validA and validB and corridor_valid:
                # Crear plan
                plan = []
                if useA:
                    plan.extend(build_shelves_for_wall("A", lenA, depthA, hl["height"], hl["levels"]))
                if useB:
                    plan.extend(build_shelves_for_wall("B", lenB, depthB, hl["height"], hl["levels"]))
                
                return {
                    "valid": True,
                    "plan": plan,
                    "lenA": lenA,
                    "lenB": lenB,
                    "lenE": 0.0,
                    "depthA": depthA,
                    "depthB": depthB,
                    "depthE": None,
                    "complete_form": True
                }
            else:
                return {"valid": False, "reason": "Invalid lengths or corridor"}
                
        elif useA and useE and not useB:
            # Forma L con A y E
            lenA = A
            Eu = usable_length_e(E, D, True)
            lenE = max(0.0, Eu - depthA)
            
            # Validar longitudes mínimas
            validA = validate_shelf_length(lenA)
            validE = validate_shelf_length(lenE)
            
            # Validar pasillo
            corridor_valid = validate_corridor_width(A, lenA, None, depthE, False, useE)
            
            if validA and validE and corridor_valid:
                # Crear plan
                plan = []
                if useA:
                    plan.extend(build_shelves_for_wall("A", lenA, depthA, hl["height"], hl["levels"]))
                if useE:
                    plan.extend(build_shelves_for_wall("E", lenE, depthE, hl["height"], hl["levels"]))
                
                return {
                    "valid": True,
                    "plan": plan,
                    "lenA": lenA,
                    "lenB": 0.0,
                    "lenE": lenE,
                    "depthA": depthA,
                    "depthB": None,
                    "depthE": depthE,
                    "complete_form": True
                }
            else:
                return {"valid": False, "reason": "Invalid lengths or corridor"}
    
    elif shape == "U":
        if useA and useB and useE:
            # Forma U con A, B y E
            lenA = A
            lenB = usable_length_b(B, C, True)
            lenE = usable_length_e(E, D, True)
            
            # Ajustar longitudes para evitar superposiciones
            lenB = max(0.0, lenB - depthA)
            lenE = max(0.0, lenE - depthA)
            
            # Validar longitudes mínimas
            validA = validate_shelf_length(lenA)
            validB = validate_shelf_length(lenB)
            validE = validate_shelf_length(lenE)
            
            # Validar pasillo
            corridor_valid = validate_corridor_width(A, lenA, depthB, depthE, useB, useE)
            
            if validA and validB and validE and corridor_valid:
                # Crear plan
                plan = []
                if useA:
                    plan.extend(build_shelves_for_wall("A", lenA, depthA, hl["height"], hl["levels"]))
                if useB:
                    plan.extend(build_shelves_for_wall("B", lenB, depthB, hl["height"], hl["levels"]))
                if useE:
                    plan.extend(build_shelves_for_wall("E", lenE, depthE, hl["height"], hl["levels"]))
                
                return {
                    "valid": True,
                    "plan": plan,
                    "lenA": lenA,
                    "lenB": lenB,
                    "lenE": lenE,
                    "depthA": depthA,
                    "depthB": depthB,
                    "depthE": depthE,
                    "complete_form": True
                }
            else:
                return {"valid": False, "reason": "Invalid lengths or corridor"}
    
    # Para otras formas o configuraciones
    return {"valid": False, "reason": "Unsupported configuration"}

def find_best_combination(A: float, B: float, C: float, D: float, E: float, 
                         walls: List[str], shape: str, hl: Dict) -> Dict:
    """
    Encuentra la mejor combinación de profundidades que permita crear la forma solicitada.
    
    Prioriza:
    1. Combinaciones que permitan crear la forma completa
    2. Mejor calidad según los criterios existentes
    """
    combinations = generate_depth_combinations(C, D)
    valid_combinations = []
    
    # Evaluar todas las combinaciones
    for combination in combinations:
        result = evaluate_combination(combination, A, B, C, D, E, walls, shape, hl)
        if result["valid"]:
            # Calcular métricas de calidad
            plan = result["plan"]
            pieces, waste, cuts, total_len = evaluate_plan_quality(plan)
            
            valid_combinations.append({
                "combination": combination,
                "result": result,
                "quality": (pieces, waste, cuts, total_len),
                "score": pieces * 1000 + waste + cuts * 100 + total_len  # Menor es mejor
            })
    
    if not valid_combinations:
        return {"ok": False, "error": "No es posible armar la forma solicitada con las restricciones dadas."}
    
    # Ordenar por score (menor es mejor)
    valid_combinations.sort(key=lambda x: x["score"])
    best = valid_combinations[0]
    
    # Construir respuesta
    plan = best["result"]["plan"]
    totals = {
        "totalLen": round1(sum(p["length"] for p in plan)),
        "pieces": len(plan),
        "cuts": sum(1 for p in plan if p["length"] < MAX_LEN),
    }
    
    meta = {
        "depthMax": {
            "A": best["result"]["depthA"],
            "B": best["result"]["depthB"],
            "E": best["result"]["depthE"]
        },
        "hl": hl,
        "lenA": round1(best["result"]["lenA"]),
        "lenB": round1(best["result"]["lenB"]),
        "lenE": round1(best["result"]["lenE"]),
    }
    
    return {
        "ok": True,
        "plan": plan,
        "totals": totals,
        "meta": meta
    }

def plan_shelves_py(params: Dict) -> Dict:
    A = float(params.get("A", 0))
    B = float(params.get("B", 0))
    C = float(params.get("C", 0))
    D = float(params.get("D", 0))
    E = float(params.get("E", 0))
    room_height = float(params.get("roomHeight", params.get("H", 0)))
    walls = params.get("walls", [])
    shape = params.get("shape", "L").strip()  # Normalizar eliminando espacios

    hl = pick_height_and_levels(room_height)
    if not hl:
        return {"ok": False, "error": "Ninguna altura cumple la holgura de 30 cm al cielo."}

    # Usar el nuevo sistema de evaluación de combinaciones
    return find_best_combination(A, B, C, D, E, walls, shape, hl)
