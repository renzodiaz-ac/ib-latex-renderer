FROM python:3.11-slim

# Install system dependencies (LaTeX + poppler for PDF to PNG)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    texlive-latex-base texlive-latex-recommended texlive-latex-extra \
    texlive-pictures texlive-fonts-recommended poppler-utils && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    flask \
    pydantic==2.5.2 \
    chromadb \
    openai

RUN pip install uvicorn


# Set working directory
WORKDIR /app

# Copy all sources (including your ib_store vector DB)
COPY . /app

# Expose port for Render
EXPOSE 8080

# Start Flask app
CMD ["python", "app.py"]
