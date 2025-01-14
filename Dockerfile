# Use Python 3.12 slim image
FROM python:3.12-slim

# Install necessary system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    unzip \
    libpq-dev \
    gcc \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source code
COPY src .

# Expose the necessary ports
EXPOSE 8501

EXPOSE 5433

# Run the Streamlit app
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0", "--browser.serverAddress=0.0.0.0", "--server.enableCORS=False"]
