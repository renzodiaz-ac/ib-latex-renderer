FROM python:3.11-slim

# 1. Instalar dependencias del sistema
# - build-essential: Necesario para compilar dependencias de ChromaDB
# - texlive-science: CRUCIAL para el paquete 'siunitx' (unidades físicas)
# - ghostscript: Ayuda en la renderización de fuentes PDF a Imagen
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
    poppler-utils \
    ghostscript && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 2. Configurar directorio de trabajo
WORKDIR /app

# 3. Copiar requirements (o instalar directos)
# Se recomienda crear un requirements.txt, pero aquí lo hacemos directo para simplicidad
RUN pip install --no-cache-dir \
    flask \
    pydantic==2.5.2 \
    chromadb \
    openai \
    uvicorn

# 4. Copiar todo el código (incluyendo la carpeta ib_store si existe localmente)
COPY . /app

# 5. Exponer el puerto
EXPOSE 8080

# 6. Comando de inicio
CMD ["python", "app.py"]