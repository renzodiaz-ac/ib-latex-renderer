from flask import Flask, request, jsonify
import tempfile, subprocess, os, base64, uuid, time, glob

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
            png_path = os.path.join(tmp, "doc")  # prefix for pdftoppm

            # 🔽 Decode LaTeX from Base64
            with open(tex_path, "wb") as f:
                f.write(base64.b64decode(latex_b64))

            # 🧩 Compile LaTeX → PDF
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

            # ✅ Convert PDF → PNG (300 dpi)
            subprocess.run(
                ["pdftoppm", "-png", "-singlefile", "-r", "300", pdf_path, png_path],
                check=True
            )

            # 🔄 Read both outputs in Base64
            with open(pdf_path, "rb") as f:
                pdf_b64 = base64.b64encode(f.read()).decode()

            with open(png_path + ".png", "rb") as f:
                png_b64 = base64.b64encode(f.read()).decode()

            # ============================================================
            # 🧱 Save PNG persistently to /static/ for public access
            # ============================================================
            os.makedirs("static", exist_ok=True)

            # 🧹 Clean old files (>1 hour)
            for f in glob.glob("static/exercise_*.png"):
                try:
                    if time.time() - os.path.getmtime(f) > 3600:  # 1 hour
                        os.remove(f)
                except Exception:
                    pass

            # 🆕 Unique filename per exercise
            unique_id = uuid.uuid4().hex[:8]
            output_filename = f"exercise_{unique_id}.png"
            output_path = os.path.join("static", output_filename)

            # Save PNG
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(png_b64))

            png_url = f"https://{request.host}/{output_path}"

            # ✅ Return all outputs
            return jsonify({
                "pdf_base64": pdf_b64,
                "png_base64": png_b64,
                "png_url": png_url
            })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================================
#  🔹 ENDPOINT 2 – Generic Upload (Base64 → Public URL)
# ==========================================================
@app.route("/upload", methods=["POST"])
def upload():
    """
    Receives a Base64 string (e.g. from an AI-generated image)
    and stores it in /static/ returning a public URL.
    """
    try:
        data = request.get_json(force=True)
        file_b64 = data.get("base64", "")
        filename = data.get("filename", "uploaded.png")

        if not file_b64:
            return jsonify({"error": "Missing 'base64' in request."}), 400

        # Remove prefix if present
        if file_b64.startswith("data:image"):
            file_b64 = file_b64.split(",")[1]

        os.makedirs("static", exist_ok=True)
        file_path = os.path.join("static", filename)

        with open(file_path, "wb") as f:
            f.write(base64.b64decode(file_b64))

        url = f"https://{request.host}/{file_path}"
        return jsonify({"url": url})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================================
#  🚀 APP STARTUP
# ==========================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
