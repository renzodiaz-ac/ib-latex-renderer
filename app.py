import os
import time
import uuid
import glob
import base64
import tempfile
import subprocess
import re
import random
from flask import Flask, request, jsonify
from pydantic import BaseModel
from typing import List

# Inicializar Flask
app = Flask(__name__)

# ==========================================================
# 0. UTILIDADES DE LIMPIEZA LATEX
# ==========================================================
def sanitize_latex(latex_code):
    """
    Limpia alucinaciones comunes de la IA y corrige errores de sintaxis
    antes de compilar.
    """
    # 1. Eliminar paquetes conflictivos
    latex_code = re.sub(r'\\usepackage(\[.*\])?\{microtype\}', '', latex_code)
    # latex_code = re.sub(r'\\usepackage(\[.*\])?\{tcolorbox\}', '', latex_code) # YA NO LO BORRES si lo usas en el template

    # 2. CORRECCIÓN CRÍTICA: EL ERROR DE "MATH MODE" vs "ESPACIO VERTICAL"
    # La IA escribe \[2mm] pensando que es espacio. LaTeX cree que es una ecuación.
    # Buscamos \[ seguido de dígitos y unidades (mm, cm, pt, ex, em) y cerramos el corchete
    # Reemplazamos \[2mm] por \\[2mm]
    latex_code = re.sub(r'\\\[\s*(\d+[a-z]{2})\]', r'\\\\[\1]', latex_code)

    # 3. Corrección de saltos de línea mal formados al inicio
    latex_code = re.sub(r'^\s*\\\\\[', r'\\[', latex_code, flags=re.MULTILINE)

    # 4. Corrección de formas geométricas (Diamantes -> Círculos)
    latex_code = latex_code.replace(", diamond", ", circle")
    latex_code = latex_code.replace("diamond,", "circle,")
    latex_code = latex_code.replace("[diamond]", "[circle]")

    # 5. Desempaquetado de seguridad (Solo si la caja está duplicada o mal formada)
    # Si ves que tienes \begin{tcolorbox} dentro de otro, habilita esto. 
    # Por ahora, con el template fijo, déjalo comentado o úsalo solo para limpiar "inner boxes".
    
    return latex_code

# ==========================================================
# 1. VECTOR PARSER (Strokes → Geometry)
# ==========================================================
class Stroke(BaseModel):
    id: str
    points: List[List[float]]
    strokeWidth: float = None
    strokeColor: str = None
    groupIds: List[str] = []
    frameId: str = None
    seed: int = None

class ParseRequest(BaseModel):
    elements: List[Stroke]

class Symbol(BaseModel):
    id: str
    bbox: List[float]
    points: List[List[float]]

def compute_bbox(points):
    if not points: return [0,0,0,0]
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return [min(xs), min(ys), max(xs), max(ys)]

