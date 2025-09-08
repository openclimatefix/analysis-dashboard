# Use Python 3.12 slim image
FROM python:3.12-slim

# Install necessary system packages including curl for uv installation
RUN apt-get update && apt-get install -y --no-install-recommends \
    unzip \
    libpq-dev \
    gcc \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set the working directory
WORKDIR /app

# Copy pyproject.toml for dependency installation
COPY pyproject.toml ./

# Install dependencies using uv (generate lock file during build)
RUN uv sync

# Copy the application source code
COPY src .

# Expose the necessary ports
EXPOSE 8501

EXPOSE 5433

# Run the Streamlit app with uv
CMD ["uv", "run", "streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0", "--browser.serverAddress=0.0.0.0", "--server.enableCORS=False"]
