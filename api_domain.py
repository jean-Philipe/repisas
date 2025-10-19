from typing import Dict, List, Optional, Tuple

DEPTHS = [68, 48, 38, 28]
MAX_LEN = 243
MIN_LEN = 40
DOOR_CLEAR = 80
MIN_CORRIDOR_WIDTH = 58  # Minimum corridor width in cm
WASTE_TOLERANCE = 25  # Maximum waste difference to consider maximizing area in L-shape forms

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

def calculate_total_area(plan: List[Dict]) -> float:
    """
    Calcula el área total cubierta por las repisas (centímetros cuadrados).
    """
    total_area = 0.0
    for shelf in plan:
        length = shelf["length"]
        depth = shelf["depth"]
        area = length * depth
        total_area += area
    return total_area

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

def optimize_l_shape_planning(A: float, E: float, D: float, depthA: int, depthE: int, hl: Dict, useA: bool, useE: bool, C: float = 0.0) -> Tuple[float, float, List[Dict]]:
    """
    Optimiza la planificación para forma L entre A y E evaluando dos estrategias:
    1) A completa y E reducido por la profundidad de A.
    2) E completa y A reducido por la profundidad de E.
    Devuelve los largos elegidos y un plan local de referencia.
    """
    if not useA or not useE or not depthA or not depthE:
        lenA = A if useA else 0.0
        lenE = usable_length_e(E, D, True, C) if useE else 0.0
        plan: List[Dict] = []
        if useA and depthA:
            plan.extend(build_shelves_for_wall("A", lenA, depthA, hl["height"], hl["levels"]))
        if useE and depthE:
            plan.extend(build_shelves_for_wall("E", lenE, depthE, hl["height"], hl["levels"]))
        return lenA, lenE, plan

    usableE = usable_length_e(E, D, True, C)

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

def usable_length_e(E: float, D: float, use_e: bool, C: float = 0.0) -> float:
    if not use_e:
        return E
    # When D=0, there are no space restrictions, use full length
    if D == 0:
        # But check if there's a door restriction from C (door on E wall)
        if C > 0:
            return max(0.0, E - DOOR_CLEAR)
        return E
    return E

def usable_length_b(B: float, C: float, use_b: bool, D: float = 0.0) -> float:
    if not use_b:
        return B
    # When C=0, there are no space restrictions, use full length
    if C == 0:
        # Check if there's a door restriction from D (door on B wall)
        # D > 0 means there's a door on the B wall that reduces usable length
        if D > 0:
            return max(0.0, B - DOOR_CLEAR)
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

