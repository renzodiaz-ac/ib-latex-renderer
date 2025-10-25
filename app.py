from flask import Flask, request, jsonify
import tempfile, subprocess, os, base64, re

app = Flask(__name__)

# ============================================================
# 🧩 UTILIDADES Y SANITIZACIÓN
# ============================================================

def safe_str(x, default=""):
    return default if x is None else str(x)

def clean_unicode(s: str) -> str:
    """Reemplaza caracteres problemáticos por equivalentes LaTeX."""
    if not s:
        return ""
    replacements = {
        "–": "-", "—": "-", "−": "-", "°": r"\degree",
        "“": '"', "”": '"', "‘": "'", "’": "'",
        "•": r"$\bullet$", "→": r"$\to$",
        " ": " ", " ": " ",  # espacios no estándar
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s

def extract_tikz(diagram_raw: str) -> str:
    """
    Extrae el bloque \begin{tikzpicture}...\end{tikzpicture}
    y lo escala con adjustbox de forma segura.
    """
    if not diagram_raw:
        return ""
    s = safe_str(diagram_raw).strip()
    s = re.sub(r"(?s).*?(\\begin\{tikzpicture\})", r"\1", s)  # recorta inicio
    s = re.sub(r"(\\end\{tikzpicture\}).*", r"\1", s)         # recorta fin
    if "\\begin{tikzpicture}" not in s or "\\end{tikzpicture}" not in s:
        return ""
    # Wrapping robusto con adjustbox
    return (
        "\n\\begin{center}\n"
        "\\begin{adjustbox}{max width=0.95\\linewidth,keepaspectratio}\n"
        f"{s}\n"
        "\\end{adjustbox}\n"
        "\\end{center}\n"
    )

# ============================================================
# 🧱 ENDPOINT: COMPILAR LATEX → PDF
# ============================================================

@app.route("/compile", methods=["POST"])
def compile_tex():
    try:
        data = request.get_json(force=True) or {}
        question = clean_unicode(safe_str(data.get("question"), "").strip())
        diagram  = clean_unicode(safe_str(data.get("diagram"), "").strip())
        meta     = data.get("metadata") or {}
        topic    = clean_unicode(safe_str(meta.get("topic"), "IB Exercise").strip())

        tikz_block = extract_tikz(diagram)

        latex_doc = rf"""
\documentclass[12pt]{{article}}
\usepackage[a5paper,landscape,left=1.2cm,right=1.2cm,top=0.5cm,bottom=0.8cm]{{geometry}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage{{textcomp,gensymb,adjustbox}}
\usepackage{{xcolor,amsmath,amssymb,tcolorbox,lmodern,tikz,pgfplots}}
\pgfplotsset{{compat=1.18,width=\linewidth}}
\usetikzlibrary{{calc,arrows.meta,patterns}}
\definecolor{{IBNavy}}{{HTML}}{{0B1B35}}
\pagestyle{{empty}}

\begin{{document}}
\begin{{tcolorbox}}[
    colback=white,
    colframe=IBNavy,
    sharp corners,
    boxrule=0.8pt,
    before skip=2mm,
    after skip=3mm,
    title=IB Math AI SL -- {topic},
    fonttitle=\bfseries
]
{question}
\end{{tcolorbox}}

{tikz_block}

\end{{document}}
"""

        with tempfile.TemporaryDirectory() as tmp:
            tex_path = os.path.join(tmp, "doc.tex")
            pdf_path = os.path.join(tmp, "doc.pdf")

            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(latex_doc)

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
                        latex_log = log.read()[-8000:]
                    # fallback: PDF sin TikZ
                    fallback_pdf = None
                    if tikz_block:
                        with open(tex_path, "w", encoding="utf-8") as f:
                            f.write(latex_doc.replace(tikz_block, ""))
                        subprocess.run(
                            ["pdflatex", "-interaction=nonstopmode", "doc.tex"],
                            cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                        )
                        with open(pdf_path, "rb") as f:
                            fallback_pdf = base64.b64encode(f.read()).decode()
                    return jsonify({
                        "error": "LaTeX TikZ compilation failed",
                        "log": latex_log,
                        "fallback_pdf": fallback_pdf
                    }), 500

            with open(pdf_path, "rb") as f:
                pdf_b64 = base64.b64encode(f.read()).decode()

        return jsonify({"pdf_base64": pdf_b64})

    except Exception as e:
        return jsonify({"error": safe_str(e)}), 500

# ============================================================
# 🖼️ ENDPOINT: PDF → PNG
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
# 🚀 MAIN
# ============================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
