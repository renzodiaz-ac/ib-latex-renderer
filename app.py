from flask import Flask, request, jsonify
import tempfile, subprocess, os, base64, re

app = Flask(__name__)

# ============================================================
# 🧩 SANITIZACIÓN Y HELPERS
# ============================================================

def safe_str(x, default=""):
    return default if x is None else str(x)

def replace_unsafe_chars(s: str) -> str:
    """Limpia caracteres Unicode problemáticos."""
    if not s:
        return ""
    replacements = {
        "–": "-", "—": "-", "−": "-", "°": r"\degree",
        "“": '"', "”": '"', "‘": "'", "’": "'",
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s

def clean_tikz_block(diagram_raw: str) -> str:
    """Limpia duplicados center y asegura estructura válida TikZ."""
    if not diagram_raw:
        return ""
    s = safe_str(diagram_raw).strip()
    if "\\begin{tikzpicture}" not in s:
        return ""
    # Remueve center anidados y comentarios finales dañinos
    s = re.sub(r"\\begin\{center\}", "", s)
    s = re.sub(r"\\end\{center\}", "", s)
    s = s.strip()
    if not s.endswith("\\end{tikzpicture}"):
        s += "\n\\end{tikzpicture}"
    # Asegura un cierre limpio y escalado seguro
    return (
        "\n\\begin{center}\n"
        "\\resizebox{0.95\\linewidth}{!}{%\n"
        f"{s}\n"
        "}%\n\\end{center}\n"
    )

# ============================================================
# 🧱 ENDPOINT: COMPILAR LATEX → PDF
# ============================================================

@app.route("/compile", methods=["POST"])
def compile_tex():
    try:
        data = request.get_json(force=True) or {}

        question = replace_unsafe_chars(safe_str(data.get("question"), "").strip())
        diagram  = replace_unsafe_chars(safe_str(data.get("diagram"), "").strip())
        meta     = data.get("metadata") or {}
        topic    = replace_unsafe_chars(safe_str(meta.get("topic"), "IB Exercise").strip())

        diagram_block = clean_tikz_block(diagram)

        latex = (
            r"\documentclass[12pt]{article}" + "\n"
            + r"\usepackage[a5paper,landscape,left=1.2cm,right=1.2cm,top=0.5cm,bottom=0.8cm]{geometry}" + "\n"
            + r"\usepackage[utf8]{inputenc}" + "\n"
            + r"\usepackage[T1]{fontenc}" + "\n"
            + r"\usepackage{textcomp,gensymb}" + "\n"
            + r"\usepackage{xcolor,amsmath,amssymb,tcolorbox,lmodern,tikz,pgfplots}" + "\n"
            + r"\pgfplotsset{compat=1.18,width=\linewidth}" + "\n"
            + r"\usetikzlibrary{calc,arrows.meta,patterns}" + "\n"
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
                ["pdflatex", "-interaction=nonstopmode", "doc.tex"],
                cwd=tmp,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            if result.returncode != 0:
                log_file = os.path.join(tmp, "doc.log")
                if os.path.exists(log_file):
                    with open(log_file, "r", encoding="utf-8", errors="ignore") as log:
                        latex_log = log.read()[:15000]
                    return jsonify({"error": "LaTeX compilation failed", "log": latex_log}), 500
                return jsonify({"error": "pdflatex failed", "details": result.stderr.decode(errors='ignore')}), 500

            with open(pdf_path, "rb") as f:
                pdf_b64 = base64.b64encode(f.read()).decode()

        return jsonify({"pdf_base64": pdf_b64})

    except Exception as e:
        return jsonify({"error": safe_str(e)}), 500

# ============================================================
# 🖼️ ENDPOINT: CONVERTIR PDF → PNG
# ============================================================

@app.route("/pdf-to-png", methods=["POST"])
def pdf_to_png():
    try:
        data = request.get_json(force=True) or {}
        pdf_b64 = safe_str(data.get("pdf_base64"), "")

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
        return jsonify({"error": "pdftoppm failed", "details": safe_str(e)}), 500
    except Exception as e:
        return jsonify({"error": safe_str(e)}), 500

# ============================================================
# 🚀 SERVIDOR
# ============================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
