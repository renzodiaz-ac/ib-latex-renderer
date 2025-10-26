FROM python:3.10-slim

# Instala solo lo necesario para LaTeX con TikZ + PDF to PNG
RUN apt-get update && apt-get install -y \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-science \
    texlive-pictures \
    poppler-utils \
    ghostscript \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Instala Flask
RUN python3 -m pip install --no-cache-dir flask

# Puerto y ejecución
EXPOSE 8080
CMD ["python3", "app.py"]
