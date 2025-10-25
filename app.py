from flask import Flask, request, jsonify
import tempfile, subprocess, os, base64, html

app = Flask(__name__)

# ============================================================
# 1️⃣ COMPILAR LATEX A PDF
# ============================================================
@app.route("/compile", methods=["POST"])
def compile_tex():
    try:
        data = request.get_json(force=True)
        question = data.get("question", "").strip()
        diagram = data.get("diagram", "")
        topic = data.get("metadata", {}).get("topic", "IB Exercise")

        # -------------------------------------------
        # 🧹 LIMPIEZA DE TEXTO
        # -------------------------------------------
        question = html.unescape(question)
        question = question.replace("\\n", "\\\\").replace("\n", "\\\\")
        forbidden = ["\u2022", "“", "”", "’", "–", "—"]
        for f in forbidden:
            question = question.replace(f, "'")
        diagram = diagram.replace("\\\\degree", "\\degree").replace("\\\\circ", "\\circ")

        # Escapar caracteres LaTeX problemáticos fuera de entorno matemático
        def escape_latex(s):
            for char in ["&", "%", "#"]:
                s = s.replace(char, "\\" + char)
            return s

        question = escape_latex(question)

        # -------------------------------------------
        # 🧩 BLOQUE DE DIAGRAMA
        # -------------------------------------------
        diagram_block = ""
        if diagram and "\\begin{tikzpicture}" in diagram:
            # Asegura cierre correcto del entorno TikZ
            if "\\end{tikzpicture}" not in diagram:
                diagram += "\n\\end{tikzpicture}"
            diagram_block = "\n" + diagram.strip() + "\n"

        # -------------------------------------------
        # 🧱 CONSTRUCCIÓN DEL DOCUMENTO LATEX
        # -------------------------------------------
        latex = (
            r"\documentclass[12pt]{article}" + "\n"
            + r"\usepackage[a5paper,landscape,left=1.2cm,right=1.2cm,top=0.5cm,bottom=0.8cm]{geometry}" + "\n"
            + r"\usepackage[T1]{fontenc}" + "\n"
            + r"\usepackage{xcolor,amsmath,amssymb,tcolorbox,lmodern,tikz,pgfplots,gensymb}" + "\n"
            + r"\pgfplotsset{compat=1.18}" + "\n"
            + r"\definecolor{IBNavy}{HTML}{0B1B35}" + "\n"
            + r"\pagestyle{empty}" + "\n\n"
            + r"\begin{document}" + "\n"
            + r"\begin{tcolorbox}[colback=white,colframe=IBNavy,"
            + "title=IB Math AI SL -- " + topic + ",fonttitle=\\bfseries]" + "\n"
            + question + "\n"
            + r"\end{tcolorbox}" + "\n\n"
            + diagram_block + "\n"
            + r"\end{document}"
        )

        # -------------------------------------------
        # 🧪 COMPILACIÓN TEMPORAL
        # -------------------------------------------
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
                else:
                    return jsonify({"error": "pdflatex failed", "details": result.stderr.decode()}), 500

            with open(pdf_path, "rb") as f:
                pdf_b64 = base64.b64encode(f.read()).decode()

        return jsonify({"pdf_base64": pdf_b64})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# 2️⃣ CONVERTIR PDF A PNG
# ============================================================
@app.route("/pdf-to-png", methods=["POST"])
def pdf_to_png():
    try:
        data = request.get_json(force=True)
        pdf_b64 = data.get("pdf_base64", "")

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

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# SERVIDOR
# ============================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
