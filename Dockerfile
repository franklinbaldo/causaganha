FROM python:3.12-slim

# Install uv
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./
RUN uv pip install -e .[dev]

# Copy the rest of the application
COPY . .

CMD ["bash"]
