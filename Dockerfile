FROM python:3.10-slim

# =====================================================
# 🔧 Instalación de dependencias del sistema
# =====================================================
RUN apt-get update && apt-get install -y \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-science \
    texlive-pictures \
    lmodern \
    poppler-utils \
    ghostscript \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Actualiza el índice de TeX (necesario para detectar nuevos paquetes)
RUN mktexlsr

# =====================================================
# 📁 Configuración del entorno
# =====================================================
WORKDIR /app
COPY . .

# Instala dependencias de Python
RUN pip install --no-cache-dir flask gunicorn

# Crea carpeta para archivos estáticos públicos
RUN mkdir -p static

# =====================================================
# 🚀 Configuración del servidor
# =====================================================
# Render usa gunicorn por defecto; es más estable que python app.py
#  - workers=2 permite compilar múltiples requests simultáneamente
#  - threads=4 mejora la concurrencia I/O para Make y Softr
EXPOSE 8080
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4"]
