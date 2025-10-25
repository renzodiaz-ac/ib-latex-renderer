from flask import Flask, request, jsonify
import tempfile, subprocess, os, base64

app = Flask(__name__)

# -----------------------------
# Helpers robustos
# -----------------------------
def as_str(x, default=""):
    """Devuelve un str seguro; maneja None, ints, etc."""
    return default if x is None else str(x)

def build_diagram_block(diagram_raw: str) -> str:
    """Devuelve un bloque LaTeX que escala el tikz al ancho A5."""
    if not diagram_raw:
        return ""
    s = as_str(diagram_raw, "").strip()
    if "\\begin{tikzpicture}" not in s:
        # No es un tikz; no lo insertamos automáticamente.
        return ""
    if "\\end{tikzpicture}" not in s:
        s += "\n\\end{tikzpicture}"
    # Escalar a 95% del ancho útil para evitar recortes
    return "\n\\begin{center}\\resizebox{0.95\\linewidth}{!}{%\n" + s + "\n}%\n\\end{center}\n"


# ============================================================
# 1️⃣ COMPILAR LATEX A PDF
# ============================================================
@app.route("/compile", methods=["POST"])
def compile_tex():
    try:
        data = request.get_json(force=True) or {}

        question = as_str(data.get("question"), "").strip()
        diagram   = data.get("diagram")  # puede ser None
        meta      = data.get("metadata") or {}
        topic     = as_str(meta.get("topic"), "IB Exercise").replace("\n", " ").strip()

        diagram_block = build_diagram_block(diagram)

        latex = (
            r"\documentclass[12pt]{article}" + "\n"
            + r"\usepackage[a5paper,landscape,left=1.2cm,right=1.2cm,top=0.5cm,bottom=0.8cm]{geometry}" + "\n"
            + r"\usepackage[T1]{fontenc}" + "\n"
            + r"\usepackage{xcolor,amsmath,amssymb,tcolorbox,lmodern,tikz,pgfplots,gensymb}" + "\n"
            + r"\pgfplotsset{compat=1.18,width=\linewidth}" + "\n"
            + r"\usetikzlibrary{calc}" + "\n"
            + r"\definecolor{IBNavy}{HTML}{0B1B35}" + "\n"
            + r"\pagestyle{empty}" + "\n\n"
            + r"\begin{document}" + "\n"
            + r"\begin{tcolorbox}[colback=white,colframe=IBNavy,"
              "before skip=2mm,after skip=2mm,sharp corners,boxrule=0.8pt,"
              "title=IB Math AI SL -- " + topic + ",fonttitle=\\bfseries]" + "\n"
            + question + "\n"
            + r"\end{tcolorbox}" + "\n\n"
            + diagram_block
            + r"\end{document}"
        )

        with tempfile.TemporaryDirectory() as tmp:
            tex_path = os.path.join(tmp, "doc.tex")
            pdf_path = os.path.join(tmp, "doc.pdf")

            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(latex)

            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", tex_path],
                cwd=tmp,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            if result.returncode != 0:
                log_file = os.path.join(tmp, "doc.log")
                if os.path.exists(log_file):
                    with open(log_file, "r", encoding="utf-8", errors="ignore") as log:
                        latex_log = log.read()
                    return jsonify({"error": "LaTeX compilation failed", "log": latex_log}), 500
                return jsonify({"error": "pdflatex failed", "details": result.stderr.decode(errors='ignore')}), 500

            with open(pdf_path, "rb") as f:
                pdf_b64 = base64.b64encode(f.read()).decode()

        return jsonify({"pdf_base64": pdf_b64})

    except Exception as e:
        # Evita errores no serializables
        return jsonify({"error": as_str(e)}), 500


# ============================================================
# 2️⃣ CONVERTIR PDF A PNG
# ============================================================
@app.route("/pdf-to-png", methods=["POST"])
def pdf_to_png():
    try:
        data = request.get_json(force=True) or {}
        pdf_b64 = as_str(data.get("pdf_base64"), "")

        if not pdf_b64:
            return jsonify({"error": "Missing field: pdf_base64"}), 400

        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = os.path.join(tmp, "input.pdf")
            png_path = os.path.join(tmp, "page")

            with open(pdf_path, "wb") as f:
                f.write(base64.b64decode(pdf_b64))

            subprocess.run(
                ["pdftoppm", "-png", "-singlefile", "-r", "300", pdf_path, png_path],
                check=True
            )

            with open(png_path + ".png", "rb") as f:
                png_b64 = base64.b64encode(f.read()).decode()

        return jsonify({"png_base64": png_b64})

    except subprocess.CalledProcessError as e:
        return jsonify({"error": "pdftoppm failed", "details": as_str(e)}), 500
    except Exception as e:
        return jsonify({"error": as_str(e)}), 500


# ============================================================
# SERVIDOR
# ============================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
