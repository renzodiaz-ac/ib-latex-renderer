FROM python:3.11-slim

# Instalar dependencias mínimas de LaTeX
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-pictures \
    texlive-science \
    ghostscript \
    lmodern && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Instalar Flask
RUN pip install flask

WORKDIR /app
COPY app.py /app

EXPOSE 8080
CMD ["python", "app.py"]
