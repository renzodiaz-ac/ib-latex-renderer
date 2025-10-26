from flask import Flask, request, jsonify
import tempfile, subprocess, os, base64

app = Flask(__name__)


@app.route("/compile", methods=["POST"])
def compile_tex():
    try:
        data = request.get_json(force=True)
        latex_b64 = data.get("latex_base64", "")

        if not latex_b64:
            return jsonify({"error": "Missing 'latex_base64' in request."}), 400

        with tempfile.TemporaryDirectory() as tmp:
            tex_path = os.path.join(tmp, "doc.tex")
            pdf_path = os.path.join(tmp, "doc.pdf")
            png_path = os.path.join(tmp, "doc")  # pdftoppm output prefix

            # 🔽 Escribe .tex a partir de base64
            with open(tex_path, "wb") as f:
                f.write(base64.b64decode(latex_b64))

            # 🔄 Compilar LaTeX a PDF
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

            # ✅ PDF a base64
            with open(pdf_path, "rb") as f:
                pdf_b64 = base64.b64encode(f.read()).decode()

            # 🔄 Convertir PDF a PNG (300 dpi, A4 aprox)
            subprocess.run(
                ["pdftoppm", "-png", "-singlefile", "-r", "300", pdf_path, png_path],
                check=True
            )

            # ✅ PNG a base64
            with open(png_path + ".png", "rb") as f:
                png_b64 = base64.b64encode(f.read()).decode()

            # ✅ Devuelve ambos correctamente
            return jsonify({
                "pdf_base64": pdf_b64,
                "png_base64": png_b64
            })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)