@app.post("/parse_strokes")
def parse_strokes_endpoint():
    try:
        # force=True permite leer JSON aunque el header esté mal
        payload = request.get_json(force=True)
        if isinstance(payload, list):
            if not payload:
                return jsonify({"error": "Empty list received"}), 400
            payload = payload[0]

        req = ParseRequest(**payload)

        symbols = []
        for el in req.elements:
            if not el.points:
                continue
            bbox = compute_bbox(el.points)
            symbols.append(Symbol(
                id=el.id,
                bbox=bbox,
                points=el.points
            ))

        return jsonify({
            "count": len(symbols),
            "symbols": [s.dict() for s in symbols]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================================
# 2. COMPILE LATEX (ROBUSTO)
# ==========================================================
@app.route("/compile", methods=["POST"])
def compile_tex():
    try:
        data = request.get_json(force=True)
        latex_b64 = data.get("latex_base64", "")

        if not latex_b64:
            return jsonify({"error": "Missing 'latex_base64'"}), 400

        # Decodificar y SANITIZAR el código LaTeX
        raw_latex = base64.b64decode(latex_b64).decode('utf-8')
        clean_latex = sanitize_latex(raw_latex)
        
        # Volver a bytes para escribir el archivo
        latex_bytes = clean_latex.encode('utf-8')

        with tempfile.TemporaryDirectory() as tmp:
            tex_path = os.path.join(tmp, "doc.tex")
            pdf_path = os.path.join(tmp, "doc.pdf")
            png_prefix = os.path.join(tmp, "doc")

            # Escribir el archivo .tex
            with open(tex_path, "wb") as f:
                f.write(latex_bytes)

            # 1. Ejecutar PDFLATEX con TIMEOUT
            try:
                process = subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "doc.tex"],
                    cwd=tmp,  # Ejecutar DENTRO del temp para que los logs queden ahí
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=15  # Matar si tarda más de 15s
                )
            except subprocess.TimeoutExpired:
                return jsonify({"error": "Compilation timed out (infinite loop in LaTeX)"}), 408

            # Verificar errores de LaTeX
            if process.returncode != 0:
                log_file = os.path.join(tmp, "doc.log")
                latex_log = "Log not found."
                if os.path.exists(log_file):
                    # Latin-1 es necesario porque los logs de error de LaTeX suelen tener caracteres raros
                    with open(log_file, "r", encoding="latin-1", errors="replace") as log:
                        latex_log = log.read()
                
                # Devolver el log truncado para no saturar la respuesta
                return jsonify({"error": "LaTeX compilation failed", "log": latex_log[-2000:]}), 400

            # 2. Ejecutar PDFTOPPM (Convertir PDF a PNG)
            try:
                subprocess.run(
                    ["pdftoppm", "-png", "-singlefile", "-r", "300", "doc.pdf", "doc"],
                    cwd=tmp,
                    check=True,
                    timeout=15
                )
            except subprocess.CalledProcessError:
                return jsonify({"error": "Failed to convert PDF to Image"}), 500

            # Leer resultado
            generated_png = png_prefix + ".png"
            if not os.path.exists(generated_png):
                 return jsonify({"error": "PNG file was not generated"}), 500

            pdf_b64_out = base64.b64encode(open(pdf_path, "rb").read()).decode()
            png_b64_out = base64.b64encode(open(generated_png, "rb").read()).decode()

            # Guardar en static para acceso público (limpieza automática simple)
            os.makedirs("static", exist_ok=True)
            
            # Limpiar archivos viejos (> 1 hora)
            now = time.time()
            for f in glob.glob("static/exercise_*.png"):
                try:
                    if now - os.path.getmtime(f) > 3600:
                        os.remove(f)
                except: pass

            unique_id = uuid.uuid4().hex[:8]
            output_filename = f"exercise_{unique_id}.png"
            output_path = os.path.join("static", output_filename)
            
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(png_b64_out))

            # Construir URL pública
            # Nota: En Render, request.host suele ser correcto, pero si usas HTTPS asegúrate de que el esquema sea https
            scheme = "https" if request.is_secure or request.headers.get("X-Forwarded-Proto") == "https" else "http"
            png_url = f"{scheme}://{request.host}/static/{output_filename}"

            return jsonify({
                "pdf_base64": pdf_b64_out,
                "png_base64": png_b64_out,
                "png_url": png_url
            })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================================
# 3. UPLOAD IMAGE
# ==========================================================
@app.route("/upload", methods=["POST"])
def upload():
    try:
        data = request.get_json(force=True)
        file_b64 = data.get("base64")
        filename = data.get("filename", "uploaded.png")

        if not file_b64:
            return jsonify({"error": "Missing 'base64'"}), 400

        if "," in file_b64:
            file_b64 = file_b64.split(",")[1]

        os.makedirs("static", exist_ok=True)
        file_path = os.path.join("static", filename)

        with open(file_path, "wb") as f:
            f.write(base64.b64decode(file_b64))
        
        scheme = "https" if request.is_secure or request.headers.get("X-Forwarded-Proto") == "https" else "http"
        return jsonify({"url": f"{scheme}://{request.host}/static/{filename}"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# ==========================================================
# 5. START SERVER
# ==========================================================
if __name__ == "__main__":
    # En Render, PORT viene como variable de entorno
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)