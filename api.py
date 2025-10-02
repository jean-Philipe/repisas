from flask import Flask, request, jsonify, Response
import cairosvg
from api_domain import plan_shelves_py
from api_draw import render_svg

app = Flask(__name__)


def parse_walls(raw):
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw]
    # comma-separated string
    return [x.strip() for x in str(raw).split(',') if x.strip()]


@app.get('/plan')
def plan_endpoint_get():
    try:
        params = {
            'A': float(request.args.get('A', type=float)),
            'B': float(request.args.get('B', type=float)),
            'C': float(request.args.get('C', type=float)),
            'D': float(request.args.get('D', type=float)),
            'E': float(request.args.get('E', type=float)),
            'roomHeight': float(request.args.get('H', request.args.get('roomHeight', type=float))),
            'walls': parse_walls(request.args.get('walls')),
            'shape': request.args.get('shape', default='L'),
        }
    except Exception:
        return jsonify({'ok': False, 'error': 'Parámetros inválidos'}), 400

    result = plan_shelves_py(params)
    status = 200 if result.get('ok') else 422
    return jsonify({'input': params, 'result': result}), status


@app.post('/plan')
def plan_endpoint_post():
    try:
        payload = request.get_json(force=True)
        # allow either top-level fields or nested under 'input'
        body = payload.get('input', payload)
        params = {
            'A': float(body.get('A', 0)),
            'B': float(body.get('B', 0)),
            'C': float(body.get('C', 0)),
            'D': float(body.get('D', 0)),
            'E': float(body.get('E', 0)),
            'roomHeight': float(body.get('roomHeight', body.get('H', 0))),
            'walls': body.get('walls', []),
            'shape': body.get('shape', 'L'),
        }
    except Exception:
        return jsonify({'ok': False, 'error': 'JSON inválido'}), 400

    result = plan_shelves_py(params)
    status = 200 if result.get('ok') else 422
    return jsonify({'input': params, 'result': result}), status


@app.post('/render')
def render_endpoint():
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({'ok': False, 'error': 'JSON inválido'}), 400

    # Accept either a combined {'input':..., 'result':...} or just 'input' to recompute
    input_data = payload.get('input') or payload
    result = payload.get('result')
    if result is None:
        # recompute using the same planning logic to be robust
        result = plan_shelves_py(input_data)
        if not result.get('ok'):
            return jsonify({'ok': False, 'error': result.get('error', 'Error desconocido')}), 422

    # Render SVG y convertir a PNG preservando transparencias y colores
    svg = render_svg(input_data, result)
    png_bytes = cairosvg.svg2png(bytestring=svg.encode('utf-8'))
    return Response(png_bytes, mimetype='image/png')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
