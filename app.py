# app.py
from flask import Flask, request, jsonify, send_file
import tempfile, subprocess, os, base64, json

app = Flask(__name__)

@app.route("/compile", methods=["POST"])
def compile_tex():
    data = request.get_json()
    question = data.get("question", "")
    diagram = data.get("diagram", "")
    topic = data.get("metadata", {}).get("topic", "Untitled")

    latex = fr"""
\documentclass[12pt]{{article}}
\usepackage[a5paper,landscape,left=1.2cm,right=1.2cm,top=0.5cm,bottom=0.8cm]{{geometry}}
\usepackage{{xcolor,amsmath,amssymb,tcolorbox,lmodern,tikz,pgfplots}}
\pgfplotsset{{compat=1.18}}
\definecolor{{IBNavy}}{{HTML}}{{0B1B35}}
\definecolor{{IBGold}}{{HTML}}{{F2C94C}}
\pagestyle{{empty}}

\begin{{document}}
\begin{{tcolorbox}}[colback=white,colframe=IBNavy,
title=IB Math AI SL -- {topic},fonttitle=\bfseries]
{question}
\end{{tcolorbox}}

{diagram if "\\begin{tikzpicture}" in diagram else ""}
\end{{document}}
"""

    with tempfile.TemporaryDirectory() as tmp:
        tex_path = os.path.join(tmp, "doc.tex")
        pdf_path = os.path.join(tmp, "doc.pdf")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(latex)

        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "doc.tex"],
            cwd=tmp, check=True
        )

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
            pdf_b64 = base64.b64encode(pdf_bytes).decode()

    return jsonify({"pdf_base64": pdf_b64})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
