# Imagen base oficial con TeX Live y Python
FROM texlive/texlive:latest

# Instala Python y Flask
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    python3 -m pip install --break-system-packages flask && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copia la aplicación
WORKDIR /app
COPY app.py /app

# Exponer el puerto
EXPOSE 8080

# Ejecutar el servidor Flask
CMD ["python3", "app.py"]
