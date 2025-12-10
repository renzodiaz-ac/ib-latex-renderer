FROM python:3.11-slim

# 1. Instalar dependencias del sistema
# AGREGADO: 'lmodern' para corregir tu error de fuentes.
# AGREGADO: 'texlive-fonts-extra' opcional por si pides fuentes raras, 
# pero 'lmodern' es la clave aquí.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-pictures \
    texlive-fonts-recommended \
    texlive-science \
    lmodern \
    poppler-utils \
    ghostscript && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 2. Configurar directorio de trabajo
WORKDIR /app

# 3. Instalar librerías de Python
RUN pip install --no-cache-dir \
    flask \
    pydantic==2.5.2 \
    chromadb \
    openai \
    uvicorn

# 4. Copiar todo el código
COPY . /app

# 5. Exponer el puerto
EXPOSE 8080

# 6. Comando de inicio
CMD ["python", "app.py"]