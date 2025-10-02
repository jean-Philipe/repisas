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
        if useOnlyB and B > MAX_LEN and A <= MAX_LEN and depthA:
            lenA = A
            lenB = max(0.0, B - depthA)
        elif useOnlyE and usable_length_e(E, D, True) > MAX_LEN and A <= MAX_LEN and depthA:
            lenA = A
            lenE = max(0.0, usable_length_e(E, D, True) - depthA)
        else:
            if useA and useB:
                lenA = max(0.0, A - (depthB or 0))
            if useA and useE:
                lenA = max(0.0, A - (depthE or 0))
            if useE:
                lenE = usable_length_e(E, D, True)
    if shape == "U" and useA and useB and useE:
        lenA = max(0.0, A - (depthB or 0) - (depthE or 0))
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
