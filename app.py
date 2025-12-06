from flask import Flask, request, jsonify
import tempfile, subprocess, os, base64, uuid, time, glob
from pydantic import BaseModel
from typing import List

app = Flask(__name__)

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

class ParseResponse(BaseModel):
    count: int
    symbols: List[Symbol]

def compute_bbox(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return [min(xs), min(ys), max(xs), max(ys)]

@app.post("/parse_strokes")
def parse_strokes_endpoint():
    try:
        payload = request.get_json(force=True)

        # If Make sends a list, unwrap it
        if isinstance(payload, list):
            if len(payload) == 0:
                return jsonify({"error": "Empty list received"}), 400
            payload = payload[0]

        if not isinstance(payload, dict):
            return jsonify({"error": "Invalid JSON format"}), 400

        # Pydantic validation
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
# 2. COMPILE LATEX
# ==========================================================
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
            png_path = os.path.join(tmp, "doc")

            with open(tex_path, "wb") as f:
                f.write(base64.b64decode(latex_b64))

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

            subprocess.run(
                ["pdftoppm", "-png", "-singlefile", "-r", "300", pdf_path, png_path],
                check=True
            )

            with open(pdf_path, "rb") as f:
                pdf_b64 = base64.b64encode(f.read()).decode()

            with open(png_path + ".png", "rb") as f:
                png_b64 = base64.b64encode(f.read()).decode()

            os.makedirs("static", exist_ok=True)

            for f in glob.glob("static/exercise_*.png"):
                try:
                    if time.time() - os.path.getmtime(f) > 3600:
                        os.remove(f)
                except:
                    pass

            unique_id = uuid.uuid4().hex[:8]
            output_filename = f"exercise_{unique_id}.png"
            output_path = os.path.join("static", output_filename)

            with open(output_path, "wb") as f:
                f.write(base64.b64decode(png_b64))

            png_url = f"https://{request.host}/{output_path}"

            return jsonify({
                "pdf_base64": pdf_b64,
                "png_base64": png_b64,
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
        file_b64 = data.get("base64", "")
        filename = data.get("filename", "uploaded.png")

        if not file_b64:
            return jsonify({"error": "Missing 'base64' in request."}), 400

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
# 5. RAG: Retrieve Past Paper Examples
# ==========================================================
from openai import OpenAI
import chromadb

client = OpenAI()

# Load persistent vector DB
chroma_client = chromadb.PersistentClient(path="ib_store")
collection = chroma_client.get_collection("ib_questions")

@app.route("/retrieve", methods=["POST"])
def retrieve():
    try:
        data = request.get_json(force=True)
        topic = data.get("topic")
        archetype_description = data.get("archetype_description")
        k = data.get("k", 3)

        if not topic or not archetype_description:
            return jsonify({"error": "Missing topic or archetype_description"}), 400

        query_text = f"Topic: {topic}\nSkill: {archetype_description}"

        # Create embedding
        emb = client.embeddings.create(
            model="text-embedding-3-large",
            input=query_text
        ).data[0].embedding

        # Query vector store
        results = collection.query(
            query_embeddings=[emb],
            n_results=k,
            where={"topic": topic}
        )

        out = []
        for doc, qid in zip(results["documents"][0], results["ids"][0]):
            out.append({
                "id": qid,
                "text": doc
            })

        return jsonify({"examples": out})

    except Exception as e:
        return jsonify({"error": str(e)}), 500





# ==========================================================
# 4. START SERVER
# ==========================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