def evaluate_l_shape_strategies(depthA: int, depthB: int, A: float, B: float, C: float, hl: Dict, D: float = 0.0) -> List[Dict]:
    """
    Evalúa múltiples estrategias para la forma L entre A y B y devuelve todas las válidas.
    Prioriza estrategias que minimicen el número de repisas y la merma.
    
    En una forma L:
    - Si A ocupa la totalidad de su muro, B se reduce por la profundidad de A
    - Si B ocupa la totalidad de su muro, A se reduce por la profundidad de B
    - Priorizamos minimizar la merma sobre maximizar el ancho de las repisas
    - Considera múltiples repisas en B cuando hay espacio disponible
    """
    strategies = []
    
    # Estrategia 1: A completa, B reducido por la profundidad de A
    lenA1 = A
    usableB1 = usable_length_b(B, C, True, D)
    lenB1 = max(0.0, usableB1 - depthA)
    
    if (validate_shelf_length(lenA1) and validate_shelf_length(lenB1) and
        validate_corridor_width(A, lenA1, depthB, None, True, False)):
        
        plan1 = []
        plan1.extend(build_shelves_for_wall("A", lenA1, depthA, hl["height"], hl["levels"]))
        plan1.extend(build_shelves_for_wall("B", lenB1, depthB, hl["height"], hl["levels"]))
        
        strategies.append({
            "strategy": "A_complete_B_reduced",
            "plan": plan1,
            "lenA": lenA1,
            "lenB": lenB1,
            "depthA": depthA,
            "depthB": depthB
        })
        
        # NOTA: No agregar repisas adicionales en forma L
        # En forma L, las repisas A y B son complementarias, no aditivas
        # La repisa A cubre su longitud completa y la repisa B cubre solo la parte no ocupada por A
    
    # Estrategia 2: B completo, A reducido por la profundidad de B
    lenA2 = max(0.0, A - depthB)
    lenB2 = usable_length_b(B, C, True, D)
    
    if (validate_shelf_length(lenA2) and validate_shelf_length(lenB2) and
        validate_corridor_width(A, lenA2, depthB, None, True, False)):
        
        plan2 = []
        plan2.extend(build_shelves_for_wall("A", lenA2, depthA, hl["height"], hl["levels"]))
        plan2.extend(build_shelves_for_wall("B", lenB2, depthB, hl["height"], hl["levels"]))
        
        strategies.append({
            "strategy": "B_complete_A_reduced",
            "plan": plan2,
            "lenA": lenA2,
            "lenB": lenB2,
            "depthA": depthA,
            "depthB": depthB
        })
        
        # NOTA: No agregar repisas adicionales en forma L
        # En forma L, las repisas A y B son complementarias, no aditivas
        # La repisa B cubre su longitud completa y la repisa A cubre solo la parte no ocupada por B
    
    # Estrategia 3: A limitado para evitar división, B reducido por profundidad de A
    lenA3 = min(A, MAX_LEN)
    usableB3 = usable_length_b(B, C, True, D)
    lenB3 = max(0.0, usableB3 - depthA)
    
    if (validate_shelf_length(lenA3) and validate_shelf_length(lenB3) and
        validate_corridor_width(A, lenA3, depthB, None, True, False)):
        
        plan3 = []
        plan3.extend(build_shelves_for_wall("A", lenA3, depthA, hl["height"], hl["levels"]))
        plan3.extend(build_shelves_for_wall("B", lenB3, depthB, hl["height"], hl["levels"]))
        
        strategies.append({
            "strategy": "A_limited_B_reduced",
            "plan": plan3,
            "lenA": lenA3,
            "lenB": lenB3,
            "depthA": depthA,
            "depthB": depthB
        })
        
        # NOTA: No agregar repisas adicionales en forma L
        # En forma L, las repisas A y B son complementarias, no aditivas
        # La repisa A limitada cubre su longitud y la repisa B cubre solo la parte no ocupada por A
    
    # Estrategia 4: B limitado para evitar división, A reducido por profundidad de B
    lenA4 = max(0.0, A - depthB)
    usableB4 = usable_length_b(B, C, True, D)
    lenB4 = min(usableB4, MAX_LEN)
    
    if (validate_shelf_length(lenA4) and validate_shelf_length(lenB4) and
        validate_corridor_width(A, lenA4, depthB, None, True, False)):
        
        plan4 = []
        plan4.extend(build_shelves_for_wall("A", lenA4, depthA, hl["height"], hl["levels"]))
        plan4.extend(build_shelves_for_wall("B", lenB4, depthB, hl["height"], hl["levels"]))
        
        strategies.append({
            "strategy": "B_limited_A_reduced",
            "plan": plan4,
            "lenA": lenA4,
            "lenB": lenB4,
            "depthA": depthA,
            "depthB": depthB
        })
        
        # NOTA: No agregar repisas adicionales en forma L
        # En forma L, las repisas A y B son complementarias, no aditivas
        # La repisa B limitada cubre su longitud y la repisa A cubre solo la parte no ocupada por B
    
    # Estrategias adicionales con diferentes profundidades para minimizar merma
    # Probar con profundidades menores para encontrar la combinación con menor merma
    
    # Estrategia 5: A completa, B reducido, pero con profundidades ajustadas
    for test_depthA in [68, 48, 38, 28]:
        lenA5 = A
        usableB5 = usable_length_b(B, C, True, D)
        lenB5 = max(0.0, usableB5 - test_depthA)
            
        if (validate_shelf_length(lenA5) and validate_shelf_length(lenB5) and
            validate_corridor_width(A, lenA5, depthB, None, True, False)):
            
            plan5 = []
            plan5.extend(build_shelves_for_wall("A", lenA5, test_depthA, hl["height"], hl["levels"]))
            plan5.extend(build_shelves_for_wall("B", lenB5, depthB, hl["height"], hl["levels"]))
            
            strategies.append({
                "strategy": f"A_complete_B_reduced_depthA{test_depthA}",
                "plan": plan5,
                "lenA": lenA5,
                "lenB": lenB5,
                "depthA": test_depthA,
                "depthB": depthB
            })
            
            # NOTA: No agregar repisas adicionales en forma L
            # En forma L, las repisas A y B son complementarias, no aditivas
    
    # Estrategia 6: B completo, A reducido, pero con profundidades ajustadas
    for test_depthB in [68, 48, 38, 28]:
        if test_depthB <= C:  # Verificar restricción de espacio
            lenA6 = max(0.0, A - test_depthB)
            lenB6 = usable_length_b(B, C, True, D)
            
            if (validate_shelf_length(lenA6) and validate_shelf_length(lenB6) and
                validate_corridor_width(A, lenA6, test_depthB, None, True, False)):
                
                plan6 = []
                plan6.extend(build_shelves_for_wall("A", lenA6, depthA, hl["height"], hl["levels"]))
                plan6.extend(build_shelves_for_wall("B", lenB6, test_depthB, hl["height"], hl["levels"]))
                
                strategies.append({
                    "strategy": f"B_complete_A_reduced_depthB{test_depthB}",
                    "plan": plan6,
                    "lenA": lenA6,
                    "lenB": lenB6,
                    "depthA": depthA,
                    "depthB": test_depthB
                })
                
                # NOTA: No agregar repisas adicionales en forma L
                # En forma L, las repisas A y B son complementarias, no aditivas
    
    # Estrategia 7: Maximizar cobertura de B con diferentes combinaciones de profundidades
    # Probar todas las combinaciones de profundidades para encontrar la que maximice la cobertura de B
    for test_depthA in [68, 48, 38, 28]:
        for test_depthB in [68, 48, 38, 28]:
            if test_depthB <= C:  # Verificar restricción de espacio
                # Estrategia: A completa, B con máxima cobertura posible
                lenA7 = A
                usableB7 = usable_length_b(B, C, True, D)
                lenB7 = max(0.0, usableB7 - test_depthA)
                
                # NOTA: No agregar repisas adicionales en forma L
                # En forma L, las repisas A y B son complementarias, no aditivas
    
    return strategies

