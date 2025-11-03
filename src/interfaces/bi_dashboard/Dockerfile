FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY src/interfaces/bi_dashboard/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/interfaces/bi_dashboard/ .

# Expose Dash default port
EXPOSE 8050

# Run the application
CMD ["python", "app.py"]
