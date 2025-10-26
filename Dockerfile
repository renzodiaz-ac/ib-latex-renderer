FROM python:3.10-slim

# Instala paquetes necesarios para LaTeX + TikZ + fuentes modernas
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

# Actualiza índice de TeX (necesario para encontrar lmodern.sty)
RUN mktexlsr

# Trabajo en /app
WORKDIR /app
COPY . .

# Instala Flask
RUN pip install --no-cache-dir flask

# Puerto y comando final
EXPOSE 8080
CMD ["python3", "app.py"]
