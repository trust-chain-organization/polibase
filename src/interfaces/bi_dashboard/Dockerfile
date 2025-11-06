FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv via pip (more reliable in Docker)
RUN pip install --no-cache-dir uv

# Copy project files needed for dependency installation
COPY pyproject.toml uv.lock README.md ./
COPY src/ /app/src/

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# Install BI Dashboard specific dependencies
COPY src/interfaces/bi_dashboard/requirements.txt /tmp/bi_requirements.txt
RUN uv pip install -r /tmp/bi_requirements.txt

# Set Python path to include /app so that 'src' module can be found
ENV PYTHONPATH=/app

# Expose Dash default port
EXPOSE 8050

# Run the application using uv from /app directory (where .venv is located)
CMD ["uv", "run", "python", "src/interfaces/bi_dashboard/app.py"]
