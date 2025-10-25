FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    texlive-latex-base texlive-latex-recommended texlive-latex-extra \
    texlive-pictures texlive-fonts-recommended poppler-utils && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app
RUN pip install flask

EXPOSE 8080
CMD ["python", "app.py"]
