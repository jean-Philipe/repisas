from typing import Dict


def render_svg(input_data: Dict, result: Dict) -> str:
    A = float(input_data["A"]) ; B = float(input_data["B"]) ; E = float(input_data["E"]) 
    base_w = A
    base_h = max(B, E)
    
    # Calcular el espacio necesario para las etiquetas
    def calculate_text_width(text: str, font_size: int = 12) -> float:
        # Aproximación del ancho del texto (1px por carácter es conservador)
        return len(text) * font_size * 0.6
    
    # Espacios necesarios para etiquetas de muros
    label_a_width = calculate_text_width(f"A ({A} cm)")
    label_b_width = calculate_text_width(f"B ({B} cm)")
    label_e_width = calculate_text_width(f"E ({E} cm)")
    
    # Margen mínimo para etiquetas (izquierda, derecha, arriba, abajo)
    margin_left = max(15, label_e_width + 5)
    margin_right = max(15, label_b_width + 5)
    margin_top = 25  # espacio para etiqueta A
    margin_bottom = 35  # espacio para leyenda
    
    # Calcular dimensiones del canvas necesario
    min_canvas_w = base_w + margin_left + margin_right
    min_canvas_h = base_h + margin_top + margin_bottom
    
    # Establecer un tamaño mínimo y escalar si es necesario
    min_size = 600
    scale_factor = max(min_size / min_canvas_w, min_size / min_canvas_h, 1.0)
    
    canvas_w = min_canvas_w * scale_factor
    canvas_h = min_canvas_h * scale_factor
    
    # Recalcular escala para el contenido
    available_w = canvas_w - margin_left - margin_right
    available_h = canvas_h - margin_top - margin_bottom
    s = min(available_w / base_w, available_h / base_h)
    
    # Dimensiones del cuarto escalado
    w = base_w * s
    h = base_h * s
    
    # Posición centrada con márgenes
    x0 = margin_left + (available_w - w) / 2
    y0 = margin_top + (available_h - h) / 2

    def per_wall(wall: str) -> float:
        return sum(p["length"] for p in result["plan"] if p["wall"] == wall)

    def depth_of(wall: str) -> float:
        for p in result["plan"]:
            if p["wall"] == wall:
                return p["depth"]
        return 0

    def has_wall(wall: str) -> bool:
        return any(p["wall"] == wall for p in result["plan"])

    def approximately_equal(a: float, b: float, tol: float = 0.5) -> bool:
        return abs(a - b) <= tol

    parts = []
    parts.append(
        f'<svg viewBox="0 0 {canvas_w} {canvas_h}" width="{canvas_w}" height="{canvas_h}"\n'
        f'     xmlns="http://www.w3.org/2000/svg" text-rendering="optimizeLegibility">'
    )
    # Inline styles to ensure crisp, black typography
    parts.append(
        '<style>\n'
        '  text { font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; fill:#111; }\n'
        '  .measure { font-size:12px; font-weight:700; }\n'
        '  .legend { font-size:13px; fill:#555; }\n'
        '  .walllbl { font-size:12px; }\n'
        '</style>'
    )
    # grid
    parts.append('<g class="grid" stroke="#ddd" stroke-width="1">')
    x = 0
    while x <= w:
        parts.append(f'<line x1="{x0+x}" y1="{y0}" x2="{x0+x}" y2="{y0+h}" />')
        x += s*50
    y = 0
    while y <= h:
        parts.append(f'<line x1="{x0}" y1="{y0+y}" x2="{x0+w}" y2="{y0+y}" />')
        y += s*50
    parts.append('</g>')

    # room rectangle
    parts.append(f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="none" stroke="#111" stroke-width="4" />')

    # wall labels A,B,E with measurements
    parts.append(f'<text class="walllbl" x="{x0 + w/2}" y="{y0 - 10}" text-anchor="middle">A ({A} cm)</text>')
    parts.append(f'<text class="walllbl" x="{x0 + w + 10}" y="{y0 + h/2}" text-anchor="start">B ({B} cm)</text>')
    parts.append(f'<text class="walllbl" x="{x0 - 10}" y="{y0 + h/2}" text-anchor="end">E ({E} cm)</text>')

    # shelves group
    parts.append('<g fill="#e43" fill-opacity="0.15" stroke="#e43" stroke-width="3">')

    # B (right)
    if per_wall('B') > 0:
        d = depth_of('B') * s
        L = min(per_wall('B'), B) * s
        hasA = has_wall('A')
        hasE = has_wall('E')
        dA = depth_of('A') * s if hasA else 0
        fills_full = approximately_equal(per_wall('B'), B)
        y_start = y0 if fills_full else ((y0 + dA) if (hasA and not hasE) else y0)
        parts.append(f'<rect x="{x0 + w - d}" y="{y_start}" width="{d}" height="{L}" />')

    # A (top)
    if per_wall('A') > 0:
        dA = depth_of('A') * s
        useE = has_wall('E')
        useB = has_wall('B')
        dE = depth_of('E') * s if useE else 0
        L = min(result['meta'].get('lenA', A), A) * s
        x_start = x0
        if useE:
            e_fills_full = approximately_equal(per_wall('E'), E)
            if e_fills_full:
                x_start = x0 + dE
        parts.append(f'<rect x="{x_start}" y="{y0}" width="{L}" height="{dA}" />')

    # E (left)
    if per_wall('E') > 0:
        d = depth_of('E') * s
        L = min(per_wall('E'), E) * s
        hasA = has_wall('A')
        hasB = has_wall('B')
        dA = depth_of('A') * s if hasA else 0
        fills_full = approximately_equal(per_wall('E'), E)
        y_start = y0 if fills_full else ((y0 + dA) if (hasA and not hasB) else y0)
        parts.append(f'<rect x="{x0}" y="{y_start}" width="{d}" height="{L}" />')

    parts.append('</g>')

    # shelf labels (outside the group so they're black)
    if per_wall('B') > 0:
        d = depth_of('B') * s
        hasA = has_wall('A')
        hasE = has_wall('E')
        dA = depth_of('A') * s if hasA else 0
        fills_full = approximately_equal(per_wall('B'), B)
        y_start = y0 if fills_full else ((y0 + dA) if (hasA and not hasE) else y0)
        parts.append(f'<text class="legend" x="{x0 + w - d/2}" y="{y_start - 6}" text-anchor="middle">{round(per_wall("B"),1)} × {int(depth_of("B"))}</text>')

    if per_wall('A') > 0:
        dA = depth_of('A') * s
        useE = has_wall('E')
        dE = depth_of('E') * s if useE else 0
        L = min(result['meta'].get('lenA', A), A) * s
        x_start = x0
        if useE:
            e_fills_full = approximately_equal(per_wall('E'), E)
            if e_fills_full:
                x_start = x0 + dE
        parts.append(f'<text class="legend" x="{x_start + L/2}" y="{y0 + dA + 14}" text-anchor="middle">{result["meta"].get("lenA", A)} × {int(depth_of("A"))}</text>')

    if per_wall('E') > 0:
        d = depth_of('E') * s
        hasA = has_wall('A')
        hasB = has_wall('B')
        dA = depth_of('A') * s if hasA else 0
        fills_full = approximately_equal(per_wall('E'), E)
        y_start = y0 if fills_full else ((y0 + dA) if (hasA and not hasB) else y0)
        parts.append(f'<text class="legend" x="{x0 + d/2}" y="{y_start - 6}" text-anchor="middle">{round(per_wall("E"),1)} × {int(depth_of("E"))}</text>')

    # legend
    parts.append(f'<text class="legend" x="{x0}" y="{y0 + h + 28}" text-anchor="start">Escala aproximada. Cuadrícula cada 50 cm.</text>')
    parts.append('</svg>')
    return "".join(parts)
