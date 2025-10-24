from flask import Flask, request, jsonify
import tempfile, subprocess, os, base64, json

app = Flask(__name__)

@app.route("/compile", methods=["POST"])
def compile_tex():
    try:
        data = request.get_json(force=True)
        question = data.get("question", "")
        diagram = data.get("diagram", "")
        topic = data.get("metadata", {}).get("topic", "IB Exercise")

        # Prepara el bloque del diagrama fuera del string
        diagram_block = ""
        if diagram and "\\begin{tikzpicture}" in diagram:
            diagram_block = diagram

        # Construir el documento LaTeX
        latex = (
    r"\documentclass[12pt]{article}" + "\n" +
    r"\usepackage[a5paper,landscape,left=1.2cm,right=1.2cm,top=0.5cm,bottom=0.8cm]{geometry}" + "\n" +
    r"\usepackage[T1]{fontenc}" + "\n" +
    r"\usepackage{xcolor,amsmath,amssymb,tcolorbox,lmodern,tikz,pgfplots}" + "\n" +
    r"\pgfplotsset{compat=1.18}" + "\n" +
    r"\definecolor{IBNavy}{HTML}{0B1B35}" + "\n" +
    r"\pagestyle{empty}" + "\n\n" +
    r"\begin{document}" + "\n" +
    r"\begin{tcolorbox}[colback=white,colframe=IBNavy," +
    "title=IB Math AI SL -- " + topic + ",fonttitle=\\bfseries]" + "\n" +
    question + "\n" +
    r"\end{tcolorbox}" + "\n\n" +
    diagram_block + "\n" +
    r"\end{document}"
)


        # Crear archivo temporal y compilar LaTeX
        with tempfile.TemporaryDirectory() as tmp:
            tex_path = os.path.join(tmp, "doc.tex")
            pdf_path = os.path.join(tmp, "doc.pdf")

            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(latex)

            subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", tex_path],
                cwd=tmp,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            with open(pdf_path, "rb") as f:
                pdf_b64 = base64.b64encode(f.read()).decode()

        return jsonify({"pdf_base64": pdf_b64})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
