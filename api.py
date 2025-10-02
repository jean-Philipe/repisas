from flask import Flask, request, jsonify, Response
import cairosvg
from api_domain import plan_shelves_py
from api_draw import render_svg
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.utils import ImageReader
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO

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

    try:
        # Render SVG y convertir a PNG preservando transparencias y colores
        svg = render_svg(input_data, result)
        if not svg or len(svg.strip()) == 0:
            return jsonify({'ok': False, 'error': 'SVG generado está vacío'}), 500
            
        # Convertir con parámetros específicos para evitar corrupción
        png_bytes = cairosvg.svg2png(
            bytestring=svg.encode('utf-8'),
            output_width=1200,
            output_height=900,
            background_color='white'
        )
        
        if not png_bytes or len(png_bytes) == 0:
            return jsonify({'ok': False, 'error': 'PNG generado está vacío'}), 500
            
        return Response(png_bytes, mimetype='image/png')
    except Exception as e:
        return jsonify({'ok': False, 'error': f'Error generando imagen: {str(e)}'}), 500


@app.post('/pdf')
def pdf_endpoint():
    try:
        # Verificar que se enviaron los archivos
        if 'image' not in request.files or 'pdf' not in request.files:
            return jsonify({'ok': False, 'error': 'Se requieren archivos "image" (PNG) y "pdf"'}), 400
        
        image_file = request.files['image']
        pdf_file = request.files['pdf']
        
        if image_file.filename == '' or pdf_file.filename == '':
            return jsonify({'ok': False, 'error': 'Archivos no seleccionados'}), 400
        
        # Leer archivos
        image_data = image_file.read()
        pdf_data = pdf_file.read()
        
        if not image_data or not pdf_data:
            return jsonify({'ok': False, 'error': 'Archivos vacíos'}), 400
        
        # Crear nueva página con la imagen
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # Definir colores
        orange_color = (1.0, 0.576, 0.118)  # RGB para #ff931e
        black_color = (0.0, 0.0, 0.0)       # RGB para negro
        white_color = (1.0, 1.0, 1.0)       # RGB para blanco
        
        # Definir márgenes para el marco
        margin = 30
        
        # Dibujar marco negro con márgenes
        frame_width = 4
        c.setStrokeColor(black_color)
        c.setLineWidth(frame_width)
        c.rect(margin, margin, width-(2*margin), height-(2*margin), stroke=1, fill=0)
        
        # Dibujar banner naranja en la parte superior
        banner_height = 60
        c.setFillColor(orange_color)
        c.rect(0, height - banner_height, width, banner_height, stroke=0, fill=1)
        
        # Texto "PLANO PROPUESTO" en blanco (más pequeño)
        c.setFillColor(white_color)
        c.setFont("Helvetica-Bold", 18)
        text_width = c.stringWidth("PLANO PROPUESTO", "Helvetica-Bold", 18)
        text_x = (width - text_width) / 2
        text_y = height - banner_height + 25
        c.drawString(text_x, text_y, "PLANO PROPUESTO")
        
        # Insertar imagen centrada en el espacio restante
        img = ImageReader(BytesIO(image_data))
        img_width, img_height = img.getSize()
        
        # Calcular espacio disponible (restando banner y márgenes)
        available_width = width - 40  # márgenes laterales
        available_height = height - banner_height - 60  # banner + márgenes
        
        # Calcular escala para que la imagen quepa manteniendo proporción
        scale = min(available_width / img_width, available_height / img_height)
        new_width = img_width * scale
        new_height = img_height * scale
        
        # Centrar la imagen en el espacio disponible
        x = (width - new_width) / 2
        y = (height - banner_height - new_height) / 2
        
        c.drawImage(img, x, y, width=new_width, height=new_height)
        c.save()
        
        # Obtener la nueva página como PDF
        new_page_data = buffer.getvalue()
        buffer.close()
        
        # Leer PDF original
        pdf_reader = PdfReader(BytesIO(pdf_data))
        pdf_writer = PdfWriter()
        
        # Agregar primera página
        if len(pdf_reader.pages) > 0:
            pdf_writer.add_page(pdf_reader.pages[0])
        
        # Insertar nueva página con la imagen
        new_page_reader = PdfReader(BytesIO(new_page_data))
        if len(new_page_reader.pages) > 0:
            pdf_writer.add_page(new_page_reader.pages[0])
        
        # Agregar resto de páginas (si hay más de 1 página original)
        for i in range(1, len(pdf_reader.pages)):
            pdf_writer.add_page(pdf_reader.pages[i])
        
        # Generar PDF final
        output_buffer = BytesIO()
        pdf_writer.write(output_buffer)
        output_data = output_buffer.getvalue()
        output_buffer.close()
        
        return Response(output_data, mimetype='application/pdf')
        
    except Exception as e:
        return jsonify({'ok': False, 'error': f'Error procesando PDF: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
