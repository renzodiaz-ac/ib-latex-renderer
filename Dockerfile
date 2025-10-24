FROM debian:bookworm-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    texlive texlive-latex-extra texlive-fonts-recommended \
    texlive-pictures texlive-science lmodern python3 python3-pip && \
    pip install flask && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY app.py /app
EXPOSE 8080
CMD ["python3", "app.py"]
