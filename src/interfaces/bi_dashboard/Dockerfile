FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including curl for uv installation
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Copy project files needed for dependency installation
COPY pyproject.toml uv.lock ./
COPY src/ /app/src/

# Install dependencies using uv (use absolute path)
RUN /root/.cargo/bin/uv sync --frozen --no-dev

# Set PATH for runtime
ENV PATH="/root/.cargo/bin:${PATH}"

# Set Python path to include /app so that 'src' module can be found
ENV PYTHONPATH=/app

# Set working directory to BI dashboard
WORKDIR /app/src/interfaces/bi_dashboard

# Expose Dash default port
EXPOSE 8050

# Run the application using uv
CMD ["uv", "run", "python", "app.py"]