def evaluate_u_shape_strategies(depthA: int, depthB: int, depthE: int, A: float, B: float, C: float, D: float, E: float, hl: Dict) -> List[Dict]:
    """
    Evalúa múltiples estrategias para la forma U y devuelve todas las válidas.
    Prioriza estrategias que minimicen el número de repisas y maximicen el ancho.
    
    En una forma U:
    - Si B y E ocupan la totalidad de sus muros, A se reduce por sus profundidades
    - Si A ocupa la totalidad de su muro, B y E se reducen por la profundidad de A
    - Priorizamos maximizar el ancho de las repisas para el cliente
    """
    strategies = []
    
    # Estrategia 1: B y E completos, A reducida por sus profundidades
    lenA1 = max(0.0, A - depthB - depthE)
    lenB1 = usable_length_b(B, C, True, D)
    lenE1 = usable_length_e(E, D, True, C)
    
    if (validate_shelf_length(lenA1) and validate_shelf_length(lenB1) and validate_shelf_length(lenE1) and
        validate_corridor_width(A, lenA1, depthB, depthE, True, True)):
        
        plan1 = []
        plan1.extend(build_shelves_for_wall("A", lenA1, depthA, hl["height"], hl["levels"]))
        plan1.extend(build_shelves_for_wall("B", lenB1, depthB, hl["height"], hl["levels"]))
        plan1.extend(build_shelves_for_wall("E", lenE1, depthE, hl["height"], hl["levels"]))
        
        strategies.append({
            "strategy": "BE_complete_A_reduced",
            "plan": plan1,
            "lenA": lenA1,
            "lenB": lenB1,
            "lenE": lenE1,
            "depthA": depthA,
            "depthB": depthB,
            "depthE": depthE
        })
    
    # Estrategia 2: A completa, B y E reducidos por la profundidad de A
    lenA2 = A
    lenB2 = max(0.0, usable_length_b(B, C, True, D) - depthA)
    lenE2 = max(0.0, usable_length_e(E, D, True, C) - depthA)
    
    if (validate_shelf_length(lenA2) and validate_shelf_length(lenB2) and validate_shelf_length(lenE2) and
        validate_corridor_width(A, lenA2, depthB, depthE, True, True)):
        
        plan2 = []
        plan2.extend(build_shelves_for_wall("A", lenA2, depthA, hl["height"], hl["levels"]))
        plan2.extend(build_shelves_for_wall("B", lenB2, depthB, hl["height"], hl["levels"]))
        plan2.extend(build_shelves_for_wall("E", lenE2, depthE, hl["height"], hl["levels"]))
        
        strategies.append({
            "strategy": "A_complete_BE_reduced",
            "plan": plan2,
            "lenA": lenA2,
            "lenB": lenB2,
            "lenE": lenE2,
            "depthA": depthA,
            "depthB": depthB,
            "depthE": depthE
        })
    
    # Estrategia 3: A reducida para evitar división, B y E completos
    lenA3 = min(max(0.0, A - depthB - depthE), MAX_LEN)
    lenB3 = usable_length_b(B, C, True, D)
    lenE3 = usable_length_e(E, D, True, C)
    
    if (validate_shelf_length(lenA3) and validate_shelf_length(lenB3) and validate_shelf_length(lenE3) and
        validate_corridor_width(A, lenA3, depthB, depthE, True, True)):
        
        plan3 = []
        plan3.extend(build_shelves_for_wall("A", lenA3, depthA, hl["height"], hl["levels"]))
        plan3.extend(build_shelves_for_wall("B", lenB3, depthB, hl["height"], hl["levels"]))
        plan3.extend(build_shelves_for_wall("E", lenE3, depthE, hl["height"], hl["levels"]))
        
        strategies.append({
            "strategy": "A_reduced_no_division",
            "plan": plan3,
            "lenA": lenA3,
            "lenB": lenB3,
            "lenE": lenE3,
            "depthA": depthA,
            "depthB": depthB,
            "depthE": depthE
        })
    
    # Estrategia 4: A completa limitada, B y E reducidos por profundidad de A
    lenA4 = min(A, MAX_LEN)
    lenB4 = max(0.0, usable_length_b(B, C, True, D) - depthA)
    lenE4 = max(0.0, usable_length_e(E, D, True, C) - depthA)
    
    if (validate_shelf_length(lenA4) and validate_shelf_length(lenB4) and validate_shelf_length(lenE4) and
        validate_corridor_width(A, lenA4, depthB, depthE, True, True)):
        
        plan4 = []
        plan4.extend(build_shelves_for_wall("A", lenA4, depthA, hl["height"], hl["levels"]))
        plan4.extend(build_shelves_for_wall("B", lenB4, depthB, hl["height"], hl["levels"]))
        plan4.extend(build_shelves_for_wall("E", lenE4, depthE, hl["height"], hl["levels"]))
        
        strategies.append({
            "strategy": "A_limited_BE_reduced",
            "plan": plan4,
            "lenA": lenA4,
            "lenB": lenB4,
            "lenE": lenE4,
            "depthA": depthA,
            "depthB": depthB,
            "depthE": depthE
        })
    
    # Estrategia 5: B y E simétricos completos, A reducida por sus profundidades
    # Esta es la estrategia ideal para forma U donde B y E deben ser simétricos
    lenB5 = usable_length_b(B, C, True, D)
    lenE5 = usable_length_e(E, D, True, C)
    lenA5 = max(0.0, A - depthB - depthE)
    
    if (validate_shelf_length(lenA5) and validate_shelf_length(lenB5) and validate_shelf_length(lenE5) and
        validate_corridor_width(A, lenA5, depthB, depthE, True, True)):
        
        plan5 = []
        plan5.extend(build_shelves_for_wall("A", lenA5, depthA, hl["height"], hl["levels"]))
        plan5.extend(build_shelves_for_wall("B", lenB5, depthB, hl["height"], hl["levels"]))
        plan5.extend(build_shelves_for_wall("E", lenE5, depthE, hl["height"], hl["levels"]))
        
        strategies.append({
            "strategy": "BE_symmetric_A_reduced",
            "plan": plan5,
            "lenA": lenA5,
            "lenB": lenB5,
            "lenE": lenE5,
            "depthA": depthA,
            "depthB": depthB,
            "depthE": depthE
        })
    
    return strategies

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
            # Forma L con A y B - evaluar múltiples estrategias
            strategies = evaluate_l_shape_strategies(depthA, depthB, A, B, C, hl, D)
            
            if strategies:
                # Calcular métricas adicionales para cada estrategia
                for strategy in strategies:
                    plan = strategy["plan"]
                    b_shelves = [s for s in plan if s['wall'] == 'B']
                    a_shelves = [s for s in plan if s['wall'] == 'A']
                    
                    total_a_length = sum(s['length'] for s in a_shelves)
                    total_b_length = sum(s['length'] for s in b_shelves)
                    
                    # Calcular cobertura de cada muro
                    a_coverage = total_a_length / A if A > 0 else 0
                    b_coverage = total_b_length / B if B > 0 else 0
                    
                    # Calcular cobertura total (promedio de ambos muros)
                    total_coverage = (a_coverage + b_coverage) / 2
                    
                    # Calcular área total cubierta
                    total_area = calculate_total_area(plan)
                    
                    strategy["a_coverage"] = a_coverage
                    strategy["b_coverage"] = b_coverage
                    strategy["total_coverage"] = total_coverage
                    strategy["total_area"] = total_area
                    strategy["total_a_length"] = total_a_length
                    strategy["total_b_length"] = total_b_length
                
                # Ordenar estrategias priorizando:
                # 1. Mayor área total cubierta (objetivo principal - maximizar espacio útil)
                # 2. Mayor cobertura total (promedio de cobertura de ambos muros)
                # 3. Menor número de repisas (cuando el área es similar)
                # 4. Menor merma (criterio final)
                strategies.sort(key=lambda s: (
                    -s["total_area"],            # Priorizar mayor área total
                    -s["total_coverage"],        # Luego mayor cobertura total
                    len(s["plan"]),              # Luego menor número de repisas
                    calculate_waste(s["plan"])   # Finalmente menor merma
                ))
                
                # Seleccionar la primera estrategia (ya está ordenada correctamente)
                best_strategy = strategies[0]
                
                return {
                    "valid": True,
                    "plan": best_strategy["plan"],
                    "lenA": best_strategy["lenA"],
                    "lenB": best_strategy["lenB"],
                    "lenE": 0.0,
                    "depthA": best_strategy["depthA"],
                    "depthB": best_strategy["depthB"],
                    "depthE": None,
                    "complete_form": True,
                    "strategy": best_strategy["strategy"]
                }
            else:
                return {"valid": False, "reason": f"No se pueden crear repisas en forma L con muros A y B. Verifique que: 1) Las longitudes de A ({A} cm) y B ({B} cm) sean suficientes, 2) El espacio disponible C ({C} cm) permita la profundidad mínima (28 cm), 3) El pasillo tenga al menos {MIN_CORRIDOR_WIDTH} cm de ancho."}
                
        elif useA and useE and not useB:
            # Forma L con A y E
            lenA = A
            Eu = usable_length_e(E, D, True, C)
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
                return {"valid": False, "reason": f"No se pueden crear repisas en forma L con muros A y E. Verifique que: 1) Las longitudes de A ({A} cm) y E ({E} cm) sean suficientes, 2) El espacio disponible D ({D} cm) permita la profundidad mínima (28 cm), 3) El pasillo tenga al menos {MIN_CORRIDOR_WIDTH} cm de ancho."}
    
    elif shape == "U":
        if useA and useB and useE:
            # Forma U con A, B y E - evaluar múltiples estrategias
            strategies = evaluate_u_shape_strategies(depthA, depthB, depthE, A, B, C, D, E, hl)
            
            if strategies:
                # Ordenar estrategias por número de repisas (menor es mejor), 
                # y como segundo criterio por ancho total (mayor es mejor)
                strategies.sort(key=lambda s: (len(s["plan"]), -sum(p["depth"] for p in s["plan"])))
                best_strategy = strategies[0]
                
                return {
                    "valid": True,
                    "plan": best_strategy["plan"],
                    "lenA": best_strategy["lenA"],
                    "lenB": best_strategy["lenB"],
                    "lenE": best_strategy["lenE"],
                    "depthA": best_strategy["depthA"],
                    "depthB": best_strategy["depthB"],
                    "depthE": best_strategy["depthE"],
                    "complete_form": True,
                    "strategy": best_strategy["strategy"]
                }
            else:
                return {"valid": False, "reason": f"No se pueden crear repisas en forma U con muros A, B y E. Verifique que: 1) Las longitudes de A ({A} cm), B ({B} cm) y E ({E} cm) sean suficientes, 2) Los espacios disponibles C ({C} cm) y D ({D} cm) permitan las profundidades mínimas (28 cm), 3) El pasillo tenga al menos {MIN_CORRIDOR_WIDTH} cm de ancho."}
    
    # Para otras formas o configuraciones
    return {"valid": False, "reason": f"Configuración no soportada: forma '{shape}' con muros {walls}. Las formas soportadas son 'L' (con muros A-B o A-E) y 'U' (con muros A-B-E)."}

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
            
            # Calcular el ancho total de las repisas (mayor es mejor para el cliente)
            total_depth = sum(p["depth"] for p in plan)
            
            valid_combinations.append({
                "combination": combination,
                "result": result,
                "quality": (pieces, waste, cuts, total_len),
                "total_depth": total_depth,
                "score": (pieces, -total_depth, waste, cuts, total_len)  # Priorizar piezas, luego ancho
            })
    
    if not valid_combinations:
        return {"ok": False, "error": f"No es posible crear repisas en forma {shape} con los muros {walls}. Las posibles causas son: 1) Longitudes insuficientes (A={A} cm, B={B} cm, E={E} cm), 2) Espacios restringidos (C={C} cm, D={D} cm), 3) Pasillo insuficiente (mínimo {MIN_CORRIDOR_WIDTH} cm), 4) Altura de habitación insuficiente para las repisas."}
    
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
        min_height = min(opt['h'] for opt in HEIGHT_OPTIONS) + 30
        available_heights = ', '.join([f'{opt["h"]} cm' for opt in HEIGHT_OPTIONS])
        return {"ok": False, "error": f"La altura de la habitación ({room_height} cm) es insuficiente para las repisas. Se requiere al menos {min_height} cm (altura mínima de repisa + 30 cm de holgura al cielo). Las alturas disponibles son: {available_heights}."}

    # Usar el nuevo sistema de evaluación de combinaciones
    return find_best_combination(A, B, C, D, E, walls, shape, hl)
