# ---------- BASE ----------
FROM python:3.10-slim

# ---------- DEPENDENCIAS DEL SISTEMA ----------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-pictures \
    texlive-science \
    poppler-utils \
    ghostscript \
    lmodern \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ---------- DEPENDENCIAS DE PYTHON ----------
RUN pip install flask

# ---------- COPIAR ARCHIVOS ----------
WORKDIR /app
COPY app.py /app/app.py

# ---------- EJECUTAR SERVIDOR ----------
CMD ["python", "app.py"]
