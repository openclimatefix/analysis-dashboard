FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy only what is needed for install
COPY pyproject.toml README.md ./
COPY src/ src/

# Copy ONLY git metadata for versioning
COPY .git .git

# Ensure tags are available
RUN git fetch --tags || true

# Install dependencies + project (version resolved here)
RUN uv sync --no-dev

# Remove git metadata after install (keeps image small)
RUN rm -rf .git

EXPOSE 8501

CMD ["streamlit", "run", "src/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
