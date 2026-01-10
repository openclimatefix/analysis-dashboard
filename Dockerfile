FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy full repository INCLUDING .git
COPY . .

# Ensure git tags are present for versioning
RUN git describe --tags || git fetch --tags

# Install project + dependencies
RUN uv sync --no-dev

EXPOSE 8501

CMD ["uv", "run", "streamlit", "run", "src/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
