from typing import Dict


def render_svg(input_data: Dict, result: Dict) -> str:
    A = float(input_data["A"]) ; B = float(input_data["B"]) ; E = float(input_data["E"]) 
    walls = set(input_data.get("walls", []))
    base_w = A
    # Altura base debe reflejar únicamente los muros activos:
    # - Si solo E está activo (o A+E), usar E
    # - Si solo B está activo (o A+B), usar B
    # - Si B y E están activos, usar max(B, E)
    if ("B" in walls) and ("E" in walls):
        base_h = max(B, E)
    elif "B" in walls:
        base_h = B
    elif "E" in walls:
        base_h = E
    else:
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

    # Track positions for each wall to place shelves sequentially
    wall_positions = {'A': 0, 'B': 0, 'E': 0}
    # Detect if A fills the entire top length; if so, vertical shelves must start below A depth
    lenA_meta = float(result.get('meta', {}).get('lenA', A))
    a_fills_full_length = approximately_equal(lenA_meta, A)
    
    # Check for special L-shape case: exactly 2 shelves, A > 243cm but < A wall length
    def is_special_l_case():
        # Must be L-shape (A and B walls only, no E)
        if not (walls == {"A", "B"}):
            return False
        
        # Must have exactly 2 shelves
        if len(result["plan"]) != 2:
            return False
        
        # Check if one shelf is for A and one for B
        walls_in_plan = {shelf["wall"] for shelf in result["plan"]}
        if walls_in_plan != {"A", "B"}:
            return False
        
        # Find the A shelf
        a_shelf = next((shelf for shelf in result["plan"] if shelf["wall"] == "A"), None)
        if not a_shelf:
            return False
        
        # Check A shelf length conditions: >= 243cm but < A wall length
        a_length = a_shelf["length"]
        return a_length >= 243 and a_length < A
    
    special_l_case = is_special_l_case()

    # Draw each individual shelf from the plan
    for shelf in result["plan"]:
        wall = shelf["wall"]
        length = shelf["length"] * s
        depth = shelf["depth"] * s
        
        if wall == 'B':  # Right wall
            hasA = has_wall('A')
            hasE = has_wall('E')
            dA = depth_of('A') * s if hasA else 0
            fills_full = approximately_equal(per_wall('B'), B)
            
            # Calculate proper scaling for B wall based on its actual height
            # The B wall should be scaled based on its own height, not the base_h
            b_scale = s * (B / base_h) if base_h > 0 else s
            length_scaled = shelf["length"] * b_scale
            
            # Determine positioning based on which shelf occupies more of its wall
            if hasA and not hasE:
                # L-shape with A and B: determine which shelf occupies more of its wall
                lenA_meta = float(result.get('meta', {}).get('lenA', A))
                lenB_meta = float(result.get('meta', {}).get('lenB', B))
                a_percentage = lenA_meta / A if A > 0 else 0
                b_percentage = lenB_meta / B if B > 0 else 0
                b_fills_most = b_percentage > a_percentage
                
                if b_fills_most:
                    # B occupies most of its wall, start from top
                    y_start = y0
                else:
                    # A occupies most of its wall, start B below A to avoid overlap
                    y_start = y0 + dA
            else:
                # Default logic for other cases
                if hasA and a_fills_full_length:
                    y_start = y0 + dA
                else:
                    y_start = y0 if fills_full else ((y0 + dA) if (hasA and not hasE) else y0)
            
            # Position this shelf after previous ones on wall B
            current_y = y_start + wall_positions['B']
            parts.append(f'<rect x="{x0 + w - depth}" y="{current_y}" width="{depth}" height="{length_scaled}" />')
            wall_positions['B'] += length_scaled
            
        elif wall == 'A':  # Top wall
            useE = has_wall('E')
            useB = has_wall('B')
            dE = depth_of('E') * s if useE else 0
            dB = depth_of('B') * s if useB else 0
            
            # Special case: L-shape with 2 shelves, A > 243cm but < A wall length
            if special_l_case:
                # Position A shelf at the right edge (next to B wall)
                x_start = x0 + w - length
            else:
                # Determine positioning based on which shelf occupies most of its wall
                if useE and useB:
                    # U-shape: check if A fills the entire wall width
                    lenA_meta = float(result.get('meta', {}).get('lenA', A))
                    a_fills_full_width = approximately_equal(lenA_meta, A)
                    
                    if a_fills_full_width:
                        # A fills the entire wall, start from left edge
                        x_start = x0
                    else:
                        # A doesn't fill the entire wall, center between E and B depths
                        available_width = w - dE - dB
                        x_start = x0 + dE + (available_width - length) / 2
                elif useE:
                    # L-shape with A and E: determine which shelf occupies more of its wall
                    lenA_meta = float(result.get('meta', {}).get('lenA', A))
                    lenE_meta = float(result.get('meta', {}).get('lenE', E))
                    a_percentage = lenA_meta / A if A > 0 else 0
                    e_percentage = lenE_meta / E if E > 0 else 0
                    a_fills_most = a_percentage > e_percentage
                    
                    if a_fills_most:
                        # A occupies most of its wall, start from left edge
                        x_start = x0
                    else:
                        # E occupies most of its wall, start after E depth
                        x_start = x0 + dE
                elif useB:
                    # L-shape with A and B: determine which shelf occupies more of its wall
                    lenA_meta = float(result.get('meta', {}).get('lenA', A))
                    lenB_meta = float(result.get('meta', {}).get('lenB', B))
                    a_percentage = lenA_meta / A if A > 0 else 0
                    b_percentage = lenB_meta / B if B > 0 else 0
                    a_fills_most = a_percentage > b_percentage
                    
                    if a_fills_most:
                        # A occupies most of its wall, start from left edge
                        x_start = x0
                    else:
                        # B occupies most of its wall, start A from left edge to avoid overlap
                        x_start = x0
                else:
                    # Only A wall: start from left edge
                    x_start = x0
                
                # Position this shelf after previous ones on wall A
                x_start += wall_positions['A']
            
            parts.append(f'<rect x="{x_start}" y="{y0}" width="{length}" height="{depth}" />')
            wall_positions['A'] += length
            
        elif wall == 'E':  # Left wall
            hasA = has_wall('A')
            hasB = has_wall('B')
            dA = depth_of('A') * s if hasA else 0
            lenE_meta = float(result.get('meta', {}).get('lenE', E))
            fills_full = approximately_equal(lenE_meta, E)
            # If top shelf A spans full length, always start E below A to avoid overlap
            if hasA and a_fills_full_length:
                y_start = y0 + dA
            else:
                y_start = y0 if fills_full else ((y0 + dA) if (hasA and not hasB) else y0)
            # Position this shelf after previous ones on wall E
            current_y = y_start + wall_positions['E']
            parts.append(f'<rect x="{x0}" y="{current_y}" width="{depth}" height="{length}" />')
            wall_positions['E'] += length

    parts.append('</g>')

    # shelf labels (outside the group so they're black)
    # Draw labels for each individual shelf
    wall_positions_labels = {'A': 0, 'B': 0, 'E': 0}
    
    for i, shelf in enumerate(result["plan"]):
        wall = shelf["wall"]
        length = shelf["length"]
        depth = shelf["depth"]
        
        if wall == 'B':  # Right wall
            hasA = has_wall('A')
            hasE = has_wall('E')
            dA = depth_of('A') * s if hasA else 0
            fills_full = approximately_equal(per_wall('B'), B)
            
            # Calculate proper scaling for B wall based on its actual height
            # The B wall should be scaled based on its own height, not the base_h
            b_scale = s * (B / base_h) if base_h > 0 else s
            length_scaled = shelf["length"] * b_scale
            
            # Determine positioning based on which shelf occupies more of its wall
            if hasA and not hasE:
                # L-shape with A and B: determine which shelf occupies more of its wall
                lenA_meta = float(result.get('meta', {}).get('lenA', A))
                lenB_meta = float(result.get('meta', {}).get('lenB', B))
                a_percentage = lenA_meta / A if A > 0 else 0
                b_percentage = lenB_meta / B if B > 0 else 0
                b_fills_most = b_percentage > a_percentage
                
                if b_fills_most:
                    # B occupies most of its wall, start from top
                    y_start = y0
                else:
                    # A occupies most of its wall, start B below A to avoid overlap
                    y_start = y0 + dA
            else:
                # Default logic for other cases
                if hasA and a_fills_full_length:
                    y_start = y0 + dA
                else:
                    y_start = y0 if fills_full else ((y0 + dA) if (hasA and not hasE) else y0)
            
            # Position label for this specific shelf
            current_y = y_start + wall_positions_labels['B'] + (length_scaled / 2)
            parts.append(f'<text class="legend" x="{x0 + w - (depth * s)/2}" y="{current_y}" text-anchor="middle">{length} × {depth}</text>')
            wall_positions_labels['B'] += length_scaled
            
        elif wall == 'A':  # Top wall
            useE = has_wall('E')
            useB = has_wall('B')
            dE = depth_of('E') * s if useE else 0
            dB = depth_of('B') * s if useB else 0
            x_start = x0
            
            # Special case: L-shape with 2 shelves, A > 243cm but < A wall length
            if special_l_case:
                # Position A shelf at the right edge (next to B wall)
                x_start = x0 + w - (length * s)
            else:
                # Determine positioning based on which shelf occupies most of its wall
                if useE and useB:
                    # U-shape: check if A fills the entire wall width
                    lenA_meta = float(result.get('meta', {}).get('lenA', A))
                    a_fills_full_width = approximately_equal(lenA_meta, A)
                    
                    if a_fills_full_width:
                        # A fills the entire wall, start from left edge
                        x_start = x0
                    else:
                        # A doesn't fill the entire wall, center between E and B depths
                        available_width = w - dE - dB
                        x_start = x0 + dE + (available_width - (length * s)) / 2
                elif useE:
                    # L-shape with A and E: determine which shelf occupies more of its wall
                    lenA_meta = float(result.get('meta', {}).get('lenA', A))
                    lenE_meta = float(result.get('meta', {}).get('lenE', E))
                    a_percentage = lenA_meta / A if A > 0 else 0
                    e_percentage = lenE_meta / E if E > 0 else 0
                    a_fills_most = a_percentage > e_percentage
                    
                    if a_fills_most:
                        # A occupies most of its wall, start from left edge
                        x_start = x0
                    else:
                        # E occupies most of its wall, start after E depth
                        x_start = x0 + dE
                elif useB:
                    # L-shape with A and B: determine which shelf occupies more of its wall
                    lenA_meta = float(result.get('meta', {}).get('lenA', A))
                    lenB_meta = float(result.get('meta', {}).get('lenB', B))
                    a_percentage = lenA_meta / A if A > 0 else 0
                    b_percentage = lenB_meta / B if B > 0 else 0
                    a_fills_most = a_percentage > b_percentage
                    
                    if a_fills_most:
                        # A occupies most of its wall, start from left edge
                        x_start = x0
                    else:
                        # B occupies most of its wall, start A from left edge to avoid overlap
                        x_start = x0
                else:
                    # Only A wall: start from left edge
                    x_start = x0
                
                # Position this shelf after previous ones on wall A
                x_start += wall_positions_labels['A']
            
            # Position label for this specific shelf
            current_x = x_start + (length * s / 2)
            parts.append(f'<text class="legend" x="{current_x}" y="{y0 + (depth * s) + 14}" text-anchor="middle">{length} × {depth}</text>')
            wall_positions_labels['A'] += length * s
            
        elif wall == 'E':  # Left wall
            hasA = has_wall('A')
            hasB = has_wall('B')
            dA = depth_of('A') * s if hasA else 0
            lenE_meta = float(result.get('meta', {}).get('lenE', E))
            fills_full = approximately_equal(lenE_meta, E)
            if hasA and a_fills_full_length:
                y_start = y0 + dA
            else:
                y_start = y0 if fills_full else ((y0 + dA) if (hasA and not hasB) else y0)
            # Position label for this specific shelf
            current_y = y_start + wall_positions_labels['E'] + (length * s / 2)
            parts.append(f'<text class="legend" x="{x0 + (depth * s)/2}" y="{current_y}" text-anchor="middle">{length} × {depth}</text>')
            wall_positions_labels['E'] += length * s

    # legend
    parts.append(f'<text class="legend" x="{x0}" y="{y0 + h + 28}" text-anchor="start">Escala aproximada. Cuadrícula cada 50 cm.</text>')
    parts.append('</svg>')
    return "".join(parts)
