FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY src/interfaces/bi_dashboard/requirements.txt /tmp/bi_dashboard_requirements.txt
RUN pip install --no-cache-dir -r /tmp/bi_dashboard_requirements.txt

# Copy entire src directory (needed for DI container and infrastructure)
COPY src/ /app/src/

# Set Python path to include /app so that 'src' module can be found
ENV PYTHONPATH=/app

# Set working directory to BI dashboard
WORKDIR /app/src/interfaces/bi_dashboard

# Expose Dash default port
EXPOSE 8050

# Run the application
CMD ["python", "app.py"]
