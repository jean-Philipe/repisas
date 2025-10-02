# API de Planificador de Repisas

Requisitos
- Python 3.10+
- pip

Instalación
1. Crear y activar un virtualenv (opcional)
2. Instalar dependencias:
   
   ```bash
   pip install -r requirements.txt
   ```

Ejecución
```bash
python api.py
```
Arranca en `http://localhost:8000`.

Endpoints
- GET `/plan`
  - Query params: `A,B,C,D,E,H,shape,walls`
    - `walls`: lista separada por comas, por ejemplo `A,B` o `A,B,E`
    - `shape`: `L` | `U` | `1`
  - Respuesta: `{ input, result }` con `result.ok=false` y `error` si no es factible (HTTP 422).
  - Ejemplo:

  ```bash
  curl "http://localhost:8000/plan?A=130&B=250&C=50&D=0&E=250&H=250&shape=L&walls=A,B"
  ```

- POST `/render`
  - Body JSON:
    - Opción 1: el mismo `{ input, result }` recibido desde `/plan`
    - Opción 2: solo `{ input }` con campos `A,B,C,D,E,H,shape,walls`; el servidor recalcula
  - Respuesta: imagen `image/svg+xml`
  - Ejemplo:

  ```bash
  curl -X POST http://localhost:8000/render \
    -H 'Content-Type: application/json' \
    -d '{"input":{"A":130,"B":250,"C":50,"D":0,"E":250,"roomHeight":250,"walls":["A","B"],"shape":"L"}}' > out.svg
  ```

Notas
- La lógica de cálculo está en `api_domain.py`.
- La generación del SVG está en `api_draw.py`.
- No se modifican los archivos existentes del front, la API es independiente.
