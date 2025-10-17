from typing import Dict, List, Optional, Tuple

DEPTHS = [68, 48, 38, 28]
MAX_LEN = 243
MIN_LEN = 40
DOOR_CLEAR = 80

HEIGHT_OPTIONS = [
    {"h": 300, "levels": [6, 4]},
    {"h": 250, "levels": [5, 4]},
    {"h": 200, "levels": [4]},
]

def round1(x: float) -> float:
    return round(x * 10) / 10.0

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
    Optimiza la planificación para forma L considerando opciones de repisas más largas.
    Evalúa si es mejor usar una repisa larga que cubra parte de A y E.
    """
    if not useA or not useE or not depthA or not depthE:
        # Fallback al comportamiento original
        lenA = A
        lenE = usable_length_e(E, D, True)
        plan = []
        if useA:
            plan.extend(build_shelves_for_wall("A", lenA, depthA, hl["height"], hl["levels"]))
        if useE:
            plan.extend(build_shelves_for_wall("E", lenE, depthE, hl["height"], hl["levels"]))
        return lenA, lenE, plan
    
    # Opción 1: Planificación tradicional (A y E separados)
    lenA_trad = A
    lenE_trad = max(0.0, usable_length_e(E, D, True) - depthA)
    
    plan_trad = []
    if useA:
        plan_trad.extend(build_shelves_for_wall("A", lenA_trad, depthA, hl["height"], hl["levels"]))
    if useE:
        plan_trad.extend(build_shelves_for_wall("E", lenE_trad, depthE, hl["height"], hl["levels"]))
    
    # Opción 2: Una repisa larga para A completa + parte de E
    lenA_opt2 = A
    lenE_opt2 = max(0.0, usable_length_e(E, D, True) - depthA)
    
    # Si E queda muy corto, considerar una repisa que cubra A completa y E completa
    if lenE_opt2 < MIN_LEN:
        # Opción 3: Repisa que cubra A completa (122cm) y E completa (302cm)
        # Esto requeriría una repisa de 122 + 302 = 424cm, que excede MAX_LEN
        # Pero podemos evaluar si es mejor hacer una repisa de 122cm para A y otra de 302cm para E
        lenA_opt3 = A
        lenE_opt3 = usable_length_e(E, D, True)
        
        plan_opt3 = []
        if useA:
            plan_opt3.extend(build_shelves_for_wall("A", lenA_opt3, depthA, hl["height"], hl["levels"]))
        if useE:
            plan_opt3.extend(build_shelves_for_wall("E", lenE_opt3, depthE, hl["height"], hl["levels"]))
        
        # Evaluar todas las opciones
        quality_trad = evaluate_plan_quality(plan_trad)
        quality_opt3 = evaluate_plan_quality(plan_opt3)
        
        if quality_opt3 < quality_trad:
            return lenA_opt3, lenE_opt3, plan_opt3
    
    # Evaluar opción tradicional vs opción 2
    quality_trad = evaluate_plan_quality(plan_trad)
    
    return lenA_trad, lenE_trad, plan_trad

def pick_max_le(options: List[int], limit: float) -> Optional[int]:
    for v in options:
        if v <= limit:
            return v
    return None

def pick_height_and_levels(room_height: float) -> Optional[Dict[str, int]]:
    usable = room_height - 40
    sorted_opts = sorted(HEIGHT_OPTIONS, key=lambda o: o["h"], reverse=True)
    for opt in sorted_opts:
        if opt["h"] <= usable:
            return {"height": opt["h"], "levels": max(opt["levels"])}
    return None

def pack_lengths(target: float) -> List[float]:
    if target <= 0:
        return []
    if target <= MAX_LEN:
        return [round1(target)]
    n_full = int(target // MAX_LEN)
    rem = target - n_full * MAX_LEN
    if rem == 0:
        return [MAX_LEN] * n_full
    if rem < MIN_LEN:
        return [MAX_LEN] * n_full
    return [MAX_LEN] * n_full + [round1(rem)]

def max_depth_per_wall(C: float, D: float) -> Dict[str, Optional[int]]:
    b = pick_max_le(DEPTHS, C if C is not None else float("inf"))
    e = pick_max_le(DEPTHS, D if D is not None else float("inf"))
    a = pick_max_le(DEPTHS, float("inf"))
    return {"A": a, "B": b, "E": e}

def usable_length_e(E: float, D: float, use_e: bool) -> float:
    if not use_e:
        return E
    if D == 0:
        return max(0.0, E - DOOR_CLEAR)
    return E

def build_shelves_for_wall(wall: str, usable_len: float, depth: int, height: int, levels: int) -> List[Dict]:
    pieces = pack_lengths(usable_len)
    return [{"wall": wall, "length": l, "depth": depth, "height": height, "levels": levels} for l in pieces]

def plan_shelves_py(params: Dict) -> Dict:
    A = float(params.get("A", 0))
    B = float(params.get("B", 0))
    C = float(params.get("C", 0))
    D = float(params.get("D", 0))
    E = float(params.get("E", 0))
    room_height = float(params.get("roomHeight", params.get("H", 0)))
    walls = params.get("walls", [])
    shape = params.get("shape", "L")

    hl = pick_height_and_levels(room_height)
    if not hl:
        return {"ok": False, "error": "Ninguna altura cumple la holgura de 40 cm al cielo."}

    depth_max = max_depth_per_wall(C, D)
    useA = "A" in walls
    useB = "B" in walls
    useE = "E" in walls

    def choose_depth_common(ws: List[str]) -> Optional[int]:
        cands = [depth_max[w] for w in ws if depth_max.get(w) is not None]
        if not cands:
            return None
        return min(cands)

    depthA = depth_max.get("A")
    depthB = depth_max.get("B")
    depthE = depth_max.get("E")

    if shape == "U" and useA and useB and useE:
        common = choose_depth_common(["B", "A", "E"])
        if common:
            depthA = depthB = depthE = common

    lenA, lenB, lenE = A, B, E
    if shape == "L":
        useOnlyB = useA and useB and not useE
        useOnlyE = useA and useE and not useB
        
        # Para forma L, evaluar opciones cuando hay restricciones de longitud
        if useOnlyB and depthA and depthB:
            # Opción 1: A completa, B reducido
            lenA_opt1 = A
            lenB_opt1 = max(0.0, B - depthA)
            
            # Opción 2: A reducido, B completo
            lenA_opt2 = max(0.0, A - (depthB or 0))
            lenB_opt2 = B
            
            # Evaluar ambas opciones
            plan_opt1 = []
            if useA:
                plan_opt1.extend(build_shelves_for_wall("A", lenA_opt1, depthA, hl["height"], hl["levels"]))
            if useB:
                plan_opt1.extend(build_shelves_for_wall("B", lenB_opt1, depthB, hl["height"], hl["levels"]))
            
            plan_opt2 = []
            if useA:
                plan_opt2.extend(build_shelves_for_wall("A", lenA_opt2, depthA, hl["height"], hl["levels"]))
            if useB:
                plan_opt2.extend(build_shelves_for_wall("B", lenB_opt2, depthB, hl["height"], hl["levels"]))
            
            # Elegir la opción con mejor calidad (prioridad: menos piezas, menos merma, menos cortes)
            quality1 = evaluate_plan_quality(plan_opt1)
            quality2 = evaluate_plan_quality(plan_opt2)
            
            if quality1 <= quality2:
                lenA = lenA_opt1
                lenB = lenB_opt1
            else:
                lenA = lenA_opt2
                lenB = lenB_opt2
                
        elif useOnlyE and depthA and depthE:
            # Usar la función de optimización especializada para forma L con A y E
            lenA, lenE, plan = optimize_l_shape_planning(A, E, D, depthA, depthE, hl, useA, useE)
        else:
            if useA and useB:
                lenA = max(0.0, A - (depthB or 0))
            if useA and useE:
                lenA = max(0.0, A - (depthE or 0))
            if useE:
                lenE = usable_length_e(E, D, True)
    # Para forma U con A, B y E activos, evaluar combinaciones y elegir la que minimiza piezas
    if shape == "U" and useA and useB and useE:
        # Variante 1 (actual): restar profundidades laterales a A
        lenA_v1 = max(0.0, A - (depthB or 0) - (depthE or 0))
        lenB_v1 = B
        lenE_v1 = usable_length_e(E, D, True)

        # Variante 2 (priorizar A completa): usar A completa y descontar profundidad de A a B y E
        lenA_v2 = A
        lenB_v2 = max(0.0, B - (depthA or 0))
        lenE_v2 = max(0.0, usable_length_e(E, D, True) - (depthA or 0))

        def build_plan_lengths(la: float, lb: float, le: float):
            plan_local: List[Dict] = []
            if useB:
                if not depthB:
                    return None
                plan_local.extend(build_shelves_for_wall("B", lb, depthB, hl["height"], hl["levels"]))
            if useA:
                if not depthA:
                    return None
                plan_local.extend(build_shelves_for_wall("A", la, depthA, hl["height"], hl["levels"]))
            if useE:
                if not depthE:
                    return None
                plan_local.extend(build_shelves_for_wall("E", le, depthE, hl["height"], hl["levels"]))
            pieces = len(plan_local)
            cuts = sum(1 for p in plan_local if p["length"] < MAX_LEN)
            total_len = sum(p["length"] for p in plan_local)
            return {
                "plan": plan_local,
                "pieces": pieces,
                "cuts": cuts,
                "tot_len": total_len,
                "lens": (round1(la), round1(lb), round1(le)),
            }

        cand1 = build_plan_lengths(lenA_v1, lenB_v1, lenE_v1)
        cand2 = build_plan_lengths(lenA_v2, lenB_v2, lenE_v2)

        # Elegir el candidato con mejor calidad (prioridad: menos piezas, menos merma, menos cortes)
        best = cand1
        if cand2 is not None:
            if best is None:
                best = cand2
            else:
                # Evaluar calidad de ambos candidatos
                quality1 = evaluate_plan_quality(cand1["plan"])
                quality2 = evaluate_plan_quality(cand2["plan"])
                
                if quality2 < quality1:
                    best = cand2

        if best is not None:
            plan = best["plan"]
            lenA, lenB, lenE = best["lens"]
        else:
            # Fallback a la variante 1 si algo falló
            lenA = lenA_v1
            lenB = lenB_v1
            lenE = lenE_v1
            plan: List[Dict] = []
            if useB:
                plan.extend(build_shelves_for_wall("B", lenB, depthB, hl["height"], hl["levels"]))
            if useA:
                plan.extend(build_shelves_for_wall("A", lenA, depthA, hl["height"], hl["levels"]))
            if useE:
                plan.extend(build_shelves_for_wall("E", lenE, depthE, hl["height"], hl["levels"]))
    else:
        if shape != "L" and useE:
            lenE = usable_length_e(E, D, True)
        plan: List[Dict] = []
        if useB:
            if not depthB:
                return {"ok": False, "error": "No cabe ninguna profundidad en B por C."}
            plan.extend(build_shelves_for_wall("B", lenB, depthB, hl["height"], hl["levels"]))
        if useA:
            if not depthA:
                return {"ok": False, "error": "No hay profundidad válida para A."}
            plan.extend(build_shelves_for_wall("A", lenA, depthA, hl["height"], hl["levels"]))
        if useE:
            if not depthE:
                return {"ok": False, "error": "No cabe ninguna profundidad en E por D."}
            plan.extend(build_shelves_for_wall("E", lenE, depthE, hl["height"], hl["levels"]))

    totals = {
        "totalLen": round1(sum(p["length"] for p in plan)),
        "pieces": len(plan),
        "cuts": sum(1 for p in plan if p["length"] < MAX_LEN),
    }
    meta = {
        "depthMax": depth_max,
        "hl": hl,
        "lenA": round1(lenA),
        "lenB": round1(lenB),
        "lenE": round1(lenE),
    }
    return {"ok": True, "plan": plan, "totals": totals, "meta": meta}
