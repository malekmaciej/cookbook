FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY chainlit.md .
COPY .chainlit/ .chainlit/

# Expose port 8000 (Chainlit default)
EXPOSE 8000

# Set environment variables
ENV CHAINLIT_HOST=0.0.0.0
ENV CHAINLIT_PORT=8000

# Run the Chainlit application
CMD ["chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8000"]
