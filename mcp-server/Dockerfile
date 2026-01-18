FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server.py .

# Expose the MCP server port
EXPOSE 8000

# Set environment variables with defaults
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000
ENV MCP_PATH=/mcp
ENV GITHUB_REPO=malekmaciej/przepisy
ENV RECIPES_PATH=""

# Run the MCP server
CMD ["python", "server.py"]
