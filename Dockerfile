FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock README.md ./

# Install dependencies (no dev deps in production)
RUN uv sync --frozen --no-dev

# Copy the rest of the application
COPY alembic.ini ./
COPY migrations/ ./migrations/
COPY src/ ./src/

# Rebuild with source so the package is installed
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Run migrations then start the server
CMD ["sh", "-c", "alembic upgrade head && python -m kevin.main"]
