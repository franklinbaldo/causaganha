FROM python:3.12-slim

# Install uv
RUN apt-get update && apt-get install -y git \
    && pip install --no-cache-dir uv pre-commit \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./
RUN uv pip install -e .[dev]

# Copy the rest of the application
COPY . .

CMD ["bash"]
